import pytest
from fastapi.testclient import TestClient

from app.core.limits import WINDOWS
from app.core.settings import get_settings
from app.db.store import Store, store
from app.llm.efficiency import ANSWERS, LOCKS
from app.llm.groq import COOLDOWNS
from app.main import app


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    database = Store(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(store, "engine", database.engine)
    monkeypatch.setattr(store, "url", database.url)
    settings = get_settings()
    for key, value in {
        "openai_api_key": "",
        "gemini_api_key": "",
        "groq_api_key": "",
        "llm_provider": "gemini",
        "retrieval_mode": "hybrid",
        "redis_url": "",
        "seed_demo": True,
        "environment": "development",
        "requests_per_minute": 1000,
        "github_client_id": "",
        "github_client_secret": "",
    }.items():
        monkeypatch.setattr(settings, key, value)
    WINDOWS.clear()
    ANSWERS.clear()
    LOCKS.clear()
    COOLDOWNS.clear()
    database.initialize()
    yield store
    database.engine.dispose()
    WINDOWS.clear()


@pytest.fixture
def client(isolated_store):
    with TestClient(app) as client:
        yield client
