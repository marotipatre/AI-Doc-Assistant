# Two-minute RepoLens demo

## Preparation

Start the app using the README. Use the fixture workspace for a repeatable demo without provider keys. The UI should visibly identify this mode. For a real repository demonstration, start FastAPI first and configure the GitHub/Gemini environment; do not describe fixture answers as live model output.

## Walkthrough

1. **0:00–0:20 — Orient.** Introduce RepoLens as a repository intelligence workbench. Point out the navigation, conversation workspace, and evidence inspector. Explain the displayed repository and index status.
2. **0:20–0:45 — Connect or sync.** With FastAPI running, open repository connection, validate a GitHub URL, inspect the metadata, and start indexing. For the browser-only fixture demo, use Sync repository and explicitly explain that the displayed stages are simulated; it does not connect arbitrary GitHub URLs.
3. **0:45–1:15 — Ask and inspect.** Ask where authentication is handled. Follow the answer stream, open an evidence citation, and inspect its file path, lines, excerpt, and commit provenance.
4. **1:15–1:35 — Skills.** Open Skills and inspect a technology's confidence and evidence. Show how the classification connects to actual configuration or source paths.
5. **1:35–2:00 — Take context away.** Export repository context, return to the conversation, and show sync status. Ask an unsupported question to demonstrate the evidence-limited response.

## Recovery

If the API is unavailable, use the explicitly labeled fixture experience. If GitHub rate-limits a request, explain the error and retry after the reported window or configure a server token. If provider configuration is missing, show the configuration state instead of suggesting that a model call succeeded. Large repositories intentionally have bounded ingestion and may show skipped-file warnings.

## Reproducible local recording

With `pnpm dev` running, run `node --experimental-strip-types scripts/record-demo.ts`. It records the illustrative workspace, asks an authentication question, inspects source evidence, opens Skills, and exports context. Output goes to ignored `artifacts/` as WebM, PNG, and Markdown files. No provider or GitHub requests are used.
