# Developer handoff direction

User feedback: unclear outcomes; hidden tools; difficult GitHub navigation; reconnecting the same account; unclear walkthrough; demo buried in settings.

Primary outcome: prepare a reviewable repository handoff for an AI coding session. Readiness pack offers indexed evidence categories, explicitly missing evidence, a locally matched task brief, SKILL.md preview/copy/download and comparison against the last exported commit. No AI requests are used. Evidence coverage is partial; this is not a security audit, dependency impact graph or automatic conflict detector.

Navigation: visible Readiness pack tab and overview action; visible demo switch; landing sample links directly to pack. GitHub OAuth requests account selection and public identity by default. Disconnect removes RepoLens authorization, not the browser's GitHub session.

Remaining product work: automatically detecting contradictory setup instructions, complete dependency-aware change impact, and cross-device export history. These are not claimed as implemented.

## Focused product revision
The workspace now consists of repository connection, readiness pack and expandable evidence inspection. Removed the chat composer, conversation history, overview dashboard, technology dashboard, generic context export, settings modal and competing tours from the rendered application. Existing backend chat endpoints remain for compatibility but have no user-facing entry point. Landing and guide describe only the handoff workflow.

The pack now carries bounded source excerpts for setup/instructions, excludes common filler words from task matching, and blocks export for unready or empty snapshots. Demo switching retains the selected live repository in the current session. Live mode can be entered with no existing repository.

## Handoff studio visual revision
The focused workflow now has three real routes inside a persistent Next.js layout: `/workspace` for the pack, `/workspace/evidence` for searchable excerpts, and `/workspace/repository` for connection and account controls. The shared provider preserves the selected repository and task draft during client navigation.

The landing page includes a clickable three-step product preview, four balanced workflow cards and direct entry points. Workspace evidence cards support pointer drag-and-drop and explicit keyboard-accessible move buttons; review buttons expand source details. Desktop uses a compact sidebar and aligned card grids; mobile uses top navigation and stacked panels. Motion respects reduced-motion preferences. Card ordering is local to the mounted pack; it does not change exported evidence ordering.

## Clear instructions, account selection and document editing
User-facing copy now explains SKILL.md as an editable repository instruction file. Removed model-call counts and abstract slogans from the workspace and marketing pages. GitHub connection/account switching/disconnect are in the navbar. New visits do not restore a repository or select the first result; an existing authenticated GitHub session is shown truthfully in the navbar. The repository picker fills both URL and default branch. Disconnect clears the selected repository, account list, draft and URL fields.

Writing assistant is focused on editing the current document. Users can edit directly, select a passage for a proposed replacement, or request a new section. The backend returns a bounded proposal without changing stored repository data. Apply, discard and undo are explicit; stale proposals cannot overwrite manual edits. Copy/download use the current edited document. Reference cards are below the main editor. Drafts are session-local and cleared on repository changes, demo switching or disconnect; download before leaving.
