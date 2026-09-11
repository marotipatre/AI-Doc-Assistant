import hashlib
import re
from pathlib import PurePosixPath
from urllib.parse import quote

from app.core.security import contains_secret, safe_path
from app.core.settings import get_settings
from app.documentation import detect_technologies

SKIP_DIRECTORIES = {
    "node_modules",
    ".git",
    ".next",
    "dist",
    "build",
    "vendor",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    "target",
    "fixtures",
    "__snapshots__",
}
EXTENSIONS = {
    ".md",
    ".mdx",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".rs",
    ".go",
    ".sql",
    ".sh",
    ".css",
    ".prisma",
    ".graphql",
    ".java",
    ".rb",
    ".vue",
    ".svelte",
    ".sol",
}
LANGUAGES = {
    ".sol": "Solidity",
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".rs": "Rust",
    ".go": "Go",
    ".md": "Markdown",
    ".mdx": "MDX",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".css": "CSS",
    ".sql": "SQL",
    ".toml": "TOML",
}


def eligible(path: str, size: int = 0) -> bool:
    p = PurePosixPath(path)
    name = p.name.lower()
    if not safe_path(path) or size > get_settings().max_file_bytes:
        return False
    if any(part in SKIP_DIRECTORIES for part in p.parts):
        return False
    if name.startswith(".env") or any(
        token in name for token in ("secret", "credential", "id_rsa", "id_ed25519")
    ):
        return False
    if p.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".lock", ".map"}:
        return False
    if name.endswith((".min.js", ".min.css")) or name in {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lockb",
    }:
        return False
    return p.suffix.lower() in EXTENSIONS or name in {
        "readme",
        "license",
        "contributing",
        "dockerfile",
        "makefile",
        "procfile",
        ".gitignore",
    }


def priority(path: str) -> tuple[int, str]:
    lowered = path.lower()
    if PurePosixPath(lowered).name.startswith("readme"):
        return 0, path
    if PurePosixPath(lowered).name in {
        "package.json",
        "pyproject.toml",
        "cargo.toml",
        "dockerfile",
        "requirements.txt",
        "docker-compose.yml",
    }:
        return 1, path
    if lowered.startswith(("docs/", ".github/")):
        return 2, path
    return 3, path


def chunks(repository: dict, path: str, content: str) -> list[dict]:
    """Bounded overlapping line chunks preserve heading and exact line provenance."""
    if "\x00" in content or contains_secret(content):
        return []
    lines = content.splitlines()
    result = []
    start = 0
    heading = PurePosixPath(path).name
    while start < len(lines):
        end = start
        size = 0
        while end < len(lines) and end - start < 65 and size + len(lines[end]) < 4800:
            size += len(lines[end]) + 1
            end += 1
        if end == start:
            # A huge minified line is neither useful context nor safe to send.
            start += 1
            continue
        for line in lines[: start + 1]:
            match = re.match(r"^#{1,6}\s+(.+)", line)
            if match:
                heading = match.group(1).strip()
        excerpt = "\n".join(lines[start:end])
        identity = f"{repository['id']}:{repository['commit_sha']}:{path}:{start}:{end}"
        link = (
            ""
            if repository.get("is_demo")
            else f"https://github.com/{repository['full_name']}/blob/{quote(repository['commit_sha'], safe='')}/{quote(path, safe='/')}#L{start + 1}-L{end}"
        )
        if excerpt.strip():
            result.append(
                {
                    "id": hashlib.sha256(identity.encode()).hexdigest()[:24],
                    "path": path,
                    "heading": heading,
                    "start_line": start + 1,
                    "end_line": end,
                    "excerpt": excerpt,
                    "commit_sha": repository["commit_sha"],
                    "github_url": link,
                    "language": LANGUAGES.get(PurePosixPath(path).suffix.lower(), "text"),
                }
            )
        if end >= len(lines):
            break
        start = max(start + 1, end - 8)
    return result


def detect_skills(sources: list[dict]) -> list[dict]:
    return detect_technologies(sources)
