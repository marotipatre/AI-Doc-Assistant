import asyncio
import hashlib
import uuid

import httpx
from fastapi import HTTPException
from openai import APIError
from redis.asyncio import Redis

from app.core.identity import token_for
from app.core.settings import get_settings
from app.db.store import ChunkRow, now, store
from app.ingestion.files import chunks, detect_skills, eligible, priority
from app.ingestion.github import GitHub
from app.llm.gemini import GeminiError
from app.llm.provider import embed, is_rate_limit, provider_failure_message
from app.schemas import Job

TASKS: set[asyncio.Task] = set()
INDEX_SEMAPHORE = asyncio.Semaphore(2)
ACTIVE_STAGES = {"queued", "running"}


class Cancelled(Exception):
    pass


def update_job(job: dict, **changes):
    current = store.get("jobs", job["id"])
    if not current or current["status"] == "cancelled":
        raise Cancelled()
    job.update(changes)
    store.put("jobs", job, job["_owner_id"], job["repository_id"])


async def enqueue(repo: dict, user: str) -> dict:
    for job in store.list("jobs", owner=user, repository_id=repo["id"]):
        if job["status"] in ACTIVE_STAGES:
            return job
    job = Job(id=str(uuid.uuid4()), repository_id=repo["id"]).model_dump()
    store.put("jobs", job, user, repo["id"])
    repo["status"] = "indexing"
    store.put("repositories", repo, repo["_owner_id"], repo["id"])
    if get_settings().redis_url:
        async with Redis.from_url(get_settings().redis_url) as redis:
            await redis.lpush("repolens:index:pending", job["id"])
    else:
        task = asyncio.create_task(run_job(job["id"]))
        TASKS.add(task)
        task.add_done_callback(TASKS.discard)
    return job


async def run_job(identifier: str):
    async with INDEX_SEMAPHORE:
        job = store.get("jobs", identifier)
        if not job or job["status"] not in ACTIVE_STAGES:
            return
        repo = store.get("repositories", job["repository_id"])
        if not repo:
            return
        previous_sources = store.list("sources", repository_id=repo["id"])
        try:
            async with asyncio.timeout(600):
                await _index(job, repo)
        except Cancelled:
            repo["status"] = "ready" if previous_sources else "connected"
            if store.get("repositories", repo["id"]):
                store.put("repositories", repo, repo["_owner_id"], repo["id"])
        except Exception as exc:
            message = (
                exc.detail
                if isinstance(exc, HTTPException)
                else provider_failure_message(exc)
                if isinstance(exc, (APIError, GeminiError, httpx.HTTPError))
                else "Indexing could not finish. Check GitHub availability and provider configuration, then retry."
            )
            try:
                update_job(job, status="failed", stage="failed", error=str(message))
            except Cancelled:
                pass
            repo["status"] = "ready" if previous_sources else "failed"
            if store.get("repositories", repo["id"]):
                store.put("repositories", repo, repo["_owner_id"], repo["id"])


