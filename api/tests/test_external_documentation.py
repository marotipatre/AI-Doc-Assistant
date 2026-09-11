import asyncio

import httpx
import pytest

from app.ingestion.files import chunks
from app.retrieval import documentation as docs


def sources():
    return chunks(
        {"id": "test", "full_name": "team/repo", "commit_sha": "abc"},
        "main.py",
        "from fastapi import FastAPI\napp = FastAPI()",
    )


@pytest.mark.asyncio
async def test_retrieves_relevant_official_page_and_link(monkeypatch):
    docs.CACHE.clear()
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if request.url.path == "/":
            content = '<h1>FastAPI</h1><a href="/tutorial/dependencies/">Dependency injection</a><a href="https://unapproved.invalid/">Ignore</a><script>not source text</script>'
        else:
            content = '<h1>Dependency injection</h1><p>Use Depends to declare a dependency.</p><h2 id="use">Declare dependencies</h2>'
        return httpx.Response(200, text=content, headers={"content-type": "text/html"})

    client = httpx.AsyncClient
    monkeypatch.setattr(
        docs.httpx,
        "AsyncClient",
        lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs),
    )
    result = await docs.retrieve_documentation(
        "Explain FastAPI dependency injection using the docs", sources()
    )
    assert len(requested) == 2
    assert result[0]["github_url"] == "https://fastapi.tiangolo.com/tutorial/dependencies/"
    assert "Use Depends" in result[0]["excerpt"]
    assert all("not source text" not in source["excerpt"] for source in result)
    assert all(source["id"].startswith("external-doc:") for source in result)
    await docs.retrieve_documentation(
        "Explain FastAPI dependency injection using the docs", sources()
    )
    assert len(requested) == 2  # cached page content, not cached model output


@pytest.mark.asyncio
async def test_redirects_cannot_escape_the_approved_host(monkeypatch):
    docs.CACHE.clear()

    def handler(request):
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})

    client = httpx.AsyncClient
    monkeypatch.setattr(
        docs.httpx,
        "AsyncClient",
        lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs),
    )
    with pytest.raises(ValueError, match="redirect"):
        await docs.fetch_page("https://fastapi.tiangolo.com/", "fastapi.tiangolo.com")
    assert await docs.retrieve_documentation("Explain FastAPI dependencies", sources()) == []
    assert not docs.allowed("https://user:password@fastapi.tiangolo.com/", "fastapi.tiangolo.com")
    assert not docs.allowed("https://fastapi.tiangolo.com:1234/", "fastapi.tiangolo.com")


@pytest.mark.asyncio
async def test_unknown_technology_does_not_trigger_fetch(monkeypatch):
    async def fail(*args):
        raise AssertionError("Unexpected fetch")

    monkeypatch.setattr(docs, "fetch_page", fail)
    assert await docs.retrieve_documentation("Read UnknownPlatform documentation", sources()) == []


@pytest.mark.asyncio
async def test_documentation_fetches_have_bounded_concurrency(monkeypatch):
    docs.CACHE.clear()
    monkeypatch.setattr(docs, "SEMAPHORE", asyncio.Semaphore(3))
    active = peak = 0

    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1
        return httpx.Response(
            200, text="<p>Reference content</p>", headers={"content-type": "text/html"}
        )

    client = httpx.AsyncClient
    monkeypatch.setattr(
        docs.httpx,
        "AsyncClient",
        lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs),
    )
    await asyncio.gather(
        *(
            docs.fetch_page(f"https://fastapi.tiangolo.com/{i}", "fastapi.tiangolo.com")
            for i in range(6)
        )
    )
    assert peak == 3
