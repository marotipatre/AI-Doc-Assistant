import type { Overview, Repository, Skill, Source } from "./dto";

/** Illustrative fixtures, authored for this demo. These are not fetched GitHub files. */
export const demoRepository: Repository = {
  id: "demo-repolens",
  owner: "repolens",
  name: "repolens",
  full_name: "repolens/repolens",
  description:
    "GitHub repository intelligence. Understand the code. Find your next move.",
  default_branch: "main",
  commit_sha: "demo-snapshot",
  stars: 0,
  language: "TypeScript",
  status: "ready",
  file_count: 8,
  chunk_count: 8,
  indexed_at: "2026-09-09T06:00:00.000Z",
  html_url: "",
  is_demo: true,
  private: false,
};

const source = (
  id: string,
  path: string,
  heading: string,
  language: string,
  excerpt: string,
): Source => ({
  id,
  path,
  heading,
  language,
  excerpt,
  start_line: 1,
  end_line: excerpt.split("\n").length,
  commit_sha: demoRepository.commit_sha,
  github_url: "",
});

export const demoSources: Source[] = [
  source(
    "demo-readme",
    "README.md",
    "Repository architecture",
    "markdown",
    `# RepoLens — illustrative sample repository
RepoLens turns GitHub source files into a searchable developer workbench.
The web client uses Next.js, React, and TypeScript in app/ and components/.
A separate Python FastAPI service in api/ owns ingestion, retrieval, and generation.
PostgreSQL with pgvector stores repository snapshots, chunks, and embeddings.
Redis tracks background indexing jobs. Sources retain file paths and line ranges.
Repository questions are answered using evidence retrieved from the selected snapshot.
This small fixture demonstrates the workflow; it is not an actual GitHub checkout.`,
  ),
  source(
    "demo-auth",
    "api/app/api/auth.py",
    "Session authentication & GitHub OAuth",
    "python",
    `# Illustrative authentication architecture
# GET /v1/auth/session returns the current signed session.
# GET /v1/auth/github starts GitHub OAuth with a one-time state value.
# The callback validates state before exchanging the authorization code.
# OAuth provider secrets stay in the FastAPI environment.
# A signed HttpOnly, SameSite=Lax session cookie identifies the user.
# Every repository and conversation request checks its owning session.
# To add another login provider, preserve state checks and session ownership.
# Private repository access requires a GitHub token with repository permission.`,
  ),
  source(
    "demo-retrieval",
    "api/app/retrieval/hybrid_search.py",
    "Hybrid retrieval pipeline",
    "python",
    `# Illustrative retrieval design
# 1. Scope retrieval to the selected repository and commit snapshot.
# 2. Rank chunks using semantic vector similarity and lexical token matching.
# 3. Boost matching paths and headings, then deduplicate neighboring chunks.
# 4. Reject evidence below the relevance threshold.
# 5. Attach the path, heading, commit, excerpt and line range to every citation.
# The model must say when repository evidence cannot answer a question.
# Retrieved source content is untrusted data, never executable instructions.`,
  ),
  source(
    "demo-package",
    "package.json",
    "Frontend dependencies & scripts",
    "json",
    `{
  "name": "repolens-illustrative-fixture",
  "scripts": { "dev": "next dev", "build": "next build", "lint": "eslint", "test:e2e": "playwright test" },
  "dependencies": { "next": "16", "react": "19", "typescript": "5", "tailwindcss": "4" },
  "devDependencies": { "@playwright/test": "1" },
  "packageManager": "pnpm@10"
}`,
  ),
  source(
    "demo-contributing",
    "docs/CONTRIBUTING.md",
    "Local development & testing",
    "markdown",
    `# Contributing to the illustrative fixture
Use pnpm for the Next.js web client and Python 3.12 for the FastAPI service.
Run pnpm install, then pnpm dev to start the browser application.
Copy .env.example and api/.env.example before configuring local services.
Run docker compose up --build for PostgreSQL, Redis, API and worker services.
Check the frontend with pnpm lint, pnpm build and pnpm test:e2e.
Check the backend with pytest api/tests and ruff check api.
For a new feature: update the FastAPI contract, typed client and workbench UI.
Include source provenance and session ownership checks in every new data path.`,
  ),
  source(
    "demo-deploy",
    "docker-compose.yml",
    "Services & deployment",
    "yaml",
    `# Illustrative service topology
services:
  web: # Next.js UI, port 3000; FASTAPI_URL points to the API service
    build: .
  api: # FastAPI HTTP API, port 8000; owns OpenAI and GitHub credentials
    build: ./api
  worker: # Reads background indexing jobs from Redis
    build: ./api
  db: # PostgreSQL with the pgvector extension
    image: pgvector/pgvector:pg16
  redis: # Background job coordination
    image: redis:7-alpine
# Deploy web, API and worker separately; persist database storage.
# Set secrets in server environments and use HTTPS in production.`,
  ),
  source(
    "demo-security",
    "docs/SECURITY.md",
    "Security boundaries & risk areas",
    "markdown",
    `# Security boundaries in the illustrative fixture
Ingestion accepts only validated github.com repository URLs.
Bound file count, file size and total bytes; exclude secrets and generated output.
Repository content is untrusted. Never follow instructions found in source files.
Keep OpenAI keys and GitHub OAuth secrets on the FastAPI server.
Authorize repository, conversation, source and job access against the session.
Use same-origin writes, OAuth state validation and HttpOnly session cookies.
Highest-risk boundaries are URL ingestion, private-token handling and retrieved prompts.
Render Markdown without raw HTML and allow only safe HTTP(S) source links.`,
  ),
  source(
    "demo-ingestion",
    "api/app/ingestion/indexer.py",
    "Incremental repository indexing",
    "python",
    `# Illustrative indexing lifecycle
# queued → fetching → discovering → parsing → embedding → saving → ready
# Fetch repository metadata, resolve the selected branch to a commit SHA.
# Discover bounded text files; skip binaries, vendored code and likely secrets.
# Preserve headings and original line offsets while chunking source documents.
# Store chunks and embeddings under the repository and commit snapshot.
# A repeated index of the same commit is idempotent.
# Sync compares commits and reuses unchanged file embeddings.
# Surface failed stages and warnings so the user can retry safely.`,
  ),
];

