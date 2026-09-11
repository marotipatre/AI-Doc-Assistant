# RepoLens: GitHub Repository Intelligence Assistant

## 1. Product Summary

RepoLens is a full-stack developer tool that connects to a GitHub repository, understands its documentation and technical structure, and helps developers work with it through grounded AI answers.

The product is designed around a practical workflow:

1. Connect a public GitHub repository or an authenticated private repository.
2. Inspect and index documentation, manifests, configuration, and relevant source files.
3. Detect the repository's stack, architecture signals, tools, and developer skills.
4. Ask questions about the codebase and receive streamed answers grounded in repository evidence.
5. Inspect exact citations and open the corresponding GitHub source.
6. Export structured repository context for AI-assisted or "vibecoding" workflows.

This should feel like a serious developer workbench, not a generic chatbot.

## 2. Portfolio Goal

The finished project should support this resume claim:

> Built a full-stack GitHub repository intelligence platform with Next.js and FastAPI, using OpenAI streaming generation, GitHub ingestion, pgvector hybrid retrieval, source-level citations, repository skill extraction, incremental indexing, OAuth access, rate limiting, and prompt-injection/SSRF defenses.

The first public demo should be reliable, understandable in under two minutes, and useful without requiring a user to configure a complex system.

## 3. Scope Decisions

- **Frontend:** Existing Next.js 16 App Router application.
- **Backend:** Separate Python FastAPI service. FastAPI owns ingestion, retrieval, model calls, rate limits, and business logic.
- **Repository access:** Public GitHub URL in the first vertical slice. GitHub OAuth and private repositories follow after the public flow is reliable.
- **Database:** PostgreSQL with pgvector.
- **Background work:** Redis-backed indexing jobs, or an equivalent queue abstraction.
- **Model provider:** OpenAI API, called only from FastAPI. Provider and model names must be configurable.
- **Development mode:** Local-first showcase using Docker Compose.
- **Deployment:** Document a later path for a Next.js host, FastAPI host, managed PostgreSQL/pgvector, and Redis worker.
- **Retrieval:** Hybrid semantic and lexical retrieval with repository metadata filters.
- **Answer policy:** Answers must be grounded in retrieved evidence. Insufficient evidence must be shown explicitly rather than hidden behind confident prose.

## 4. Primary Demo Story

A user pastes a repository URL such as a public Next.js, FastAPI, or Solana project.

The interface validates the repository, displays its name and default branch, then shows indexing stages such as fetching, parsing, embedding, and ready. Once indexing finishes, the user sees a repository overview with detected technologies and suggested questions.

The user asks:

> Where is authentication handled, and what should I change to add GitHub login?

The API retrieves relevant files, streams an answer from OpenAI, and attaches citations. The user opens a citation to inspect the excerpt, path, heading, line range, commit, and GitHub link.

The user then opens Skills and sees detected technologies with confidence and evidence. They export the repository context for use in an AI coding workflow.

## 5. Core User Experience

### Repository onboarding

- Paste and validate a GitHub URL.
- Normalize owner, repository, and branch/ref.
- Reject unsupported hosts and malformed URLs.
- Show repository metadata before indexing.
- Allow the user to choose a branch when appropriate.
- Display file counts, warnings, estimated work, and current commit SHA.

### Indexing progress

Show meaningful progress instead of an indefinite spinner:

- Queued
- Fetching repository metadata
- Discovering files
- Parsing documents
- Generating embeddings
- Saving index
- Ready
- Failed with a useful recovery action

Indexing must be idempotent by repository and commit SHA. Repeated requests should not create duplicate chunks or embeddings.

### AI workbench

Use a responsive three-region layout:

- **Navigation rail:** repositories, conversations, overview, skills, sync status.
- **Main workspace:** streaming chat, starter questions, markdown, code blocks, loading states, retries.
- **Inspector:** citations, source excerpts, repository facts, and skill evidence.

On mobile, navigation and inspection panels should become accessible drawers while the composer remains easy to reach.

### Suggested questions

Generate useful prompts from repository signals, including:

- How is this repository structured?
- Where is authentication implemented?
- What should I understand before contributing?
- How do I run the tests?
- How is this deployed?
- What are the highest-risk areas?
- What should I learn first?
- How can I add a new feature following existing patterns?

### Citations and evidence

Every grounded answer should make evidence inspectable. A citation should include:

- Repository and commit SHA
- File path
- Heading or symbol when available
- Line range when available
- Relevant excerpt
- Link to the matching GitHub source

Do not use opaque citations such as `[1]` without an inspector or source link.

### Skills view

Detect skills from manifests, imports, configuration, CI, and documentation. Group them by:

- Languages
- Frontend
- Backend
- Databases and data
- AI and machine learning
- Infrastructure
- Testing
- Workflow and tooling

Each skill must include confidence and evidence paths. Provide an export action that produces structured context suitable for another AI coding tool.

## 6. System Architecture

```text
Next.js web client
        |
        | HTTPS / streaming API
        v
FastAPI application
  |        |         |
  |        |         +--> OpenAI API
  |        +------------> GitHub API
  +---------------------> PostgreSQL + pgvector
        |
        +----------------> Redis / indexing worker
```

