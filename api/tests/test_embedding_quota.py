import pytest
from sqlalchemy import select

from app.core.settings import get_settings
from app.db.store import ChunkRow, store
from app.ingestion.jobs import run_job
from app.llm.gemini import GeminiError
from app.retrieval.search import retrieve


@pytest.fixture
def quota_repo(isolated_store, monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    repo = {
        "id": "quota-repo",
        "full_name": "example/repo",
        "owner": "example",
        "name": "repo",
        "default_branch": "main",
        "commit_sha": "a" * 40,
        "status": "connected",
        "indexed_at": None,
        "file_count": 0,
        "chunk_count": 0,
    }
    store.put("repositories", repo, "owner", repo["id"])

    class FakeGitHub:
        def __init__(self, token):
            pass

        async def metadata(self, *args):
            return {}, "b" * 40

        async def tree(self, *args):
            return {
                "tree": [
                    {"path": f"auth{i}.py", "type": "blob", "size": 50, "sha": str(i)}
                    for i in range(20)
                ]
            }

        async def blob(self, *args):
            return "# Authentication\ndef login():\n    return 'session'\n"

    monkeypatch.setattr("app.ingestion.jobs.GitHub", FakeGitHub)
    return repo


async def index_repo(repo, job_id):
    job = {
        "id": job_id,
        "repository_id": repo["id"],
        "status": "queued",
        "stage": "queued",
    }
    store.put("jobs", job, "owner", repo["id"])
    await run_job(job_id)
    return store.get("jobs", job_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("successful_batches", [0, 1])
async def test_quota_saves_sources_and_resumes_only_missing_vectors(
    quota_repo, monkeypatch, successful_batches
):
    calls = []

    async def limited_embed(texts):
        calls.append(len(texts))
        if len(calls) > successful_batches:
            raise GeminiError(429)
        return [[1.0] + [0.0] * 1535 for _ in texts]

    monkeypatch.setattr("app.ingestion.jobs.embed", limited_embed)
    job = await index_repo(quota_repo, "quota-job")
    assert job["status"] == "completed"
    assert any("keyword search" in warning for warning in job["warnings"])
    repo = store.get("repositories", quota_repo["id"])
    assert repo["status"] == "ready" and repo["chunk_count"] == 20
    assert len(store.list("sources", repository_id=repo["id"])) == 20
    assert repo["warnings"] == job["warnings"]
    with store.session() as session:
        rows = list(session.scalars(select(ChunkRow)))
        assert sum(row.embedding is not None for row in rows) == 16 * successful_batches

    async def query_quota(*args, **kwargs):
        raise GeminiError(429)

    monkeypatch.setattr("app.retrieval.search.embed", query_quota)
    assert await retrieve(repo["id"], "authentication")

    resumed = []

    async def available_embed(texts):
        resumed.extend(texts)
        return [[1.0] + [0.0] * 1535 for _ in texts]

    monkeypatch.setattr("app.ingestion.jobs.embed", available_embed)
    job = await index_repo(repo, "resume-job")
    assert job["status"] == "completed"
    assert len(resumed) == 20 - 16 * successful_batches
    assert not job["warnings"]
    with store.session() as session:
        assert all(row.embedding is not None for row in session.scalars(select(ChunkRow)))


@pytest.mark.asyncio
async def test_authentication_errors_still_fail_indexing(quota_repo, monkeypatch):
    async def rejected_embed(texts):
        raise GeminiError(403)

    monkeypatch.setattr("app.ingestion.jobs.embed", rejected_embed)
    job = await index_repo(quota_repo, "auth-job")
    assert job["status"] == "failed"
    assert "API access" in job["error"]
    assert not store.list("sources", repository_id=quota_repo["id"])
