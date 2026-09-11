import json
import time

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.limits import limit
from app.db.store import ChunkRow, store
from app.fixtures import DEMO_ID
from app.ingestion.github import GitHub
from app.ingestion.jobs import run_job
from app.main import app


def events(response):
    result = []
    for block in response.text.strip().split("\n\n"):
        lines = block.splitlines()
        event = next(line[7:] for line in lines if line.startswith("event: "))
        payload = json.loads(next(line[6:] for line in lines if line.startswith("data: ")))
        result.append((event, payload))
    return result


def conversation(client):
    response = client.post(f"/v1/repositories/{DEMO_ID}/conversations")
    assert response.status_code == 201
    return response.json()["id"]


def test_health_ready_overview_and_openapi(client):
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/ready").json()
    assert ready["database"] == "sqlite"
    assert ready["provider"] == "evidence_preview"
    overview = client.get(f"/v1/repositories/{DEMO_ID}/overview").json()
    assert overview["repository"]["is_demo"]
    assert overview["sources"] and overview["skills"]
    assert all(s["github_url"] == "" for s in overview["sources"])
    assert "X-Request-ID" in client.get("/health").headers
    assert (
        "/v1/conversations/{conversation_id}/messages"
        in client.get("/openapi.json").json()["paths"]
    )


def test_cited_stream_persistence_and_cross_user_isolation(client):
    cid = conversation(client)
    response = client.post(
        f"/v1/conversations/{cid}/messages", json={"content": "Where is authentication handled?"}
    )
    assert response.status_code == 200
    parsed = events(response)
    assert {event for event, _ in parsed} >= {"citations", "token", "done"}
    final = next(data["message"] for event, data in parsed if event == "done")
    assert "Evidence preview" in final["content"]
    assert final["content"] == "".join(data["text"] for event, data in parsed if event == "token")
    assert any("auth" in s["path"] for s in final["citations"])
    assert len(client.get(f"/v1/conversations/{cid}").json()["messages"]) == 2
    with TestClient(app) as stranger:
        assert stranger.get(f"/v1/conversations/{cid}").status_code == 404
        assert stranger.delete(f"/v1/conversations/{cid}").status_code == 404
    assert client.delete(f"/v1/conversations/{cid}").status_code == 204
    assert client.get(f"/v1/conversations/{cid}").status_code == 404


def test_unanswerable_question_and_question_validation(client):
    cid = conversation(client)
    response = client.post(
        f"/v1/conversations/{cid}/messages", json={"content": "quantum zebracorn teleportation"}
    )
    final = next(data["message"] for event, data in events(response) if event == "done")
    assert not final["citations"]
    assert "enough evidence" in final["content"]
    assert (
        client.post(f"/v1/conversations/{cid}/messages", json={"content": "  "}).status_code == 422
    )
    assert (
        client.post(f"/v1/conversations/{cid}/messages", json={"content": "x" * 4001}).status_code
        == 422
    )


def test_origin_body_and_oauth_boundaries(client):
    assert (
        client.post(
            "/v1/repositories",
            json={"url": "https://github.com/a/b"},
            headers={"origin": "https://evil.test"},
        ).status_code
        == 403
    )
    assert client.post("/v1/repositories", content="x" * 16001).status_code == 413
    assert client.get("/v1/auth/github").status_code == 503
    assert client.get("/v1/auth/repositories").status_code == 401
    assert not client.get("/v1/auth/session").json()["authenticated"]
    assert client.delete(f"/v1/repositories/{DEMO_ID}").status_code == 403


def test_provider_failure_is_a_stream_error(client, monkeypatch):
    async def failure(*args):
        yield "Partial answer"
        raise httpx.ReadTimeout("sensitive provider details")

    monkeypatch.setattr("app.main.answer", failure)
    response = client.post(
        f"/v1/conversations/{conversation(client)}/messages", json={"content": "authentication"}
    )
    parsed = events(response)
    assert any(event == "error" for event, _ in parsed)
    assert not any(event == "done" for event, _ in parsed)
    assert "sensitive provider details" not in response.text


@pytest.mark.asyncio
async def test_rate_limits(isolated_store):
    await limit("unit", 2)
    await limit("unit", 2)
    with pytest.raises(HTTPException) as error:
        await limit("unit", 2)
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_cancelled_job_is_not_processed(isolated_store):
    store.put(
        "jobs", {"id": "cancelled", "repository_id": "none", "status": "cancelled"}, "user", "none"
    )
    await run_job("cancelled")
    assert store.get("jobs", "cancelled")["status"] == "cancelled"