Business logic belongs in FastAPI. Next.js may use thin proxy or browser-facing handlers where useful, but it must not duplicate ingestion, retrieval, authorization, or model orchestration.

API keys and GitHub credentials must never be exposed to browser JavaScript.

## 7. Recommended Repository Layout

```text
app/
  layout.tsx
  page.tsx
  globals.css
  api/                         # Thin BFF handlers only when needed
components/
  workbench/
  chat/
  repository/
  skills/
  evidence/
  ui/
lib/
  api-client.ts
  dto.ts
  stream-parser.ts
  formatting.ts
api/
  app/
    main.py
    api/
      health.py
      repositories.py
      jobs.py
      conversations.py
      skills.py
      auth.py
    core/
      settings.py
      security.py
      rate_limits.py
      logging.py
    ingestion/
      github_client.py
      file_filter.py
      parsers.py
      chunking.py
      sync.py
    retrieval/
      hybrid_search.py
      ranking.py
      citations.py
    llm/
      openai_client.py
      prompts.py
      streaming.py
      usage.py
    db/
      models.py
      repositories.py
      migrations/
  tests/
docs/
  PROJECT_PLAN.md
  architecture.md
  threat-model.md
  demo-script.md
  api.md
docker-compose.yml
```

## 8. FastAPI API Contract

### Health

- `GET /health` — liveness check.
- `GET /ready` — readiness check for database, queue, and provider configuration.

### Repositories and indexing

- `POST /v1/repositories` — validate and create a repository record.
- `POST /v1/repositories/{id}/index` — enqueue or start indexing; return a job ID.
- `GET /v1/jobs/{id}` — return stage, progress, counts, warnings, and failure details.
- `POST /v1/repositories/{id}/sync` — compare the default branch and index changed files.
- `GET /v1/repositories/{id}/overview` — return repository facts and evidence.

### Skills and sources

- `GET /v1/repositories/{id}/skills` — return detected skills, confidence, and evidence.
- `GET /v1/repositories/{id}/sources/{source_id}` — return a source excerpt and GitHub link.

### Conversations

- `POST /v1/repositories/{id}/conversations` — create a conversation.
- `GET /v1/repositories/{id}/conversations` — list conversations.
- `POST /v1/conversations/{id}/messages` — validate a question and stream answer/citation events.
- `DELETE /v1/conversations/{id}` — remove a conversation and associated messages.

The OpenAPI schema generated by FastAPI is the source of truth for the web client contract.

## 9. Data Model

Use separate records for:

- `users`
- `github_accounts`
- `repositories`
- `repository_snapshots`
- `sources`
- `chunks`
- `conversations`
- `messages`
- `citations`
- `skills`
- `index_jobs`
- `usage_events`

Important constraints:

- Repository plus commit SHA must be unique for snapshots.
- Chunk identity must be stable so retries are safe.
- Every skill and citation must preserve provenance.
- Conversation access must be authorized against the owning user and repository.
- Do not retain full repository archives unless a retention policy explicitly requires it.
- Never store raw OAuth tokens without encryption and a defined rotation/deletion strategy.

## 10. RAG Pipeline

1. Validate and normalize the GitHub URL.
2. Fetch repository metadata and the selected commit SHA.
3. Fetch the repository tree with bounded file count and total byte limits.
4. Skip binaries, secrets, generated output, vendored directories, and oversized files.
5. Prioritize README files, docs, Markdown/MDX, package manifests, lockfiles, Python metadata, Docker files, CI workflows, and relevant source files.
6. Parse content while preserving Markdown headings, code fences, language, and line offsets.
7. Split content into useful chunks with repository, commit, path, heading, language, and line metadata.
8. Generate embeddings and persist chunks in pgvector.
9. Run hybrid retrieval using vector similarity, lexical matching, path signals, and metadata filters.
10. Deduplicate nearby chunks and enforce a minimum evidence threshold.
11. Send only bounded, relevant context to the model.
12. Stream answer tokens and structured citation events.
13. Store the conversation, usage counters, and citation provenance.

Repository files are untrusted input. The prompt policy must clearly distinguish repository content from system instructions and user instructions.

## 11. Security and Reliability Requirements

### Ingestion boundary

- Allowlist GitHub hosts.
- Prevent SSRF and arbitrary URL fetching.
- Enforce connection, file, byte, and total repository limits.
- Use timeouts and bounded concurrency.
- Sanitize paths and rendered Markdown.
- Skip likely secrets and sensitive files.
- Treat repository content as potentially malicious prompt input.

### Model boundary

- Keep provider keys server-side.
- Use an explicit source-grounded system policy.
- Resist prompt injection inside repository files.
- Do not put secrets into prompts or logs.
- Enforce token budgets and request timeouts.
- Retry only safe transient failures.
- Map provider failures to useful UI states.

### Application boundary

