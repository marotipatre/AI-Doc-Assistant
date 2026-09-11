"""Small original fictional repository. No external project is misrepresented."""

import hashlib

from app.db.store import now, store
from app.ingestion.files import chunks, detect_skills

DEMO_ID = "demo-repolens"
FILES = {
    "README.md": """# RepoLens · a repository intelligence workspace

RepoLens is a fictional reference repository bundled with RepoLens for a zero-key demo.
It combines a Next.js web application, a FastAPI service, and PostgreSQL storage.
This is sample source code, not an indexed external GitHub repository.

## Getting started
Install Node.js 22 and Python 3.13. Run pnpm install, then docker compose up -d.
Copy .env.example to .env. Run pnpm dev to start the web app on localhost:3000.
The FastAPI service listens on localhost:8000. Use /health to check liveness.

## Project structure
app/ contains the Next.js App Router pages and layouts.
components/ contains reusable React UI components.
api/app/ contains FastAPI endpoints, authentication, and repository services.
api/app/db/ contains SQLAlchemy models and PostgreSQL persistence.
tests/ contains Playwright browser tests; api/tests/ contains Pytest tests.

## Contributing
Create a feature branch and keep changes focused. Run pnpm lint and pnpm test.
Run pytest from api/ before submitting backend changes.
New endpoints need request validation and tests for ownership enforcement.
Never commit .env files or API keys.

## Deployment
The web app is built with pnpm build. The API runs with uvicorn app.main:app.
Docker Compose provides PostgreSQL and Redis. Store secrets in the host environment.
Apply database migrations before starting a new release.
""",
    "package.json": """{
  "name": "repolens-workspace",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "lint": "eslint .",
    "test": "vitest run",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "next": "16.2.0",
    "react": "19.2.0",
    "react-dom": "19.2.0"
  },
  "devDependencies": {
    "typescript": "^5",
    "tailwindcss": "^4",
    "vitest": "^3",
    "@playwright/test": "^1.51",
    "eslint": "^9"
  },
  "packageManager": "pnpm@10.28.0"
}
""",
    "api/app/auth.py": """\"\"\"Session authentication boundary for the RepoLens sample.\"\"\"
from fastapi import APIRouter, Depends, HTTPException, Request

router = APIRouter(prefix="/auth")

def current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user_id

@router.get("/session")
def session(user_id: str = Depends(current_user)):
    return {"user_id": user_id}

# GitHub OAuth is not yet implemented in this sample repository.
# Add /auth/github and /auth/github/callback to this router.
# Verify a one-time state value, exchange the code server-side, and
# encrypt any retained GitHub access token. Never send tokens to the browser.
# Keep current_user as the common authorization dependency.
""",
    "api/app/projects.py": """from fastapi import APIRouter, Depends, HTTPException
from .auth import current_user
from .db import projects

router = APIRouter(prefix="/projects")

@router.get("/{project_id}")
def get_project(project_id: str, user_id: str = Depends(current_user)):
    project = projects.get(project_id)
    if project is None or project.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

# Every project mutation must reuse the ownership check above.
""",
    "api/pyproject.toml": """[project]
name = "repolens-api"
requires-python = ">=3.13"
dependencies = ["fastapi", "uvicorn", "sqlalchemy", "psycopg[binary]", "redis", "openai"]

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
    "api/app/db/models.py": """\"\"\"SQLAlchemy models persisted in PostgreSQL.\"\"\"
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    owner_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String, nullable=False)

# DATABASE_URL uses postgresql+psycopg.
# Ownership indexes support per-user filtering; all reads enforce owner_id.
""",
    "app/layout.tsx": """import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RepoLens — knowledge, connected",
  description: "A repository intelligence workspace",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
""",
    "docs/architecture.md": """# Architecture

## Web boundary
The Next.js App Router renders the interface. React components call a thin API proxy.
Business logic, authorization, retrieval, and provider credentials stay in FastAPI.

## Data boundary
PostgreSQL persists users and projects. Redis holds background indexing jobs.
Workers retry transient fetch errors and write completed snapshots atomically.

## Authentication and security
The FastAPI session dependency checks a signed HttpOnly cookie.
Project endpoints enforce owner_id before returning records.
GitHub login is an extension point in api/app/auth.py, not a completed feature.
OAuth state validation and encrypted tokens are required before enabling it.

## Testing
Vitest covers component behavior. Playwright covers the login-to-project workflow.
Pytest covers API authorization, ingestion limits, and database isolation.
Run pnpm test, pnpm test:e2e, and pytest from api/.
""",
    ".github/workflows/ci.yml": """name: checks
on: [push, pull_request]
jobs:
  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm test
      - run: pnpm build
""",
    "Dockerfile": """FROM node:22-alpine AS web
WORKDIR /app
COPY . .
RUN corepack enable && pnpm install --frozen-lockfile && pnpm build
EXPOSE 3000
CMD ["pnpm", "start"]
""",
}


def seed_demo():
    if store.get("repositories", DEMO_ID):
        return
    sha = hashlib.sha256("".join(FILES.values()).encode()).hexdigest()[:40]
    repo = {
        "id": DEMO_ID,
        "owner": "repolens",
        "name": "repolens",
        "full_name": "repolens/repolens",
        "description": "A repository intelligence workspace. Explore this original sample repository—no API key needed.",
        "default_branch": "main",
        "commit_sha": sha,
        "stars": 0,
        "language": "TypeScript",
        "status": "ready",
        "file_count": len(FILES),
        "chunk_count": 0,
        "indexed_at": now(),
        "html_url": "",
        "is_demo": True,
        "private": False,
        "_owner_id": "demo",
    }
    sources = [source for path, content in FILES.items() for source in chunks(repo, path, content)]
    repo["chunk_count"] = len(sources)
    store.put("repositories", repo, "demo", DEMO_ID)
    store.replace_index(
        repo,
        sources,
        [],
        detect_skills(sources),
        {path: hashlib.sha256(content.encode()).hexdigest() for path, content in FILES.items()},
    )