def test_connect_index_sync_idempotence_and_deletion(client, monkeypatch):
    calls = []
    commit = ["a" * 40]
    files = {
        "README.md": "# Architecture\nNext.js interface calls the FastAPI service.\nRun pytest for testing.",
        "api/main.py": "from fastapi import FastAPI\napp = FastAPI()",
    }

    async def metadata(self, owner, name, branch=None):
        return {
            "owner": {"login": owner},
            "name": name,
            "full_name": f"{owner}/{name}",
            "selected_branch": branch or "main",
            "html_url": f"https://github.com/{owner}/{name}",
            "language": "Python",
            "private": False,
        }, commit[0]

    async def tree(self, full_name, sha):
        return {
            "tree": [
                {"path": path, "type": "blob", "sha": path, "size": len(content)}
                for path, content in files.items()
            ]
        }

    async def blob(self, full_name, sha):
        calls.append(sha)
        return files[sha]

    monkeypatch.setattr(GitHub, "metadata", metadata)
    monkeypatch.setattr(GitHub, "tree", tree)
    monkeypatch.setattr(GitHub, "blob", blob)
    response = client.post("/v1/repositories", json={"url": "https://github.com/example/tiny"})
    assert response.status_code == 201
    rid = response.json()["id"]
    assert (
        client.post("/v1/repositories", json={"url": "https://github.com/example/tiny"}).json()[
            "id"
        ]
        == rid
    )

    def sync():
        response = client.post(f"/v1/repositories/{rid}/sync")
        assert response.status_code == 200
        jid = response.json()["id"]
        for _ in range(100):
            status = client.get(f"/v1/jobs/{jid}").json()
            if status["status"] in ("completed", "failed"):
                break
            time.sleep(0.01)
        assert status["status"] == "completed", status
        return client.get(f"/v1/repositories/{rid}/overview").json()

    first = sync()
    initial_ids = [s["id"] for s in first["sources"]]
    assert len(calls) == 2
    assert [s["id"] for s in sync()["sources"]] == initial_ids
    assert len(calls) == 2
    commit[0] = "b" * 40
    changed = sync()
    assert len(calls) == 2, "Unchanged blobs must be reused across commits"
    assert all(s["commit_sha"] == commit[0] for s in changed["sources"])
    assert [s["id"] for s in changed["sources"]] != initial_ids
    commit[0] = "a" * 40
    reverted = sync()
    assert reverted["repository"]["commit_sha"] == commit[0]
    assert all(s["commit_sha"] == commit[0] for s in reverted["sources"])
    with TestClient(app) as stranger:
        assert stranger.get(f"/v1/repositories/{rid}/overview").status_code == 404
    assert client.delete(f"/v1/repositories/{rid}").status_code == 204
    assert not store.list("sources", repository_id=rid)
    with store.session() as session:
        from sqlalchemy import select

        assert not session.scalars(select(ChunkRow).where(ChunkRow.repository_id == rid)).all()


def test_oauth_state_encryption_private_access_and_logout(client, monkeypatch):
    from urllib.parse import parse_qs, urlsplit

    from cryptography.fernet import Fernet

    from app.core.identity import serializer
    from app.core.settings import get_settings

    settings = get_settings()
    key = Fernet.generate_key().decode()
    for name, value in {
        "github_client_id": "test-client",
        "github_client_secret": "test-secret",
        "session_secret": "test-session-secret",
        "token_encryption_key": key,
    }.items():
        monkeypatch.setattr(settings, name, value)
    begin = client.get("/v1/auth/github?private=true", follow_redirects=False)
    assert begin.status_code == 307
    query = parse_qs(urlsplit(begin.headers["location"]).query)
    assert "repo" in query["scope"][0]
    assert query["code_challenge_method"] == ["S256"]
    assert query["prompt"] == ["select_account"]
    assert "test-secret" not in begin.headers["location"]
    assert client.get("/v1/auth/github/callback?code=test&state=wrong").status_code == 400
    state_cookie = client.cookies.get("repolens_oauth_state")
    assert serializer.loads(state_cookie)["state"] == query["state"][0]

    class TokenClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            assert url == "https://github.com/login/oauth/access_token"
            assert kwargs["json"]["code_verifier"]
            return httpx.Response(
                200, json={"access_token": "unit-private-token", "scope": "repo,read:user"}
            )

    async def github_user(self, path):
        assert path == "/user"
        return {"id": 123, "login": "tester", "avatar_url": ""}

    monkeypatch.setattr("app.main.httpx.AsyncClient", TokenClient)
    monkeypatch.setattr(GitHub, "get", github_user)
    callback = client.get(
        f"/v1/auth/github/callback?code=test&state={query['state'][0]}", follow_redirects=False
    )
    assert callback.status_code == 307
    assert "github=connected" in callback.headers["location"]
    account = store.get("accounts", "github:123")
    assert account["encrypted_token"] != "unit-private-token"
    assert (
        Fernet(key.encode()).decrypt(account["encrypted_token"].encode()).decode()
        == "unit-private-token"
    )
    assert "unit-private-token" not in callback.text
    assert client.get("/v1/auth/session").json()["authenticated"]
    assert client.post("/v1/auth/logout").status_code == 204
    assert store.get("accounts", "github:123") is None
    assert not client.get("/v1/auth/session").json()["authenticated"]


def test_oauth_callback_requires_state_cookie(client, monkeypatch):
    from cryptography.fernet import Fernet
    from app.core.settings import get_settings

    settings = get_settings()
    for name, value in {
        "github_client_id": "test-client",
        "github_client_secret": "test-secret",
        "session_secret": "test-session-secret",
        "token_encryption_key": Fernet.generate_key().decode(),
    }.items():
        monkeypatch.setattr(settings, name, value)

    response = client.get("/v1/auth/github/callback?code=test&state=test")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "GitHub sign-in state is missing. Start sign-in again from the same browser URL."
    )


def test_provider_errors_are_actionable_and_redacted():
    from openai import AuthenticationError, RateLimitError

    from app.llm.provider import provider_failure_message

    response = httpx.Response(
        429, request=httpx.Request("POST", "https://api.openai.com/v1/embeddings")
    )
    error = RateLimitError(
        "sensitive-token-value", response=response, body={"code": "credit_balance_exhausted"}
    )
    message = provider_failure_message(error)
    assert "quota" in message and "sensitive-token-value" not in message
    authentication = AuthenticationError("sensitive-token-value", response=response, body=None)
    assert "OPENAI_API_KEY" in provider_failure_message(authentication)
