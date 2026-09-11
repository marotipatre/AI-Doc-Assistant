from app.core.settings import get_settings
from app.fixtures import DEMO_ID


def test_edit_requires_repository_access_and_available_service(client):
    body = {"instruction": "Clarify setup"}
    assert client.post("/v1/repositories/missing/skill-edits", json=body).status_code == 404
    assert client.post(f"/v1/repositories/{DEMO_ID}/skill-edits", json=body).status_code == 503


def test_edit_returns_reviewable_proposal_without_modifying_repository(client, monkeypatch):
    import app.main as main

    monkeypatch.setattr(get_settings(), "gemini_api_key", "fake-test-key")
    before = client.get(f"/v1/repositories/{DEMO_ID}/overview").json()

    async def fake_answer(question, sources, history, usage, system_policy):
        assert "selected_passage" in question
        assert sources
        assert "ONLY proposed replacement" in system_policy
        yield "## Setup\n\nRead README.md before installing dependencies."

    monkeypatch.setattr(main, "answer", fake_answer)
    response = client.post(
        f"/v1/repositories/{DEMO_ID}/skill-edits",
        json={"instruction": "Clarify setup", "selection": "Read docs", "context": "# Project"},
    )
    assert response.status_code == 200
    assert response.json()["content"].startswith("## Setup")
    assert response.json()["sources"]
    assert client.get(f"/v1/repositories/{DEMO_ID}/overview").json() == before
    assert (
        client.post(
            f"/v1/repositories/{DEMO_ID}/skill-edits", json={"instruction": " "}
        ).status_code
        == 422
    )
