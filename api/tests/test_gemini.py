import json
import math

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.settings import Settings, get_settings
from app.db.store import ChunkRow, now, store
from app.ingestion.files import chunks
from app.ingestion.jobs import _index
from app.llm import gemini, provider
from app.retrieval.search import retrieve


@pytest.fixture
def gemini_settings(isolated_store, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")
    return settings


def mock_transport(monkeypatch, handler):
    monkeypatch.setattr(
        gemini,
        "client",
        lambda: httpx.AsyncClient(
            base_url=gemini.ORIGIN,
            headers={"x-goog-api-key": "test-gemini-key"},
            transport=httpx.MockTransport(handler),
        ),
    )


def test_provider_selection_is_explicit():
    settings = Settings(
        _env_file=None,
        llm_provider="gemini",
        gemini_api_key="",
        openai_api_key="existing-openai-key",
    )
    assert not settings.provider_configured
    assert settings.provider_key_name == "GEMINI_API_KEY"
    assert settings.embedding_identity.startswith("gemini:")
    settings.llm_provider = "openai"
    assert settings.provider_configured
    with pytest.raises(ValidationError):
        Settings(_env_file=None, gemini_model="../../evil?key=test")


@pytest.mark.asyncio
async def test_gemini_embeddings_use_task_types_dimensions_and_normalization(
    gemini_settings, monkeypatch
):
    seen = []

    def handler(request):
        assert request.url.host == "generativelanguage.googleapis.com"
        assert "test-gemini-key" not in str(request.url)
        assert request.headers["x-goog-api-key"] == "test-gemini-key"
        assert request.url.path.endswith("gemini-embedding-001:batchEmbedContents")
        payload = json.loads(request.content)
        seen.extend(payload["requests"])
        return httpx.Response(
            200,
            json={
                "embeddings": [{"values": [3.0, 4.0] + [0.0] * 1534} for _ in payload["requests"]]
            },
        )

    mock_transport(monkeypatch, handler)
    documents = await provider.embed(["file one", "file two"])
    query = await provider.embed(["find auth"], task="query")
    assert len(documents) == 2 and len(query[0]) == 1536
    assert documents[0][:2] == [0.6, 0.8]
    assert math.isclose(sum(v * v for v in query[0]), 1)
    assert [r["taskType"] for r in seen] == [
        "RETRIEVAL_DOCUMENT",
        "RETRIEVAL_DOCUMENT",
        "RETRIEVAL_QUERY",
    ]
    assert all(r["outputDimensionality"] == 1536 for r in seen)


class SplitStream(httpx.AsyncByteStream):
    def __init__(self, content):
        self.content = content.encode()

    async def __aiter__(self):
        for i in range(0, len(self.content), 7):
            yield self.content[i : i + 7]


def stream_response(records):
    body = ": keepalive\r\n\r\n" + "\r\n\r\n".join(
        "data: " + json.dumps(r, ensure_ascii=False) for r in records
    )
    return httpx.Response(
        200, stream=SplitStream(body), headers={"Content-Type": "text/event-stream"}
    )


@pytest.mark.asyncio
async def test_gemini_stream_retains_policy_history_text_and_usage(gemini_settings, monkeypatch):
    def handler(request):
        assert request.url.params["alt"] == "sse"
        payload = json.loads(request.content)
        assert "untrusted DATA" in payload["systemInstruction"]["parts"][0]["text"]
        assert [c["role"] for c in payload["contents"]] == ["user", "model", "user"]
        assert "UNTRUSTED REPOSITORY EVIDENCE" in payload["contents"][-1]["parts"][0]["text"]
        return stream_response(
            [
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "hidden thought", "thought": True},
                                    {"text": "Auth lives "},
                                ]
                            }
                        }
                    ]
                },
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "here ✓ [1]"}]}, "finishReason": "STOP"}
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 100,
                        "candidatesTokenCount": 12,
                        "thoughtsTokenCount": 3,
                    },
                },
            ]
        )

    mock_transport(monkeypatch, handler)
    usage = {}
    source = {"path": "auth.py", "start_line": 1, "end_line": 1, "excerpt": "def auth(): pass"}
    output = "".join(
        [
            part
            async for part in provider.answer(
                "Where is auth?",
                [source],
                [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}],
                usage,
            )
        ]
    )
    assert output == "Auth lives here ✓ [1]"
    assert usage == {"input_tokens": 100, "output_tokens": 15, "thinking_tokens": 3}


