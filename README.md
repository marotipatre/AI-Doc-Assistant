# RepoLens

Create, edit and download `SKILL.md` with setup instructions, project rules and verification checks for a GitHub repository.

Choose a repository explicitly on each new visit. The navbar provides GitHub connection and account controls. The editor supports direct changes and a writing assistant that proposes replacements or new sections for review. Suggestions are applied only when requested; downloads contain the current edited document. Default repository reading and editing require no provider calls; writing suggestions use the configured provider when submitted. The example uses a fixed, labeled suggestion.

Drafts are held in the current workspace session. Download before leaving, switching repositories or disconnecting.

## Repository questions and developer documentation

Open **Ask repository** after choosing a repository. Answers retrieve repository excerpts and stream with citations. Ask a question naming a detected technology (for example, “Explain FastAPI dependencies using the docs”) to include relevant passages from approved official documentation pages.

The editor lists documentation for detected technologies and includes the links in SKILL.md. Unmapped dependencies use labeled package-registry links. Documentation links do not imply that the external pages match the project’s pinned version.

See [RAG architecture and résumé wording](docs/RAG_ARCHITECTURE.md) for implementation details, limits, and verified claims.

## Start the fixture experience

Requires Node.js 22 and pnpm 10.

```sh
pnpm install
pnpm dev
```