- Add per-user and per-repository rate limits.
- Add concurrency limits around GitHub and OpenAI calls.
- Authorize every repository, conversation, job, and source request.
- Encrypt or avoid long-term storage of OAuth tokens.
- Add request IDs and structured logs.
- Support job cancellation and partial-failure reporting.
- Delete all indexed data when a repository is removed.

## 12. Visual Direction

The interface should feel intentional and distinct from a default AI chat application.

- Warm off-white background with charcoal text.
- Electric green for primary actions and ready states.
- Restrained cyan accents for evidence and technical metadata.
- Expressive display typography paired with a readable text face.
- Monospace treatment for paths, commands, versions, and code.
- Compact, information-dense panels suitable for repeated developer use.
- Cards limited to genuinely framed tools and repeated items.
- Meaningful motion for indexing, streamed answers, and panel transitions.
- Reduced-motion support and clear focus states.
- Accessible labels and tooltips for icon-only buttons.
- Strong empty, loading, error, stale-index, and insufficient-evidence states.

Do not use a generic purple-on-white dashboard, oversized marketing hero, or decorative UI that competes with repository evidence.

## 13. Implementation Phases

### Phase 0: Foundation

1. Read the version-specific Next.js guidance under `node_modules/next/dist/docs/` before implementation.
2. Preserve the existing Next.js App Router and `pnpm` workflow.
3. Create the FastAPI service with typed settings, structured logging, CORS, and health checks.
4. Add Docker Compose for PostgreSQL/pgvector and Redis if required by the worker design.
5. Add `.env.example` files without real secrets.
6. Establish the FastAPI OpenAPI contract and a typed web API client.

### Phase 1: First vertical slice

1. Validate a public GitHub repository URL.
2. Fetch metadata and bounded file contents.
3. Parse, chunk, embed, and persist a repository snapshot.
4. Implement hybrid retrieval.
5. Stream a grounded answer with structured citations.
6. Replace the starter page with the repository workbench.
7. Support the full flow: connect, index, ask, inspect citation.

### Phase 2: Repository intelligence

1. Add repository overview and architecture signals.
2. Add detected skills with evidence and confidence.
3. Add starter questions based on repository signals.
4. Add evidence inspector and source links.
5. Add conversation history and Markdown export.
6. Add incremental repository sync.

### Phase 3: OAuth and private repositories

1. Add GitHub OAuth with least-privilege scopes.
2. Let users select repositories instead of indexing everything.
3. Add encrypted token handling and deletion.
4. Enforce authorization on every private-repository request.
5. Add user-level usage limits and rate-limit feedback.

### Phase 4: Showcase and deployment

1. Add a seeded fixture repository so the demo works without expensive indexing.
2. Add browser smoke tests and responsive accessibility checks.
3. Add retrieval evaluation with golden questions.
4. Add threat-model and deployment documentation.
5. Document deployment of Next.js, FastAPI, PostgreSQL/pgvector, and the worker.
6. Record a short demo covering onboarding, indexing, cited answers, Skills, and sync.

## 14. Testing and Evaluation

### Frontend

- `pnpm lint`
- `pnpm build`
- Browser smoke test for connect, index, chat, citation, and Skills.
- Responsive tests for desktop and mobile layouts.
- Keyboard navigation and reduced-motion checks.

### Backend

Use Ruff, formatting, type checks, and pytest for:

- URL validation and GitHub host restrictions.
- File filtering and size limits.
- Chunk metadata and line offsets.
- Idempotent indexing.
- Retrieval ranking and evidence thresholds.
- Citation construction.
- Streaming event format.
- Authorization and private-repository access.
- Rate limiting and provider failures.
- Job retries, cancellation, and partial failures.

### Retrieval quality

Create a golden question set for a seeded repository. Track:

- Retrieval recall.
- Citation precision.
- Answer groundedness.
- Latency.
- Token usage.
- Failure rate.

Include unanswerable questions that must produce an evidence-limited response.

### Security tests

Test SSRF and host validation, oversized files, path-like edge cases, Markdown/script sanitization, prompt injection in repository content, token redaction, and cross-user access.

## 15. Agent Handoff Rules

Coding agents should follow this order:

1. Scaffold the API, local services, settings, health checks, and web/API connectivity.
2. Implement public GitHub validation and fetching.
3. Implement parsing, chunking, embeddings, persistence, and progress jobs.
4. Implement retrieval, streaming answers, and citations.
5. Build the responsive workbench and connect the first vertical slice.
6. Add overview, Skills, evidence inspection, and conversations.
7. Add OAuth, private repositories, synchronization, and security hardening.
8. Add fixture mode, evaluation tests, deployment docs, and visual polish.

Before editing Next.js code, consult the version-specific documentation required by `AGENTS.md`. Keep changes focused, preserve existing user changes, and validate each slice with the narrowest relevant test or build command.

Do not begin billing, autonomous code changes, IDE extensions, or multi-provider support before the public-repository cited-answer path is reliable.

## 16. Explicit Non-Goals

The first showcase does not need:

- Autonomous code modifications.
- Automatic pull requests.
- Full IDE extension support.
- Billing or enterprise SSO.
- Model fine-tuning.
- Automatic indexing of every accessible repository.
- Uncited answers presented as authoritative.
