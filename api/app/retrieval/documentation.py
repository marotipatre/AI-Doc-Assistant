"""Bounded retrieval from catalog-approved documentation sites."""

import asyncio
import hashlib
import re
import time
from collections import OrderedDict
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlsplit

import httpx

from app.documentation import CATALOG, documentation_for

SEMAPHORE = asyncio.Semaphore(3)
CACHE: OrderedDict[str, tuple[float, tuple[str, list[tuple[str, str]]]]] = OrderedDict()


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.href = ""
        self.label: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip += 1
        if self.skip:
            return
        attributes = dict(attrs)
        if tag == "a":
            self.href = attributes.get("href", "")
            self.label = []
        if tag in {"p", "li", "h1", "h2", "h3", "pre", "div", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip = max(0, self.skip - 1)
        if tag == "a" and self.href:
            self.links.append((self.href, " ".join(self.label)))
            self.href = ""

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self.href:
                self.label.append(data)


def allowed(url: str, host: str) -> bool:
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname == host
            and parsed.port in (None, 443)
            and not parsed.username
            and not parsed.password
        )
    except ValueError:
        return False


async def fetch_page(url: str, host: str) -> tuple[str, list[tuple[str, str]]]:
    if not allowed(url, host):
        raise ValueError("Unapproved documentation URL")
    key = urldefrag(url)[0]
    cached = CACHE.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    async with (
        SEMAPHORE,
        httpx.AsyncClient(timeout=8, follow_redirects=False, trust_env=False) as client,
    ):
        target = key
        for _ in range(4):
            if not allowed(target, host):
                raise ValueError("Documentation redirect left approved host")
            async with client.stream(
                "GET",
                target,
                headers={"User-Agent": "RepoLens-Docs/1.0", "Accept": "text/html,text/plain"},
            ) as response:
                if response.is_redirect:
                    target = urljoin(target, response.headers.get("location", ""))
                    continue
                response.raise_for_status()
                if not any(
                    kind in response.headers.get("content-type", "")
                    for kind in ("text/html", "text/plain", "text/markdown")
                ):
                    raise ValueError("Unsupported documentation content")
                content = bytearray()
                async for part in response.aiter_bytes():
                    content.extend(part)
                    if len(content) > 750_000:
                        raise ValueError("Documentation page exceeds size limit")
                parser = PageParser()
                parser.feed(content.decode("utf-8", errors="replace"))
                text = "\n".join(
                    line.strip() for line in "".join(parser.parts).splitlines() if line.strip()
                )[:100_000]
                links = [
                    (urljoin(target, href), label)
                    for href, label in parser.links
                    if allowed(urljoin(target, href), host)
                ]
                result = (text, links[:500])
                CACHE[key] = (time.monotonic() + 3600, result)
                CACHE.move_to_end(key)
                while len(CACHE) > 48:
                    CACHE.popitem(last=False)
                return result
        raise ValueError("Too many documentation redirects")


async def retrieve_documentation(question: str, sources: list[dict]) -> list[dict]:
    matches = documentation_for(sources)
    named = [
        item
        for item in matches
        if item["kind"] == "Official documentation" and item["name"].lower() in question.lower()
    ]
    # Only fetch when a recognized repository technology is explicitly named.
    if not named:
        return []
    entry = named[0]
    approved = next(item for item in CATALOG if item["name"] == entry["name"])
    host = urlsplit(approved["url"]).hostname or ""
    terms = set(re.findall(r"[a-z]{3,}", question.lower())) - {
        "the",
        "and",
        "docs",
        "documentation",
        "read",
        "how",
        "what",
        "for",
        "with",
        "explain",
        "use",
    }
    results = []
    try:
        async with asyncio.timeout(18):
            text, links = await fetch_page(approved["url"], host)
            pages = [(approved["url"], text)]
            ranked = sorted(
                links,
                key=lambda link: len(
                    terms & set(re.findall(r"[a-z]{3,}", (link[0] + " " + link[1]).lower()))
                ),
                reverse=True,
            )
            if ranked and terms & set(re.findall(r"[a-z]{3,}", ranked[0][1].lower())):
                target = ranked[0][0]
                if urldefrag(target)[0] != urldefrag(approved["url"])[0]:
                    child, _ = await fetch_page(target, host)
                    pages.insert(0, (target, child))
            for url, content in pages:
                lines = content.splitlines()
                windows = [(start, lines[start : start + 24]) for start in range(0, len(lines), 18)]
                windows.sort(
                    key=lambda block: len(
                        terms & set(re.findall(r"[a-z]{3,}", " ".join(block[1]).lower()))
                    ),
                    reverse=True,
                )
                for start, block in windows[:1]:
                    excerpt = "\n".join(block)[:2800]
                    if not excerpt:
                        continue
                    results.append(
                        {
                            "id": "external-doc:"
                            + hashlib.sha256((url + excerpt).encode()).hexdigest()[:24],
                            "path": f"Official documentation: {entry['name']}",
                            "heading": entry["name"],
                            "start_line": start + 1,
                            "end_line": start + len(excerpt.splitlines()),
                            "excerpt": f"Documentation URL: {url}\nExtracted page text (line numbers refer to this extraction):\n{excerpt}",
                            "github_url": url,
                            "commit_sha": "external-documentation",
                            "language": "text",
                        }
                    )
    except (httpx.HTTPError, ValueError, TimeoutError):
        # Repository retrieval continues if external documentation is unavailable.
        return []
    return results
