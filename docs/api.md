# FastAPI contract

The running API's [OpenAPI schema](http://localhost:8000/openapi.json) and [interactive documentation](http://localhost:8000/docs) are the authoritative contract. This document describes the browser's main workflow. Requests from Next.js use `/api/backend` as a same-origin prefix; the server forwards them to `FASTAPI_URL`.

## Repository workflow

| Method | API path | Purpose |
| --- | --- | --- |
| GET | `/health` | Process liveness. |
| GET | `/ready` | Dependency and provider readiness. |
| GET | `/v1/repositories` | List repositories visible to the current session. |
| POST | `/v1/repositories` | Validate a GitHub URL and return repository metadata. |
| POST | `/v1/repositories/{id}/index` | Start indexing and return a job. |
| POST | `/v1/repositories/{id}/sync` | Check for a newer commit and synchronize. |
| GET | `/v1/jobs/{id}` | Poll stage, progress, counts, warnings, and errors. |
| GET | `/v1/repositories/{id}/overview` | Repository facts, architecture, technologies, and suggested questions. |
| GET | `/v1/repositories/{id}/skills` | Detected skills with confidence and source evidence. |
| GET | `/v1/repositories/{id}/sources` | Source excerpts for the current repository snapshot. |
| GET | `/v1/repositories/{id}/sources/{source_id}` | Inspect a specific source. |
| GET | `/v1/repositories/{id}/export` | Export structured repository context as JSON (the web client also generates Markdown). |

Connect request:

```json
{"url":"https://github.com/owner/repository","branch":"main"}
```

`branch` is optional. A repository includes its stable `id`, `full_name`, `default_branch`, `commit_sha`, `status`, file/chunk counts, and demo/private flags. Save the returned identifier instead of deriving one from the URL.

A job includes `id`, `repository_id`, `status`, `stage`, integer `progress`, `files_processed`, `total_files`, `warnings`, and nullable `error`. Poll until the job reaches a terminal state; a nonempty warning list does not necessarily mean indexing failed. Stages cover queued, fetching, discovering, parsing, embedding, saving, ready, failed, and cancelled.

## Conversations and streaming

| Method | API path | Purpose |
| --- | --- | --- |
| POST | `/v1/repositories/{id}/conversations` | Create a conversation. |
| GET | `/v1/repositories/{id}/conversations` | List repository conversations. |
| GET | `/v1/conversations/{id}` | Read a conversation and its stored messages. |
| POST | `/v1/conversations/{id}/messages` | Send a question and stream the answer. |
| DELETE | `/v1/conversations/{id}` | Delete the conversation and associated messages. |

Message requests use `{"content":"Where is authentication handled?"}`. The response is a server-sent event stream, consumed with `fetch` because the endpoint is POST. Every record has an `event:` discriminator and a `data:` JSON object; records are separated by a blank line.

```text
event: token
data: {"text":"Authentication is handled "}

event: citations
data: {"sources":[...]}

event: done
data: {"message":{"id":"...","role":"assistant","content":"...","citations":[],"created_at":"..."}}

```

An `error` event carries a user-readable `message`. Clients must process partial frames, multiline SSE data, and a final frame without assuming each network chunk contains one complete event. Abort the request to stop reading the stream. A completed answer's saved message is authoritative for final content and citations.

## Evidence shape

Each source includes `id`, `path`, `heading`, `start_line`, `end_line`, `excerpt`, `commit_sha`, `github_url`, and `language`. Line ranges are inclusive. Real sources link to the indexed commit rather than a moving default branch. Illustrative fixtures may have an empty GitHub URL; the client must label them and avoid constructing a purported real source link.

Skills include `id`, `name`, `category`, `confidence` (0–1), and an `evidence` array containing the same source objects. Confidence is a detection score, not a probability that a generated answer is correct.

## Modes and failures

The frontend fixture adapter implements this interface locally for a deliberately fictional repository and never silently falls back from live API errors. API mode connects to FastAPI. The selected provider (`LLM_PROVIDER=groq` by default) and its API key control whether the backend generates answers or returns labeled source extracts. Indexing defaults to lexical search with no AI calls. Hybrid embeddings are opt-in for Gemini/OpenAI.

Use the browser's same-origin session cookie throughout a flow. Direct scripts must retain cookies between calls. Invalid inputs, unavailable dependencies, rate limits, and provider failures should remain visible; do not turn an error into a fabricated successful response. The live OpenAPI schema documents additional authentication, deletion, and job-control endpoints.

## Authentication and deletion

`GET /v1/auth/session` reports configuration and sign-in state. `GET /v1/auth/github` starts public identity sign-in; `?private=true` requests private repository access. `GET /v1/auth/github/callback` verifies state and exchanges the authorization code. `GET /v1/auth/repositories` lists up to 100 accessible repositories for selection. `POST /v1/auth/logout` removes retained credentials and private indexed data. `POST /v1/jobs/{id}/cancel` cancels an indexing job. `DELETE /v1/repositories/{id}` removes its indexed data and conversations without modifying GitHub.

`GET /ready` reports `provider_name`, `model`, and `embedding_model` alongside provider configuration state. An embedding identity includes provider, model, and vector dimensions, preventing semantic retrieval from mixing incompatible vector spaces. Sync repositories after changing provider or embedding model.

## Runtime configuration

`GET /v1/runtime` returns safe display status: `provider`, `model`, `configured`, `retrieval_mode`, `ai_policy`, `max_output_tokens`, and `answer_cache_enabled`. It performs no provider probe and exposes no keys.

Assistant messages include `cached: boolean`. A true value means a completed answer was reused without generation. Cache keys include owner, repository snapshot, evidence, question, model, and conversation context; errors and partial responses are never reused.