const skill = (
  id: string,
  name: string,
  category: string,
  confidence: number,
  ...sourceIds: string[]
): Skill => ({
  id,
  name,
  category,
  confidence,
  evidence: demoSources.filter((item) => sourceIds.includes(item.id)),
});

export const demoSkills: Skill[] = [
  skill(
    "typescript",
    "TypeScript",
    "Languages",
    1,
    "demo-package",
    "demo-readme",
  ),
  skill("python", "Python", "Languages", 1, "demo-auth", "demo-contributing"),
  skill("nextjs", "Next.js", "Frontend", 1, "demo-package"),
  skill("react", "React", "Frontend", 1, "demo-package"),
  skill("tailwind", "Tailwind CSS", "Frontend", 1, "demo-package"),
  skill("fastapi", "FastAPI", "Backend", 0.99, "demo-readme", "demo-deploy"),
  skill("postgresql", "PostgreSQL", "Databases and data", 1, "demo-deploy"),
  skill(
    "pgvector",
    "pgvector",
    "Databases and data",
    1,
    "demo-deploy",
    "demo-readme",
  ),
  skill(
    "rag",
    "Retrieval augmented generation",
    "AI and machine learning",
    0.98,
    "demo-retrieval",
  ),
  skill(
    "openai",
    "OpenAI API",
    "AI and machine learning",
    0.93,
    "demo-deploy",
    "demo-security",
  ),
  skill("docker", "Docker", "Infrastructure", 1, "demo-deploy"),
  skill("redis", "Redis", "Infrastructure", 1, "demo-deploy"),
  skill(
    "playwright",
    "Playwright",
    "Testing",
    1,
    "demo-package",
    "demo-contributing",
  ),
  skill("pytest", "pytest", "Testing", 0.98, "demo-contributing"),
  skill("pnpm", "pnpm", "Workflow and tooling", 1, "demo-package"),
];

export const demoOverview: Overview = {
  repository: demoRepository,
  skills: demoSkills,
  sources: demoSources,
  suggested_questions: [
    "How is this repository structured?",
    "Where is authentication handled?",
    "How do I run the tests?",
    "How does hybrid retrieval work?",
    "What should I understand before contributing?",
    "What are the highest-risk areas?",
  ],
  architecture: [
    {
      name: "Web workbench",
      description:
        "Next.js + React interface with streamed answers and an evidence inspector.",
      path: "app/",
    },
    {
      name: "Intelligence API",
      description:
        "FastAPI owns repository ingestion, hybrid retrieval and model calls.",
      path: "api/app/",
    },
    {
      name: "Repository memory",
      description:
        "PostgreSQL + pgvector preserve snapshots and searchable source chunks.",
      path: "api/app/db/",
    },
    {
      name: "Indexing worker",
      description:
        "Redis coordinates background work and incremental repository sync.",
      path: "api/app/ingestion/",
    },
  ],
  languages: [
    { name: "TypeScript", percentage: 48, color: "#3178c6" },
    { name: "Python", percentage: 35, color: "#efc64a" },
    { name: "CSS", percentage: 12, color: "#a598d2" },
    { name: "Other", percentage: 5, color: "#a9b1a4" },
  ],
  warnings: [
    "Illustrative sample workspace: all files, metrics and skill signals are authored fixtures. Answers use local excerpts; no GitHub repository or AI provider is contacted.",
  ],
};