Open [localhost:3000](http://localhost:3000) for the landing page, [/guide](http://localhost:3000/guide) for a walkthrough, or [/workspace?demo=1](http://localhost:3000/workspace?demo=1) to explore the sample. The demo uses an explicitly labeled fictional repository with illustrative source excerpts. It needs no API keys or backend. Use the visible Demo switch to enter live mode or connect a repository directly.

## Run the complete local stack

Requires Docker with Compose v2.24 or later.

```sh
cp .env.example .env
docker compose up --build
```

Open [localhost:3000](http://localhost:3000) and choose the live API workspace. FastAPI documentation is at [localhost:8000/docs](http://localhost:8000/docs); readiness is at [localhost:8000/ready](http://localhost:8000/ready).

Compose starts Next.js, FastAPI, the indexing worker, PostgreSQL 17 with pgvector, and Redis. Named volumes preserve server data and queued work across restarts. Web and API ports bind to loopback; database and Redis ports are not published. Run `docker compose down` to stop the services while retaining their volumes.

No model key is needed for the focused application. The following provider settings apply only to retained backend AI endpoints. Set `GROQ_API_KEY` in `.env` for those endpoints. Defaults are `LLM_PROVIDER=groq`, `GROQ_MODEL=openai/gpt-oss-20b`, and `RETRIEVAL_MODE=lexical`. Indexing, source search, technology detection, exports, suggested prompts, and walkthroughs make no model calls. Without a key, the app still connects and indexes repositories and returns labeled evidence previews.

AI runs only when a user submits a question. Answers use at most five deduplicated excerpts (7,000 characters total), 2,000 characters of recent conversation, and a 1,200-token output limit. Groq uses low reasoning effort for GPT-OSS, with no automatic retries, extra agent loops, or hosted tools. Quota errors trigger a bounded cooldown using Groq's Retry-After header.

Successful identical requests can reuse an answer for one hour. Reuse is scoped to the user, repository snapshot, exact question, bounded conversation, evidence, provider/model, and prompt policy. Failed or interrupted streams are never cached. The cache and duplicate-request lock are bounded and process-local; multiple API processes do not share them. Settings can disable reuse with `ANSWER_CACHE_ENABLED=false`. Shorter context limits save credits but can omit details; inspect the cited sources or ask a focused follow-up when needed.

Gemini and OpenAI remain explicit alternatives. Set `LLM_PROVIDER=gemini` or `openai` and that provider's key. Optional semantic search requires `RETRIEVAL_MODE=hybrid` with Gemini or OpenAI and a repository sync; Groq always uses keyword search. Previously completed embedding batches survive quota failures and a later sync fills missing vectors. Existing keys for unselected providers are ignored. The PostgreSQL vector column expects 1,536 dimensions.

Restart FastAPI (and the worker with Redis) after editing `.env`. `GITHUB_TOKEN` is optional for public repositories. Never put keys in `NEXT_PUBLIC_*` variables. See [COMMANDS.md](COMMANDS.md) for daily commands.

## Develop FastAPI without Docker

Requires Python 3.13. From the project root:

```sh
python3 -m venv api/.venv
api/.venv/bin/pip install -r api/requirements.txt
cp .env.example .env
api/.venv/bin/uvicorn app.main:app --app-dir api --reload --port 8000
```

Run `pnpm dev` in another terminal. The default `FASTAPI_URL` is `http://127.0.0.1:8000`; requests are forwarded by a thin same-origin Next.js route. The API reads the root `.env` when launched from the root with this command.

With `REDIS_URL` empty, indexing runs inside the API process. SQLite is the explicit lightweight database fallback; it does not provide pgvector. Use Compose for PostgreSQL vector retrieval and the separate worker. If running a worker manually, launch `python -m app.worker` from `api/` with the same environment as the API.

## Configuration

All variables and defaults are listed in [.env.example](.env.example). `FASTAPI_URL` belongs to the Next.js server. Provider, GitHub, database, and queue settings belong to FastAPI. Compose overrides database and queue URLs to internal service names. Set a persistent `SESSION_SECRET` before saving live repository work: the development fallback creates a new signing secret on API restart, invalidating previous anonymous sessions.

For GitHub OAuth, create a GitHub OAuth application whose callback matches `GITHUB_CALLBACK_URL`, then set `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `TOKEN_ENCRYPTION_KEY`, and `SESSION_SECRET`. Generate a Fernet encryption key using the installed API environment:

```sh
api/.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
api/.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Use the first output as `TOKEN_ENCRYPTION_KEY` and the second as `SESSION_SECRET`. In Workspace settings, use **Enable private repository access** to request private access explicitly; the Connect dialog can then list repositories available to your GitHub account. This local showcase is not a production multi-tenant deployment; read the [threat model](docs/threat-model.md) before enabling private repositories or exposing it publicly.

## Verify

```sh
pnpm lint
pnpm build
pnpm typecheck
pnpm exec playwright install chromium
pnpm test:e2e
```

Backend checks, from `api/` after activating its virtual environment:

```sh
ruff check app tests
ruff format --check app tests
mypy app
pytest
```

The production script uses Next.js’s supported webpack builder. Browser tests exercise the deterministic fixture flow and responsive states. They do not spend provider credits or prove real GitHub ingestion. Backend tests cover ingestion boundaries, indexing, retrieval, and the API contract; inspect their fixtures and assertions for the exact scope. Live GitHub, Groq/Gemini/OpenAI, OAuth, and Docker deployment paths need their corresponding services and credentials for integration verification.

## Project map

- `app/`, `components/`, `lib/`: responsive workbench, typed client, and streaming parser.
- `api/`: FastAPI, GitHub ingestion, retrieval, provider calls, storage, and worker.
- `tests/`: browser smoke checks.
- [Architecture](docs/architecture.md), [API contract](docs/api.md), [threat model](docs/threat-model.md), [demo script](docs/demo-script.md), and [original plan](docs/PROJECT_PLAN.md).

The public-repository workflow is the showcase's main path. Source coverage is intentionally bounded; indexing a large repository is not the same as understanding every file. Fixture content is illustrative, and missing evidence is surfaced rather than filled with invented repository details.

## Gemini configuration

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

Only the API service needs this key. Keep `REDIS_URL=` empty for in-process local indexing; Compose supplies Redis automatically. After saving your key, restart FastAPI with the command above and click **Sync repository**. With Docker, run `docker compose up -d --build api worker` to recreate services with the changed environment.

`api/.venv/bin/python scripts/check-provider.py` makes one small chat request (or an embedding request when hybrid search is enabled) and reports its status without printing credentials. Free-tier quotas and model access depend on the Gemini project. Quota, authentication, blocked-response, and incomplete-stream errors are surfaced without falling back to a different provider.

The backend uses Gemini's [native streaming API](https://ai.google.dev/api/generate-content) and [synchronous embedding endpoint](https://ai.google.dev/api/embeddings), with document/query task types and normalized 1,536-dimensional vectors. No additional Python package is required beyond the existing HTTPX dependency.