@pytest.mark.asyncio
@pytest.mark.parametrize("finish", [None, "MAX_TOKENS", "SAFETY"])
async def test_incomplete_or_blocked_stream_is_not_success(gemini_settings, monkeypatch, finish):
    candidate = {"content": {"parts": [{"text": "partial"}]}}
    if finish:
        candidate["finishReason"] = finish
    mock_transport(monkeypatch, lambda request: stream_response([{"candidates": [candidate]}]))
    with pytest.raises(gemini.GeminiError):
        _ = [part async for part in gemini.answer("question", "evidence", [], "policy", {})]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500])
async def test_gemini_errors_never_expose_response_secrets(gemini_settings, monkeypatch, status):
    mock_transport(
        monkeypatch,
        lambda request: httpx.Response(status, json={"error": {"message": "private-key-in-error"}}),
    )
    with pytest.raises(gemini.GeminiError) as error:
        await provider.embed(["test"])
    assert error.value.status_code == status
    text = provider.provider_failure_message(error.value)
    assert "Gemini" in text and "private-key-in-error" not in text
    if status == 429:
        assert "quota" in text


@pytest.mark.asyncio
async def test_malformed_embedding_response_is_rejected(gemini_settings, monkeypatch):
    mock_transport(
        monkeypatch, lambda request: httpx.Response(200, json={"embeddings": [{"values": [1, 2]}]})
    )
    with pytest.raises(gemini.GeminiError):
        await provider.embed(["test"])


@pytest.mark.asyncio
async def test_missing_gemini_key_never_falls_back_to_openai(isolated_store, monkeypatch):
    monkeypatch.setattr(get_settings(), "openai_api_key", "old-openai-key")

    def unexpected():
        raise AssertionError("An unselected provider was called")

    monkeypatch.setattr(provider, "client", unexpected)
    assert await provider.embed(["test"]) == []
    assert "GEMINI_API_KEY" in "".join(
        [
            part
            async for part in provider.answer(
                "question", [{"path": "README", "excerpt": "evidence"}], [], {}
            )
        ]
    )


@pytest.mark.asyncio
async def test_provider_switch_rebuilds_vectors_and_never_searches_old_space(
    gemini_settings, monkeypatch
):
    repo = {
        "id": "migration",
        "full_name": "example/repo",
        "owner": "example",
        "name": "repo",
        "default_branch": "main",
        "commit_sha": "a" * 40,
        "status": "ready",
        "indexed_at": now(),
        "file_count": 1,
        "chunk_count": 1,
        "_owner_id": "owner",
    }
    sources = chunks(repo, "README.md", "# Authentication\nSessions protect the auth route.")
    store.put("repositories", repo, "owner", repo["id"])
    monkeypatch.setattr(gemini_settings, "llm_provider", "openai")
    store.replace_index(repo, sources, [[1.0] + [0.0] * 1535], [], {"README.md": "blob-sha"})
    monkeypatch.setattr(gemini_settings, "llm_provider", "gemini")

    async def never_embed(*args, **kwargs):
        raise AssertionError("Must not embed a query into an incompatible index")

    monkeypatch.setattr("app.retrieval.search.embed", never_embed)
    assert await retrieve(repo["id"], "authentication")

    class FakeGitHub:
        def __init__(self, token):
            pass

        async def metadata(self, *args):
            return {}, repo["commit_sha"]

        async def tree(self, *args):
            return {"tree": [{"path": "README.md", "type": "blob", "size": 50, "sha": "blob-sha"}]}

        async def blob(self, *args):
            raise AssertionError("Unchanged file should be reused")

    monkeypatch.setattr("app.ingestion.jobs.GitHub", FakeGitHub)
    calls = []

    async def embeddings(texts):
        calls.extend(texts)
        return [[0.0, 1.0] + [0.0] * 1534 for _ in texts]

    monkeypatch.setattr("app.ingestion.jobs.embed", embeddings)
    job = {
        "id": "migration-job",
        "repository_id": repo["id"],
        "status": "queued",
        "stage": "queued",
    }
    store.put("jobs", job, "owner", repo["id"])
    await _index(store.get("jobs", job["id"]), store.get("repositories", repo["id"]))
    assert len(calls) == 1
    with store.session() as session:
        row = session.scalar(select(ChunkRow).where(ChunkRow.repository_id == repo["id"]))
        assert row.embedding_model == gemini_settings.embedding_identity
        assert row.embedding[1] == 1
    assert (
        store.get("repositories", repo["id"])["embedding_identity"]
        == gemini_settings.embedding_identity
    )
    await _index(store.get("jobs", job["id"]), store.get("repositories", repo["id"]))
    assert len(calls) == 1, "Retry must reuse compatible embeddings"
