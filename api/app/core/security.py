import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from fastapi import HTTPException


def normalize_github_url(value: str, branch: str | None = None) -> tuple[str, str, str | None]:
    """Only parsed GitHub names are forwarded to a fixed GitHub API origin."""
    value = value.strip()
    if value.startswith("github.com/"):
        value = "https://" + value
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(422, "Use an HTTPS github.com repository URL.")
    parts = unquote(parsed.path).strip("/").split("/")
    if len(parts) < 2 or (len(parts) > 2 and (len(parts) < 4 or parts[2] != "tree")):
        raise HTTPException(422, "Expected github.com/owner/repository or a /tree/branch URL.")
    owner, name = parts[:2]
    name = name.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", owner):
        raise HTTPException(422, "Invalid GitHub owner.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", name) or name in (".", ".."):
        raise HTTPException(422, "Invalid GitHub repository name.")
    selected = branch or ("/".join(parts[3:]) if len(parts) > 2 else None)
    if selected and (
        len(selected) > 200
        or not re.fullmatch(r"[\w./-]+", selected)
        or ".." in selected
        or selected.startswith("/")
    ):
        raise HTTPException(422, "Invalid branch or commit reference.")
    return owner, name, selected


def safe_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return (
        bool(parts)
        and not path.startswith("/")
        and ".." not in parts
        and "\\" not in path
        and not any(ord(char) < 32 for char in path)
    )


SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{24,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
]


def contains_secret(content: str) -> bool:
    return any(pattern.search(content) for pattern in SECRET_PATTERNS)
