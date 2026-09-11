"""Single, bounded Groq request per answer; no automatic retries or external tools."""

import asyncio
import hashlib
import json
import time

import httpx

from app.core.settings import get_settings

ORIGIN = "https://api.groq.com/openai/v1/"
SEMAPHORE = asyncio.Semaphore(2)
COOLDOWNS: dict[str, float] = {}


class GroqError(Exception):
    def __init__(self, status_code: int = 502, retry_after: int = 0):
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__("Groq request could not complete")


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=ORIGIN,
        headers={"Authorization": f"Bearer {get_settings().groq_api_key}"},
        timeout=httpx.Timeout(60, connect=10),
        follow_redirects=False,
    )


async def answer(question: str, evidence: str, history: list[dict], policy: str, usage: dict):
    settings = get_settings()
    identity = hashlib.sha256((settings.groq_api_key + settings.groq_model).encode()).hexdigest()
    messages = [{"role": "system", "content": policy}]
    messages.extend({"role": item["role"], "content": item["content"]} for item in history)
    messages.append(
        {
            "role": "user",
            "content": f"QUESTION:\n{question}\n\nUNTRUSTED REPOSITORY EVIDENCE:\n{evidence}",
        }
    )
    body: dict = {
        "model": settings.groq_model,
        "messages": messages,
        "max_completion_tokens": settings.max_output_tokens,
        "temperature": 0.2,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if settings.groq_model.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = "low"
        body["include_reasoning"] = False
    async with SEMAPHORE:
        remaining = COOLDOWNS.get(identity, 0) - time.monotonic()
        if remaining > 0:
            raise GroqError(429, int(remaining) + 1)
        async with client() as http, http.stream("POST", "chat/completions", json=body) as response:
            if response.status_code != 200:
                retry_after = 0
                if response.status_code == 429:
                    try:
                        retry_after = max(
                            1, min(3600, int(float(response.headers.get("retry-after", "60"))))
                        )
                    except (ValueError, OverflowError):
                        retry_after = 60
                    COOLDOWNS.clear()
                    COOLDOWNS[identity] = time.monotonic() + retry_after
                raise GroqError(response.status_code, retry_after)
            finished = False
            emitted = False
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    break
                try:
                    event = json.loads(raw)
                except (ValueError, TypeError):
                    raise GroqError() from None
                if event.get("error"):
                    raise GroqError()
                counts = event.get("usage") or event.get("x_groq", {}).get("usage")
                if counts:
                    usage.update(
                        input_tokens=counts.get("prompt_tokens", 0),
                        output_tokens=counts.get("completion_tokens", 0),
                    )
                for choice in event.get("choices", []):
                    delta = choice.get("delta", {}).get("content")
                    if delta:
                        emitted = True
                        yield delta
                    reason = choice.get("finish_reason")
                    if reason:
                        if reason != "stop":
                            raise GroqError(422)
                        finished = True
            if not finished or not emitted:
                raise GroqError()
