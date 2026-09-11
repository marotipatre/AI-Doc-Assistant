# RAG implementation and résumé wording

RepoLens uses Next.js / React / TypeScript for the interface and asynchronous FastAPI / Python for ingestion, retrieval and streamed answers. This is implemented retrieval-augmented generation, not just a static export or a model prompt with no retrieval.

## Repository questions

1. GitHub ingestion reads bounded, filtered repository files and splits them into overlapping line-based chunks. Each chunk retains file path, commit and line provenance.
2. Owner-scoped repository/conversation authorization runs before retrieval.
3. `api/app/retrieval/search.py` ranks relevant chunks. Default lexical retrieval avoids embedding charges. Optional hybrid retrieval combines lexical ranking with embeddings and reciprocal-rank fusion; PostgreSQL uses pgvector similarity search. Groq uses lexical retrieval.
4. Retrieved excerpts and bounded conversation history are passed to the configured external provider (Groq, Gemini or OpenAI). No relevant source means an explicit insufficient-context response.
5. FastAPI streams tokens and citations through Server-Sent Events. Next.js displays the answer and expandable source references on `/workspace/questions`. Completed answers can be added to the editable SKILL.md.

## Technology documentation

- `api/app/documentation_catalog.json` maps 37 recognized technologies to curated official references: languages, frameworks, providers/model families, blockchain tools, databases, infrastructure and testing tools.
- Detection uses repository content and filenames; dependency discovery reads complete package.json, pyproject.toml, requirements.txt and Cargo.toml excerpts. Solidity files are eligible for ingestion.
- Unmapped dependencies receive labeled npm/PyPI/crates registry links, not invented documentation URLs. This is an extensible catalog, not universal technology recognition. A match indicates a repository reference, not proof of production usage.
- The UI and SKILL.md include documentation links and the repository files that identified the technology.
- Simple “where are the docs?” questions retrieve link entries and return deterministic references without a generation call.
- Explanatory questions naming a recognized technology can retrieve actual external documentation text. The fetcher starts at its catalog URL, follows at most one relevant same-host link, extracts text, ranks bounded windows and adds passages to the model context. Answers distinguish repository implementation from library documentation.
- Fetches are HTTPS-only, same-approved-host, bounded to 750 KB per response, at most four redirect attempts, two pages, an 18-second retrieval budget, and three simultaneous fetches. A bounded 48-page in-process cache retains content for one hour. External failures fall back to repository sources.
- External line numbers refer to extracted text, not GitHub source lines. Default documentation pages may describe newer versions; users must compare against repository dependencies. JavaScript-only documentation and cross-host redirects may not be retrievable.

## Concurrency, limits and credentials

FastAPI endpoints use async external I/O and SSE. Provider calls are semaphore-limited; Groq permits two in-flight calls and respects provider cooldown after 429 responses. Per-user/per-repository request limits use Redis when configured or an in-process fallback. Answer caching and per-key locks can coalesce duplicate generation requests. Default context/output budgets limit work per request.

GitHub OAuth uses state and PKCE, signed HttpOnly sessions and encrypted retained tokens. Ingestion restricts hosts and paths, skips sensitive filenames/content patterns, and imposes size limits. These are implemented controls, not a claim of a completed security audit. Process-local caches/semaphores do not coordinate multiple workers; a high-scale production throughput claim needs deployment measurements.

## Validation and defensible résumé bullets

The backend suite includes retrieval, quota, interrupted-stream, authorization, documentation link, bounded fetch, redirect rejection and concurrency tests. Documentation concurrency is tested with mocked network delays (peak three), not a real-provider throughput benchmark. No paid model calls were made for this verification.

Suggested résumé wording:

- Built a full-stack RAG application with Next.js and FastAPI to answer developer questions using retrieved repository documentation and official technology references, with streamed responses and source citations.
- Implemented asynchronous provider integrations, bounded concurrency, rate limiting, response caching, and GitHub OAuth–protected repository ingestion; added an editable SKILL.md export with repository-specific documentation links.

Avoid “instantly,” unqualified “securely,” and “highly concurrent” performance claims without measurements. Optional hybrid/vector retrieval is implemented, but the default deployment is lexical RAG; do not claim vector search is active unless enabled and indexed.
