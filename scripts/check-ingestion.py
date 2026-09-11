"""Opt-in live GitHub smoke test in an isolated, provider-free API workspace."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from fastapi.testclient import TestClient
from app.core.settings import get_settings
from app.db.store import Store, store
from app.main import app

settings = get_settings()
settings.openai_api_key = ""
settings.gemini_api_key = ""
settings.groq_api_key = ""
settings.redis_url = ""
settings.seed_demo = False
with tempfile.TemporaryDirectory(prefix="repolens-smoke-") as directory:
    database = Store(f"sqlite:///{directory}/smoke.db")
    store.engine = database.engine
    with TestClient(app) as client:
        created = client.post("/v1/repositories", json={"url": "https://github.com/octocat/Hello-World"})
        assert created.status_code == 201, created.text
        repo = created.json()
        job = client.post(f"/v1/repositories/{repo['id']}/index").json()
        for _ in range(180):
            progress = client.get(f"/v1/jobs/{job['id']}").json()
            if progress["status"] in {"completed", "failed"}:
                break
            time.sleep(0.5)
        assert progress["status"] == "completed", progress
        overview = client.get(f"/v1/repositories/{repo['id']}/overview").json()
        assert overview["sources"] and all(source["commit_sha"] in source["github_url"] for source in overview["sources"])
        conversation = client.post(f"/v1/repositories/{repo['id']}/conversations").json()
        answer = client.post(f"/v1/conversations/{conversation['id']}/messages", json={"content": "Hello World"})
        assert "event: done" in answer.text and "Evidence preview" in answer.text
        print({"result": "passed", "repository": repo["full_name"], "files": overview["repository"]["file_count"], "sources": len(overview["sources"]), "mode": "real GitHub + isolated SQLite + evidence-preview stream; no provider calls"})
    database.engine.dispose()
