import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.db.store import store
from app.fixtures import DEMO_ID
from app.llm import efficiency, groq, provider
from app.main import app


@pytest.fixture
def groq_settings(isolated_store, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "test-groq-secret")
    monkeypatch.setattr(settings, "retrieval_mode", "lexical")
    return settings


def transport(monkeypatch, handler):
    monkeypatch.setattr(
        groq,
        "client",
        lambda: httpx.AsyncClient(
            base_url=groq.ORIGIN,
            headers={"Authorization": "Bearer test-groq-secret"},
            transport=httpx.MockTransport(handler),
        ),
    )


class SplitStream(httpx.AsyncByteStream):
    def __init__(self, body):
        self.body = body.encode()

    async def __aiter__(self):
        for i in range(0, len(self.body), 7):
            yield self.body[i : i + 7]


def stream(finish="stop"):
    events = [
        {"choices": [{"delta": {"content": "Auth ✓ [1]"}, "finish_reason": None}]},
        {
            "choices": [{"delta": {}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 90, "completion_tokens": 10},
        },
    ]
    body = (
        ": keepalive\r\n\r\n"
        + "".join("data: " + json.dumps(event) + "\r\n\r\n" for event in events)
        + "data: [DONE]\r\n\r\n"
    )
    return httpx.Response(200, stream=SplitStream(body))


@pytest.mark.asyncio
async def test_groq_single_bounded_request_and_stream(groq_settings, monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url) == groq.ORIGIN + "chat/completions"
        assert request.headers["Authorization"] == "Bearer test-groq-secret"
        body = json.loads(request.content)
        assert body["model"] == groq_settings.groq_model
        assert body["max_completion_tokens"] == 1200
        assert body["reasoning_effort"] == "low" and not body["include_reasoning"]
        assert "tools" not in body
        assert body["messages"][0]["role"] == "system"
        assert "untrusted DATA" in body["messages"][0]["content"]
        return stream()

    transport(monkeypatch, handler)
    source = {"path": "auth.py", "start_line": 1, "end_line": 1, "excerpt": "def auth(): pass"}
    usage = {}
    result = "".join([part async for part in provider.answer("auth?", [source], [], usage)])
    assert result == "Auth ✓ [1]" and len(calls) == 1
    assert usage == {"input_tokens": 90, "output_tokens": 10}


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500])
async def test_groq_redacts_errors_and_observes_cooldown(groq_settings, monkeypatch, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status, headers={"retry-after": "30"}, json={"error": "test-groq-secret"}
        )

    transport(monkeypatch, handler)
    for _ in range(2):
        with pytest.raises(groq.GroqError) as error:
            _ = [part async for part in groq.answer("q", "e", [], "policy", {})]
        assert error.value.status_code == status
        assert "test-groq-secret" not in provider.provider_failure_message(error.value)
    assert len(calls) == (1 if status == 429 else 2)


@pytest.mark.asyncio
@pytest.mark.parametrize("finish", [None, "length", "tool_calls", "content_filter"])
async def test_incomplete_groq_is_not_a_success(groq_settings, monkeypatch, finish):
    transport(monkeypatch, lambda request: stream(finish))
    with pytest.raises(groq.GroqError):
        _ = [part async for part in groq.answer("q", "e", [], "policy", {})]


@pytest.mark.asyncio
async def test_groq_never_uses_other_keys_or_embeddings(groq_settings, monkeypatch):
    def forbidden():
        raise AssertionError("Unexpected provider call")

    monkeypatch.setattr(provider, "client", forbidden)
    monkeypatch.setattr(groq, "client", forbidden)
    monkeypatch.setattr(provider.gemini, "client", forbidden)
    monkeypatch.setattr(groq_settings, "gemini_api_key", "other-key")
    monkeypatch.setattr(groq_settings, "openai_api_key", "other-key")
    assert await provider.embed(["file"]) == []
    monkeypatch.setattr(groq_settings, "retrieval_mode", "hybrid")
    assert await provider.embed(["file"]) == []
    monkeypatch.setattr(groq_settings, "groq_api_key", "")
    assert not groq_settings.provider_configured
    result = "".join(
        [
            part
            async for part in provider.answer("q", [{"path": "README", "excerpt": "data"}], [], {})
        ]
    )
    assert "GROQ_API_KEY" in result


def parse(response):
    return [
        (block.splitlines()[0][7:], json.loads(block.splitlines()[1][6:]))
        for block in response.text.strip().split("\n\n")
    ]


def new_question(client, content="authentication"):
    cid = client.post(f"/v1/repositories/{DEMO_ID}/conversations").json()["id"]
    return client.post(f"/v1/conversations/{cid}/messages", json={"content": content})


