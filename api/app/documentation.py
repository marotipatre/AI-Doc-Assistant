"""Curated official references and manifest dependency discovery; no model calls."""

import json
import re
import tomllib
from pathlib import Path, PurePosixPath
from urllib.parse import quote

CATALOG = json.loads(Path(__file__).with_name("documentation_catalog.json").read_text())


def detect_technologies(sources: list[dict]) -> list[dict]:
    result = []
    for item in CATALOG:
        matches = [
            s
            for s in sources
            if re.search(item["pattern"], s["excerpt"], re.I)
            or (item["path_pattern"] and re.search(item["path_pattern"], s["path"], re.I))
        ]
        if matches:
            result.append(
                {
                    "id": item["name"].lower().replace(" ", "-").replace(".", ""),
                    "name": item["name"],
                    "category": item["category"],
                    "confidence": 0.85,
                    "evidence": matches[:3],
                }
            )
    return result


def dependency_references(sources: list[dict]) -> list[dict]:
    files: dict[str, dict[int, str]] = {}
    evidence: dict[str, dict] = {}
    for source in sources:
        path = source["path"]
        if PurePosixPath(path).name not in {
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "Cargo.toml",
        }:
            continue
        evidence.setdefault(path, source)
        lines = files.setdefault(path, {})
        for i, line in enumerate(source["excerpt"].splitlines(), source["start_line"]):
            lines[i] = line
    known = {package.lower() for item in CATALOG for package in item["packages"]}
    result: dict[str, dict] = {}
    for path, lines in files.items():
        if not lines or min(lines) != 1 or len(lines) != max(lines):
            continue  # An incomplete manifest must not be treated as a complete dependency list.
        content = "\n".join(lines[i] for i in range(1, max(lines) + 1))
        dependencies: list[str] = []
        ecosystem = "pypi"
        try:
            if path.endswith("package.json"):
                data = json.loads(content)
                ecosystem = "npm"
                for group in (
                    "dependencies",
                    "devDependencies",
                    "optionalDependencies",
                    "peerDependencies",
                ):
                    if isinstance(data.get(group), dict):
                        dependencies.extend(data[group])
            elif path.endswith("requirements.txt"):
                dependencies = content.splitlines()
            else:
                data = tomllib.loads(content)
                if path.endswith("Cargo.toml"):
                    ecosystem = "crates"
                    for group in ("dependencies", "dev-dependencies", "build-dependencies"):
                        if isinstance(data.get(group), dict):
                            dependencies.extend(data[group])
                else:
                    dependencies = data.get("project", {}).get("dependencies", [])
        except (ValueError, TypeError, AttributeError):
            continue
        for dependency in dependencies:
            if not isinstance(dependency, str):
                continue
            if dependency.strip().startswith(("#", "-", "http:", "https:", "git+")):
                continue
            match = re.match(
                r"^(@[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+|[a-zA-Z0-9][a-zA-Z0-9_.-]*)",
                dependency.strip(),
            )
            if not match:
                continue
            name = match[0]
            if name.lower() in known:
                continue
            base = {
                "npm": "https://www.npmjs.com/package/",
                "pypi": "https://pypi.org/project/",
                "crates": "https://crates.io/crates/",
            }[ecosystem]
            result[f"{ecosystem}:{name}"] = {
                "name": name,
                "url": base + quote(name, safe="@/"),
                "category": "Other dependencies",
                "kind": "Package registry",
                "evidence": [evidence[path]],
            }
    return list(result.values())[:100]


def documentation_for(sources: list[dict]) -> list[dict]:
    lookup = {item["name"]: item for item in CATALOG}
    verified = [
        {
            "name": skill["name"],
            "category": skill["category"],
            "url": lookup[skill["name"]]["url"],
            "kind": "Official documentation",
            "evidence": skill["evidence"],
        }
        for skill in detect_technologies(sources)
    ]
    return verified + dependency_references(sources)


def documentation_sources(repository_id: str, question: str, sources: list[dict]) -> list[dict]:
    """Link lookup entries, explicitly not scraped documentation content."""
    if not re.search(
        r"\b(docs?|documentation|reference|tutorial|learn|guide|links?)\b", question, re.I
    ):
        return []
    matches = documentation_for(sources)
    named = [item for item in matches if item["name"].lower() in question.lower()]
    selected = named or matches[:5]
    return [
        {
            "id": f"doc:{repository_id}:{i}",
            "path": f"Documentation link: {item['name']}",
            "heading": item["name"],
            "start_line": 1,
            "end_line": 4,
            "excerpt": f"{item['name']} — {item['kind']}\nURL: {item['url']}\nRepository reference: {item['evidence'][0]['path']}\nLink directory entry only. External documentation content has not been retrieved; do not claim it has.",
            "commit_sha": item["evidence"][0]["commit_sha"],
            "github_url": item["url"],
            "language": "text",
        }
        for i, item in enumerate(selected[:3])
    ]


def is_documentation_lookup(question: str) -> bool:
    return bool(
        re.search(r"\b(docs?|documentation|reference|tutorial|guide)\b", question, re.I)
        and re.search(r"\b(where|links?|find|official|redirect)\b", question, re.I)
    )
