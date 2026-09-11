"""Reliable Redis list worker. Unacknowledged jobs are reclaimed on restart.

Run one worker process per queue; API local mode uses the same indexing function.
"""

import asyncio

from redis.asyncio import Redis

from app.core.settings import get_settings
from app.db.store import store
from app.ingestion.jobs import run_job


async def main():
    store.initialize()
    if not get_settings().redis_url:
        raise RuntimeError("Set REDIS_URL to start a queue worker.")
    async with Redis.from_url(get_settings().redis_url, decode_responses=True) as redis:
        # Only one queue owner at a time; a renewable lease allows restart recovery.
        lock = redis.lock("repolens:index:worker-lock", timeout=900, blocking_timeout=1)
        if not await lock.acquire():
            raise RuntimeError("Another indexing worker owns this queue.")
        try:
            while await redis.rpoplpush("repolens:index:processing", "repolens:index:pending"):
                pass
            while True:
                await lock.extend(900, replace_ttl=True)
                identifier = await redis.brpoplpush(
                    "repolens:index:pending", "repolens:index:processing", timeout=10
                )
                if identifier:
                    await run_job(identifier)
                    await redis.lrem("repolens:index:processing", 1, identifier)
        finally:
            await lock.release()


if __name__ == "__main__":
    asyncio.run(main())
