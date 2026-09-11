"""Deterministic context selection and bounded, owner-scoped answer reuse."""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from contextlib import asynccontextmanager

from app.core.settings import get_settings
from app.llm.provider import SYSTEM_POLICY

# Process-local by design: never shared with another application or written to disk.
# Authorization and fresh retrieval happen before every lookup. Cache contains only
# completed text, never credentials, and expires even when a repo is unchanged.
ANSWERS: OrderedDict[str, tuple[float, str]] = OrderedDict()
LOCKS: dict[str, tuple[asyncio.Lock, int]] = {}


def bounded_history(history: list[dict]) -> list[dict]:
    history = list(history)
    # An unanswered/failed user turn is not useful history for the retry.
    while history and history[-1]["role"] == "user":
        history.pop()
    budget = get_settings().history_char_budget
    selected = []
    for item in reversed(history[-4:]):
        if budget <= 0:
            break
        content = item["content"][: min(budget, 1000)]
        selected.append({"role": item["role"], "content": content})
        budget -= len(content)
    return list(reversed(selected))


def bounded_evidence(sources: list[dict]) -> list[dict]:
    budget = get_settings().evidence_char_budget
    selected = []
    seen = set()
    for source in sources:
        # Exact duplicate chunks add no evidence and waste context.
        signature = source["excerpt"].strip()
        if signature in seen or budget <= 0:
            continue
        seen.add(signature)
        excerpt = source["excerpt"][: min(2400, budget)]
        # Preserve line-level citation accuracy when shortening evidence.
        if len(excerpt) < len(source["excerpt"]) and "\n" in excerpt:
            excerpt = excerpt.rsplit("\n", 1)[0]
        selected.append(
            {
                **source,
                "excerpt": excerpt,
                "end_line": min(
                    source["end_line"], source["start_line"] + len(excerpt.splitlines()) - 1
                ),
            }
        )
        budget -= len(excerpt)
        if len(selected) >= 5:
            break
    return selected


def answer_key(
    owner: str, repository: dict, question: str, sources: list[dict], history: list[dict]
) -> str:
    settings = get_settings()
    payload = [
        "v1",
        owner,
        repository["id"],
        repository["commit_sha"],
        repository.get("indexed_at"),
        settings.llm_provider,
        settings.chat_model,
        settings.provider_configured,
        settings.max_output_tokens,
        SYSTEM_POLICY,
        question.strip(),
        sources,
        history,
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def cached_answer(key: str) -> str | None:
    if not get_settings().answer_cache_enabled:
        return None
    item = ANSWERS.get(key)
    if item and item[0] > time.monotonic():
        ANSWERS.move_to_end(key)
        return item[1]
    ANSWERS.pop(key, None)
    return None


def save_answer(key: str, output: str):
    settings = get_settings()
    if not settings.answer_cache_enabled or not output:
        return
    now = time.monotonic()
    for expired in [key for key, (expiry, _) in ANSWERS.items() if expiry <= now]:
        ANSWERS.pop(expired)
    ANSWERS[key] = (now + settings.answer_cache_ttl_seconds, output)
    ANSWERS.move_to_end(key)
    while len(ANSWERS) > 256:
        ANSWERS.popitem(last=False)


@asynccontextmanager
async def answer_lock(key: str):
    lock, users = LOCKS.get(key, (asyncio.Lock(), 0))
    LOCKS[key] = (lock, users + 1)
    try:
        async with lock:
            yield
    finally:
        _, users = LOCKS[key]
        if users == 1:
            LOCKS.pop(key)
        else:
            LOCKS[key] = (lock, users - 1)
