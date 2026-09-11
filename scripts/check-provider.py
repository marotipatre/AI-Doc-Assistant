"""Opt-in tiny provider check; never prints credentials or provider error bodies."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from app.core.settings import get_settings
from app.llm.provider import answer, embed

async def main():
    try:
        settings = get_settings()
        if not settings.provider_configured:
            print({"status": "unconfigured", "provider": settings.provider_label})
            raise SystemExit(1)
        if settings.embeddings_enabled:
            vectors = await embed(["RepoLens connectivity check"])
            print({"status": "ok", "dimensions": len(vectors[0])})
        else:
            settings.max_output_tokens = 256
            usage = {}
            source = {"path": "check.txt", "start_line": 1, "end_line": 1, "excerpt": "Connection status: OK."}
            result = "".join([part async for part in answer("What is the connection status? Reply with one short sentence and citation.", [source], [], usage)])
            print({"status": "ok" if result else "failed", "provider": settings.provider_label, **usage})
    except Exception as error:
        print({"status": "failed", "error_type": type(error).__name__, "http_status": getattr(error, "status_code", None), "provider_code": getattr(error, "code", None)})
        raise SystemExit(1) from None

asyncio.run(main())
