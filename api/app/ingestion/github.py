import asyncio
import base64
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from app.core.settings import get_settings

GITHUB_SEMAPHORE = asyncio.Semaphore(6)


class GitHub:
    def __init__(self, token: str = ""):
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RepoLens/1.0",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def get(self, path: str) -> Any:
        # Paths are constructed from validated names, never repository URLs.
        if not path.startswith("/") or path.startswith("//"):
            raise HTTPException(422, "Invalid GitHub API path.")
        async with (
            GITHUB_SEMAPHORE,
            httpx.AsyncClient(
                base_url="https://api.github.com",
                headers=self.headers,
                timeout=25,
                follow_redirects=False,
            ) as client,
        ):
            for attempt in range(3):
                async with client.stream("GET", path) as incoming:
                    size = 0
                    body = bytearray()
                    async for part in incoming.aiter_bytes():
                        size += len(part)
                        if size > 18_000_000:
                            raise HTTPException(
                                413, "GitHub response exceeded the discovery size limit."
                            )
                        body.extend(part)
                    response = httpx.Response(
                        incoming.status_code,
                        headers={
                            key: value
                            for key, value in incoming.headers.items()
                            if key.lower() not in {"content-encoding", "content-length"}
                        },
                        content=bytes(body),
                    )
                if response.status_code not in (502, 503, 504) or attempt == 2:
                    break
                await asyncio.sleep(0.4 * (attempt + 1))
        if response.status_code == 404:
            raise HTTPException(
                404, "Repository or branch not found. Private repositories require GitHub sign-in."
            )
        if response.status_code in (401, 403, 429):
            raise HTTPException(
                429 if response.status_code != 401 else 401,
                "GitHub access was denied or its rate limit was reached. Sign in or retry later.",
            )
        if response.status_code != 200:
            raise HTTPException(
                502, f"GitHub could not complete this request ({response.status_code})."
            )
        if len(response.content) > 18_000_000:
            raise HTTPException(413, "GitHub response exceeded the discovery size limit.")
        return response.json()

    async def metadata(self, owner: str, name: str, branch: str | None = None) -> tuple[dict, str]:
        metadata = await self.get(f"/repos/{owner}/{name}")
        ref = branch or metadata["default_branch"]
        commit = await self.get(f"/repos/{owner}/{name}/commits/{quote(ref, safe='')}")
        metadata["selected_branch"] = ref
        return metadata, commit["sha"]

    async def tree(self, full_name: str, commit: str) -> dict:
        return await self.get(f"/repos/{full_name}/git/trees/{commit}?recursive=1")

    async def blob(self, full_name: str, sha: str) -> str | None:
        result = await self.get(f"/repos/{full_name}/git/blobs/{quote(sha, safe='')}")
        if (
            result.get("size", 0) > get_settings().max_file_bytes
            or result.get("encoding") != "base64"
        ):
            return None
        raw = base64.b64decode(result["content"], validate=False)
        if len(raw) > get_settings().max_file_bytes or b"\x00" in raw:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
