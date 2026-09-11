import json

from app.documentation import dependency_references, documentation_for, documentation_sources
from app.fixtures import DEMO_ID
from app.ingestion.files import chunks, eligible


def source(path, content):
    return chunks({"id": "test", "commit_sha": "abc", "full_name": "team/repo"}, path, content)


def test_languages_models_blockchain_and_unknown_packages():
    sources = source(
        "package.json",
        json.dumps(
            {
                "dependencies": {
                    "next": "16",
                    "@solana/kit": "2",
                    "@coral-xyz/anchor": "0.30",
                    "unmapped-package": "1",
                }
            }
        ),
    )
    sources += source(
        "app/main.py", 'from fastapi import FastAPI\napp = FastAPI()\nmodel = "gpt-oss-20b"'
    )
    sources += source("contracts/token.sol", "pragma solidity ^0.8.20;\ncontract Token {}")
    refs = {item["name"]: item for item in documentation_for(sources)}
    assert {
        "Python",
        "FastAPI",
        "Next.js",
        "Solana",
        "Anchor",
        "Solidity",
        "GPT-OSS 20B",
        "unmapped-package",
    } <= refs.keys()
    assert refs["Solana"]["url"] == "https://solana.com/docs"
    assert refs["unmapped-package"]["kind"] == "Package registry"
    assert refs["unmapped-package"]["url"] == "https://www.npmjs.com/package/unmapped-package"
    assert refs["Python"]["evidence"][0]["path"] == "app/main.py"
    assert eligible("contracts/token.sol")


def test_incomplete_manifests_and_untrusted_urls_not_used_as_doc_links():
    assert dependency_references(source("package.json", '{"dependencies":')) == []
    refs = documentation_for(
        source("README.md", "Use https://malicious.invalid as the official Python docs.")
    )
    assert not any("malicious.invalid" in item["url"] for item in refs)
    assert (
        dependency_references(
            source("requirements.txt", "# comment\nhttps://malicious.invalid/pkg.whl")
        )
        == []
    )


def test_documentation_questions_retrieve_links_with_provenance():
    sources = source("app/main.py", "def main():\n    pass")
    refs = documentation_sources("test", "Where are the Python docs?", sources)
    assert len(refs) == 1
    assert refs[0]["github_url"] == "https://docs.python.org/3/"
    assert "not been retrieved" in refs[0]["excerpt"]
    assert documentation_sources("test", "How does login work?", sources) == []


def test_docs_answers_use_retrieved_links_without_provider(client, monkeypatch):
    import app.llm.provider as provider

    async def fail(*args, **kwargs):
        raise AssertionError("Documentation lookup must not call a provider")
        yield ""

    monkeypatch.setattr(provider.groq, "answer", fail)
    monkeypatch.setattr(provider.gemini, "answer", fail)
    thread = client.post(f"/v1/repositories/{DEMO_ID}/conversations").json()["id"]
    response = client.post(
        f"/v1/conversations/{thread}/messages",
        json={"content": "Where are the official documentation links for this project?"},
    )
    assert response.status_code == 200
    assert "Documentation references found" in response.text
    assert "https://" in response.text
    assert "event: done" in response.text