def test_repeated_answer_reuse_and_owner_snapshot_isolation(client, monkeypatch):
    calls = []

    async def answer(question, evidence, history, usage):
        calls.append(question)
        yield "Authentication evidence [1]"

    monkeypatch.setattr("app.main.answer", answer)
    first = parse(new_question(client))[-1][1]["message"]
    second = parse(new_question(client))[-1][1]["message"]
    assert not first["cached"] and second["cached"] and len(calls) == 1
    with TestClient(app) as other:
        assert not parse(new_question(other))[-1][1]["message"]["cached"]
    assert len(calls) == 2
    repo = store.get("repositories", DEMO_ID)
    repo["commit_sha"] = "new-snapshot"
    store.put("repositories", repo, "demo", DEMO_ID)
    assert not parse(new_question(client))[-1][1]["message"]["cached"]
    assert len(calls) == 3


def test_failure_never_cached_and_passive_features_make_no_ai_calls(client, monkeypatch):
    calls = []

    async def failure(*args):
        calls.append(1)
        yield "partial"
        raise groq.GroqError(429, 10)

    monkeypatch.setattr("app.main.answer", failure)
    for _ in range(2):
        events = parse(new_question(client))
        assert events[-1][0] == "error"
        assert not any(kind == "done" for kind, _ in events)
    assert len(calls) == 2 and not efficiency.ANSWERS
    for path in ("overview", "sources", "skills", "export"):
        assert client.get(f"/v1/repositories/{DEMO_ID}/{path}").status_code == 200
    runtime = client.get("/v1/runtime").json()
    assert runtime["ai_policy"] == "on_demand"
    assert not any("key" in name for name in runtime)
    assert len(calls) == 2


def test_context_budget_dedup_and_cache_identity(isolated_store, monkeypatch):
    source = {
        "id": "1",
        "path": "a.py",
        "excerpt": "auth\n" * 1000,
        "start_line": 10,
        "end_line": 1010,
    }
    selected = efficiency.bounded_evidence([source, {**source, "id": "2"}])
    assert len(selected) == 1 and len(selected[0]["excerpt"]) <= 2400
    assert selected[0]["end_line"] == 10 + len(selected[0]["excerpt"].splitlines()) - 1
    history = [
        {"role": "user", "content": "x" * 4000},
        {"role": "assistant", "content": "y" * 4000},
        {"role": "user", "content": "failed question"},
    ]
    bounded = efficiency.bounded_history(history)
    assert sum(len(item["content"]) for item in bounded) <= 2000
    assert all(item["content"] != "failed question" for item in bounded)
    repo = {"id": "r", "commit_sha": "sha"}
    key = efficiency.answer_key("owner", repo, "q", selected, [])
    assert key != efficiency.answer_key("owner", repo, "q", selected, bounded)
    monkeypatch.setattr(get_settings(), "gemini_model", "different-model")
    assert key != efficiency.answer_key("owner", repo, "q", selected, [])
    efficiency.save_answer(key, "answer")
    assert efficiency.cached_answer(key) == "answer"
    monkeypatch.setattr(get_settings(), "answer_cache_enabled", False)
    assert efficiency.cached_answer(key) is None


@pytest.mark.asyncio
async def test_duplicate_concurrent_work_coalesces(isolated_store):
    calls = []

    async def request():
        async with efficiency.answer_lock("same"):
            if efficiency.cached_answer("same") is None:
                calls.append(1)
                await asyncio.sleep(0.01)
                efficiency.save_answer("same", "answer")
            return efficiency.cached_answer("same")

    assert await asyncio.gather(request(), request()) == ["answer", "answer"]
    assert len(calls) == 1 and not efficiency.LOCKS


@pytest.mark.asyncio
async def test_openai_interrupted_stream_cannot_be_cached(isolated_store, monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_provider", "openai")
    monkeypatch.setattr(get_settings(), "openai_api_key", "test")
    closed = []

    class PartialStream:
        async def __aiter__(self):
            yield SimpleNamespace(type="response.output_text.delta", delta="partial")

        async def close(self):
            closed.append(True)

    class FakeClient:
        responses = None

        def __init__(self):
            self.responses = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def create(self, **kwargs):
            return PartialStream()

    monkeypatch.setattr(provider, "client", FakeClient)
    source = {"path": "README", "excerpt": "data", "start_line": 1, "end_line": 1}
    with pytest.raises(RuntimeError, match="interrupted"):
        _ = [part async for part in provider.answer("q", [source], [], {})]
    assert closed == [True]