async def _index(job: dict, repo: dict):
    update_job(job, status="running", stage="fetching", progress=5)
    if repo.get("is_demo"):
        repo["status"] = "ready"
        store.put("repositories", repo, repo["_owner_id"], repo["id"])
        update_job(
            job,
            status="completed",
            stage="ready",
            progress=100,
            files_processed=repo["file_count"],
            total_files=repo["file_count"],
            warnings=[
                "Bundled sample is already indexed; connect a GitHub repository for live sync."
            ],
        )
        return
    user_token = token_for(repo["_owner_id"])
    if repo.get("private") and not user_token:
        raise HTTPException(401, "Sign in to GitHub again to sync this private repository.")
    github = GitHub(user_token or get_settings().github_token)
    metadata, commit = await github.metadata(repo["owner"], repo["name"], repo["default_branch"])
    if (
        commit == repo["commit_sha"]
        and store.get("snapshots", repo["id"] + ":" + commit)
        and repo.get("indexed_at")
        and not get_settings().embeddings_enabled
    ):
        repo["status"] = "ready"
        store.put("repositories", repo, repo["_owner_id"], repo["id"])
        update_job(
            job,
            status="completed",
            stage="ready",
            progress=100,
            files_processed=repo["file_count"],
            total_files=repo["file_count"],
            warnings=["Already up to date. No files or embeddings were duplicated."],
        )
        return
    update_job(job, stage="discovering", progress=12)
    tree = await github.tree(repo["full_name"], commit)
    warnings = []
    if tree.get("truncated"):
        warnings.append(
            "GitHub truncated the repository tree. The index covers the returned files only."
        )
    discovered = sorted(
        [
            entry
            for entry in tree.get("tree", [])
            if entry.get("type") == "blob" and eligible(entry["path"], entry.get("size", 0))
        ],
        key=lambda entry: priority(entry["path"]),
    )
    if len(discovered) > get_settings().max_files:
        warnings.append(
            f"Indexed the {get_settings().max_files} highest-priority files; {len(discovered)} eligible files were discovered."
        )
    files = discovered[: get_settings().max_files]
    previous = store.get("snapshots", repo["id"] + ":" + repo["commit_sha"])
    old_hashes = previous.get("files", {}) if previous else {}
    old_sources = store.list("sources", repository_id=repo["id"])
    old_by_path: dict[str, list] = {}
    for source in old_sources:
        old_by_path.setdefault(source["path"], []).append(source)
    old_vectors = {}
    with store.session() as session:
        from sqlalchemy import select

        for row in session.scalars(select(ChunkRow).where(ChunkRow.repository_id == repo["id"])):
            if (
                row.embedding is not None
                and row.embedding_model == get_settings().embedding_identity
            ):
                old_vectors[str(row.source_id)] = list(row.embedding)
    repo = {**repo, "commit_sha": commit, "stars": metadata.get("stargazers_count", 0)}
    all_sources: list[dict] = []
    vectors: dict[str, list] = {}
    fingerprints = {}
    total_bytes = 0
    update_job(job, stage="parsing", progress=20, total_files=len(files), warnings=warnings)
    for index, entry in enumerate(files):
        update_job(job, files_processed=index, progress=20 + int(45 * index / max(len(files), 1)))
        path = entry["path"]
        total_bytes += entry.get("size", 0)
        if total_bytes > get_settings().max_repository_bytes:
            warnings.append("Repository byte budget reached; remaining files were skipped.")
            break
        if old_hashes.get(path) == entry["sha"] and old_by_path.get(path):
            from urllib.parse import quote

            for old in old_by_path[path]:
                identity = f"{repo['id']}:{commit}:{path}:{old['start_line'] - 1}:{old['end_line']}"
                source = {
                    **old,
                    "id": hashlib.sha256(identity.encode()).hexdigest()[:24],
                    "commit_sha": commit,
                    "github_url": f"https://github.com/{repo['full_name']}/blob/{commit}/{quote(path, safe='/')}#L{old['start_line']}-L{old['end_line']}",
                }
                all_sources.append(source)
                if old["id"] in old_vectors:
                    vectors[source["id"]] = old_vectors[old["id"]]
            fingerprints[path] = entry["sha"]
            continue
        try:
            content = await github.blob(repo["full_name"], entry["sha"])
        except HTTPException as exc:
            if exc.status_code in (401, 429):
                raise
            warnings.append(f"Could not fetch {path}; skipped.")
            continue
        if content is None:
            warnings.append(f"Skipped binary, oversized, or non-UTF-8 file: {path}")
            continue
        parsed = chunks(repo, path, content)
        if not parsed:
            warnings.append(f"Skipped empty, minified, or potentially sensitive file: {path}")
            continue
        all_sources.extend(parsed)
        fingerprints[path] = entry["sha"]
    if not all_sources:
        raise HTTPException(
            422,
            "No supported, safe text files were found. Try a repository with documentation or source files.",
        )
    update_job(
        job,
        stage="embedding" if get_settings().embeddings_enabled else "saving",
        progress=72,
        files_processed=len(fingerprints),
        warnings=warnings,
    )
    needed = (
        [source for source in all_sources if source["id"] not in vectors]
        if get_settings().embeddings_enabled
        else []
    )
    # Keep completed batches when quota runs out, so the next sync can resume.
    for start in range(0, len(needed), 16):
        update_job(job, progress=72 + int(18 * start / max(len(needed), 1)))
        batch = needed[start : start + 16]
        try:
            generated = await embed([source["excerpt"] for source in batch])
        except (APIError, GeminiError) as exc:
            if not is_rate_limit(exc):
                raise
            warnings.append(
                f"Repository indexed with keyword search. {get_settings().provider_label} embedding quota was reached; "
                f"{len(vectors)} of {len(all_sources)} chunks have semantic embeddings. "
                "Sync repository after quota is available to complete semantic search. "
                "AI answers also require available chat-model quota."
            )
            break
        for source, vector in zip(batch, generated):
            vectors[source["id"]] = vector
    if not get_settings().provider_configured:
        warnings.append(
            f"Sources, skills, and keyword search are ready. Configure {get_settings().provider_key_name} to enable AI answers."
        )
    update_job(job, stage="saving", progress=92, warnings=warnings)
    repo.update(
        status="ready",
        indexed_at=now(),
        file_count=len(fingerprints),
        chunk_count=len(all_sources),
        warnings=warnings,
        embedding_identity=get_settings().embedding_identity if vectors else None,
    )
    store.replace_index(
        repo,
        all_sources,
        [vectors.get(source["id"]) for source in all_sources] if vectors else [],
        detect_skills(all_sources),
        fingerprints,
    )
    update_job(
        job, status="completed", stage="ready", progress=100, files_processed=len(fingerprints)
    )
