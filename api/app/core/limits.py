import asyncio
import time
from collections import defaultdict, deque

from fastapi import HTTPException
from redis.asyncio import Redis

from app.core.settings import get_settings

WINDOWS: dict[str, deque] = defaultdict(deque)
LOCK = asyncio.Lock()


async def limit(key: str, maximum: int, seconds: int = 60):
    if get_settings().redis_url:
        async with Redis.from_url(get_settings().redis_url) as redis:
            bucket = f"repolens:limit:{key}:{int(time.time()) // seconds}"
            count = await redis.incr(bucket)
            if count == 1:
                await redis.expire(bucket, seconds + 1)
            if count > maximum:
                raise HTTPException(
                    429,
                    "Rate limit reached. Please wait before trying again.",
                    headers={"Retry-After": str(seconds)},
                )
        return
    async with LOCK:
        timestamp = time.monotonic()
        window = WINDOWS[key]
        while window and window[0] < timestamp - seconds:
            window.popleft()
        if len(window) >= maximum:
            raise HTTPException(
                429,
                "Rate limit reached. Please wait before trying again.",
                headers={"Retry-After": str(seconds)},
            )
        window.append(timestamp)
        if len(WINDOWS) > 10_000:
            for old_key in list(WINDOWS):
                if not WINDOWS[old_key] or WINDOWS[old_key][-1] < timestamp - 3600:
                    del WINDOWS[old_key]
