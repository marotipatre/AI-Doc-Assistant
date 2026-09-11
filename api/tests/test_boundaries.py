import pytest
from fastapi import HTTPException

from app.core.security import contains_secret, normalize_github_url, safe_path
from app.ingestion.files import chunks, detect_skills, eligible


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/a/b",
        "https://github.com.evil.test/a/b",
        "https://127.0.0.1/a/b",
        "https://github.com@evil.test/a/b",
        "https://user@github.com/a/b",
        "https://github.com:8443/a/b",
        "https://github.com/a/b?url=http://localhost",
        "https://github.com/a/b#readme",
        "https://github.com/a/..",
        "https://github.com/a/b/tree/../../x",
        "file:///etc/passwd",
    ],
)
def test_url_boundary_rejects_unsupported_targets(url):
    with pytest.raises((HTTPException, ValueError)):
        normalize_github_url(url)


def test_url_normalizes_repo_and_slash_branch():
    assert normalize_github_url(" github.com/acme/project.git ") == ("acme", "project", None)
    assert normalize_github_url("https://github.com/acme/project/tree/feature/auth") == (
        "acme",
        "project",
        "feature/auth",
    )
    assert normalize_github_url("https://github.com/acme/project", "release/1")[-1] == "release/1"


@pytest.mark.parametrize(
    "path",
    [
        "../README.md",
        "/etc/config.py",
        r"docs\..\secrets.py",
        ".env",
        "src/.env.local",
        "credentials.json",
        "private.pem",
        "node_modules/x/index.ts",
        "dist/app.js",
        "pnpm-lock.yaml",
        "bundle.min.js",
        "a.png",
    ],
)
def test_file_boundary_skips_sensitive_generated_and_unsupported_files(path):
    assert not eligible(path)


def test_safe_files_and_budgets():
    assert eligible(".github/workflows/ci.yml")
    assert eligible("docs/architecture.md")
    assert eligible("README")
    assert not eligible("large.py", 999_999)
    assert not safe_path("../../etc/passwd")
    assert contains_secret("-----BEGIN PRIVATE KEY-----")
    assert contains_secret("ghp_" + "a" * 30)


def test_chunk_line_provenance_and_stable_ids():
    repo = {"id": "one", "full_name": "acme/one", "commit_sha": "a" * 40}
    lines = ["# Architecture", *[f"source line {i}" for i in range(140)]]
    source = "\n".join(lines)
    result = chunks(repo, "docs/a guide.md", source)
    assert len(result) >= 3
    assert result == chunks(repo, "docs/a guide.md", source)
    for chunk in result:
        assert chunk["excerpt"] == "\n".join(lines[chunk["start_line"] - 1 : chunk["end_line"]])
        assert chunk["heading"] == "Architecture"
        assert f"/blob/{repo['commit_sha']}/docs/a%20guide.md#L" in chunk["github_url"]
        assert chunk["commit_sha"] == repo["commit_sha"]
    assert chunks(repo, "key.py", "sk-proj-" + "a" * 30) == []
    assert chunks(repo, "a.js", "x" * 5000) == []


def test_skills_preserve_source_evidence():
    repo = {"id": "one", "full_name": "acme/one", "commit_sha": "b" * 40}
    sources = chunks(
        repo,
        "package.json",
        '{"dependencies":{"next":"16","react":"19"},"devDependencies":{"typescript":"5"}}',
    )
    skills = detect_skills(sources)
    assert {"Next.js", "React", "TypeScript"} <= {skill["name"] for skill in skills}
    assert all(0 < s["confidence"] <= 1 and s["evidence"][0] in sources for s in skills)


@pytest.mark.asyncio
async def test_github_stream_handles_compressed_json_without_double_decoding(monkeypatch):
    import gzip
    import json

    import httpx

    from app.ingestion.github import GitHub

    original = httpx.AsyncClient

    def handler(request):
        assert request.url.host == "api.github.com"
        return httpx.Response(
            200,
            content=gzip.compress(json.dumps({"name": "test"}).encode()),
            headers={"Content-Encoding": "gzip", "Content-Type": "application/json"},
        )

    monkeypatch.setattr(
        "app.ingestion.github.httpx.AsyncClient",
        lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler)),
    )
    assert await GitHub().get("/repos/example/test") == {"name": "test"}
    with pytest.raises(HTTPException):
        await GitHub().get("//evil.test/path")
