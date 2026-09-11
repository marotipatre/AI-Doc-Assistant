# Threat model

## Scope and trust boundaries

The intended deployment is a single-user local showcase. Assets include provider keys, repository contents, indexed excerpts, conversation history, and model budget. Untrusted inputs include repository URLs, branch names, paths, file contents, questions, and provider responses.

The browser is not a trusted location for secrets. The Next.js API boundary forwards requests to a configured FastAPI service; business logic and provider calls remain in FastAPI. GitHub repository contents cross a separate boundary into retrieval context and must remain data even when they contain instructions.

## Controls and remaining risks

| Threat | Implemented design | Remaining boundary |
| --- | --- | --- |
| SSRF through repository URLs | Restrict repository onboarding to GitHub and construct GitHub API requests server-side. | Revalidate redirects and any future enterprise GitHub support before expanding the allowlist. |
| Expensive or oversized ingestion | Bound file counts, file sizes, total bytes, and request timeouts; skip generated, binary, and likely secret paths. | Content can contain secrets under innocent filenames. Do not index confidential repositories without an explicit data policy. |
| Prompt injection in source files | Distinguish retrieved source content from the model's grounding instructions; never execute repository scripts. | Prompt policies reduce risk but cannot guarantee model compliance. Inspect citations before acting on answers. |
| XSS in answers and excerpts | Render source text as text and avoid enabling raw HTML in Markdown. | Reassess sanitization if rich HTML or third-party renderers are introduced. |
| Provider key exposure | Keep provider variables on the backend, exclude environment files from image context, and do not use public-prefixed secret variables. | Logs, crash reports, and deployment tooling must follow the same secret policy. |
| Public endpoint abuse | Loopback bindings, per-IP/user/repository request limits, GitHub/model concurrency bounds, and Redis-backed rate counters when configured. | Inference quotas, proxy-aware client identity, and load testing need deployment-specific validation. |
| Cross-user repository access | Signed HttpOnly sessions; ownership checks on repository, job, source, and conversation endpoints; regression tests with separate clients. | A production tenant-security audit and end-to-end OAuth verification remain necessary before a public deployment. |
| Stale or invented evidence | Preserve commit and source provenance, make evidence inspectable, and surface insufficient evidence. | A grounded excerpt is not proof that a proposed code change is correct or safe. |

## GitHub credentials

GitHub OAuth uses a signed, expiring state cookie and PKCE. Public sign-in requests `read:user`; private access explicitly requests the additional `repo` scope. Retained tokens are encrypted with Fernet, never returned to browser code, and deleted on disconnect. Disconnect also removes private indexed repositories. Reconnect to replace expired tokens; encryption-key rotation requires re-encrypting retained records or disconnecting accounts first.

Mocked OAuth tests verify state rejection, successful exchange, encrypted persistence, and credential deletion. They do not verify a real GitHub OAuth application.

## Safe operations

- Keep `.env` and provider tokens out of version control; start from `.env.example`.
- Use public repositories for the showcase. Any server GitHub token should have the narrowest required access.
- Keep PostgreSQL and Redis on an internal network; publish only loopback ports locally.
- Clear local fixture state separately from server persistence. Stopping Compose does not delete named database volumes.
- Treat exported context as repository data, including its sensitivity and license obligations.

## Verification boundaries

Backend tests and browser smoke tests cover their named behaviors; passing tests do not establish resistance to every prompt injection or prove hosted multi-user security. Docker image execution, real GitHub ingestion, paid provider calls, and deployment checks require their corresponding services and credentials. Record which mode was used when reporting demo results.
