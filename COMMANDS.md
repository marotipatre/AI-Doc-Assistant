# Local server commands

Run these commands from two separate terminal tabs. Keep both tabs open while using the app.

## 1. Start FastAPI (backend)

```bash
cd /Users/maroti/Crypto/dev-assist
pnpm run dev:api
```

## 2. Start Next.js (frontend)

```bash
cd /Users/maroti/Crypto/dev-assist
pnpm dev --hostname 127.0.0.1
```

Open http://localhost:3000 for the home page, http://localhost:3000/guide for the guide, or http://localhost:3000/workspace for your repositories.

## Restart or stop

Press **Ctrl+C** in each server's terminal to stop it. Run its start command again to restart it.

If a server is running in the background, find its process ID:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3000 -sTCP:LISTEN
```

Stop the project process using its PID (replace `12345` with the number shown):

```bash
kill -TERM 12345
```

FastAPI reload mode can show two Python PIDs. Stop both, then run the start command again.

## Set up Groq / restart after changing a key

Save your key in the project root `.env`:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b
RETRIEVAL_MODE=lexical
```

Restart FastAPI and refresh the app. A key change alone does not require reindexing in keyword-search mode. Click **Sync repository** when the repository changes.

Indexing, sources, skills, and exports do not use AI credits. A model request runs when you press Send. Groq rate limits can still apply; wait for the displayed cooldown before retrying.

Leave `REDIS_URL=` empty for this local setup. No separate Redis server or worker is needed.

## If Gemini says quota or rate limit exhausted

Indexing saves your repository with keyword search when embedding quota runs out. Sources and skills remain available. Completed embedding batches are retained; click **Sync repository** once quota is available to finish semantic search.

Check your project's model limits in [Google AI Studio](https://aistudio.google.com/usage). A server restart or a new key in the same Google project does not reset quota. Short-term limits require waiting; daily limits require waiting for the daily reset. AI chat requires available quota for the configured chat model as well.

## Check the backend

```bash
curl http://127.0.0.1:8000/health
```

The frontend should open at http://localhost:3000 and the API documentation at http://127.0.0.1:8000/docs.
