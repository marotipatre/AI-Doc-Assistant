"""Native Gemini REST transport. Keys stay in headers; error bodies are never surfaced."""

import asyncio
import json
import math
from collections.abc import AsyncIterator
from typing import Literal

import httpx

from app.core.settings import get_settings

ORIGIN = "https://generativelanguage.googleapis.com/v1beta/"


class GeminiError(Exception):
    def __init__(self, status_code: int = 502):
        self.status_code = status_code
        super().__init__("Gemini request failed")


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=ORIGIN,
        headers={"x-goog-api-key": get_settings().gemini_api_key},
        timeout=httpx.Timeout(55, connect=15),
        follow_redirects=False,
    )


async def embed(texts: list[str], task: Literal["document", "query"]) -> list[list[float]]:
    settings = get_settings()
    model = "models/" + settings.gemini_embedding_model.removeprefix("models/")
    result = []
    async with client() as http:
        for start in range(0, len(texts), 16):
            batch = texts[start : start + 16]
            body = {
                "requests": [
                    {
                        "model": model,
                        "content": {"parts": [{"text": value}]},
                        "taskType": "RETRIEVAL_QUERY" if task == "query" else "RETRIEVAL_DOCUMENT",
                        "outputDimensionality": settings.embedding_dimensions,
                    }
                    for value in batch
                ]
            }
            # Only retry safe transient failures; quota errors remain actionable.
            for attempt in range(2):
                response = await http.post(f"{model}:batchEmbedContents", json=body)
                if response.status_code not in (500, 502, 503, 504) or attempt:
                    break
                await asyncio.sleep(0.5)
            if response.status_code != 200:
                raise GeminiError(response.status_code)
            values = response.json().get("embeddings", [])
            if len(values) != len(batch):
                raise GeminiError()
            for item in values:
                vector = item.get("values", [])
                if len(vector) != settings.embedding_dimensions or not all(
                    isinstance(v, (int, float)) and math.isfinite(v) for v in vector
                ):
                    raise GeminiError()
                magnitude = math.sqrt(sum(v * v for v in vector))
                if magnitude == 0:
                    raise GeminiError()
                # Reduced-dimensional gemini-embedding-001 results need normalization.
                result.append([v / magnitude for v in vector])
    return result


async def events(response: httpx.Response) -> AsyncIterator[dict]:
    lines: list[str] = []
    async for line in response.aiter_lines():
        if not line:
            if lines:
                yield json.loads("\n".join(lines))
                lines = []
        elif line.startswith("data:"):
            lines.append(line[5:].lstrip(" "))
    if lines:
        yield json.loads("\n".join(lines))


async def answer(
    question: str, evidence: str, history: list[dict], policy: str, usage: dict
) -> AsyncIterator[str]:
    settings = get_settings()
    contents = [
        {
            "role": "model" if message["role"] == "assistant" else "user",
            "parts": [{"text": message["content"][:5000]}],
        }
        for message in history[-6:]
    ]
    contents.append(
        {
            "role": "user",
            "parts": [
                {"text": f"QUESTION:\n{question}\n\nUNTRUSTED REPOSITORY EVIDENCE:\n{evidence}"}
            ],
        }
    )
    config: dict = {"maxOutputTokens": settings.max_output_tokens, "temperature": 0.2}
    if settings.gemini_model.removeprefix("models/").startswith("gemini-2.5-flash"):
        config["thinkingConfig"] = {"thinkingBudget": 0}
    body = {
        "systemInstruction": {"parts": [{"text": policy}]},
        "contents": contents,
        "generationConfig": config,
    }
    model = "models/" + settings.gemini_model.removeprefix("models/")
    completed = False
    emitted = False
    async with client() as http:
        async with http.stream(
            "POST", f"{model}:streamGenerateContent?alt=sse", json=body
        ) as response:
            if response.status_code != 200:
                raise GeminiError(response.status_code)
            async for event in events(response):
                if event.get("error") or event.get("promptFeedback", {}).get("blockReason"):
                    raise GeminiError()
                metadata = event.get("usageMetadata", {})
                if metadata:
                    thoughts = metadata.get("thoughtsTokenCount", 0)
                    usage.update(
                        input_tokens=metadata.get("promptTokenCount", 0),
                        output_tokens=metadata.get("candidatesTokenCount", 0) + thoughts,
                        thinking_tokens=thoughts,
                    )
                candidates = event.get("candidates", [])
                if not candidates:
                    continue
                candidate = candidates[0]
                for part in candidate.get("content", {}).get("parts", []):
                    if part.get("text") and not part.get("thought"):
                        emitted = True
                        yield part["text"]
                finish = candidate.get("finishReason")
                if finish and finish != "STOP":
                    # A blocked/truncated response must not become a saved successful answer.
                    raise GeminiError()
                if finish == "STOP":
                    completed = True
    if not completed or not emitted:
        raise GeminiError()
