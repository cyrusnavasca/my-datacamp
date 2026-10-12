<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# my-datacamp

A personal, local rebuild of DataCamp's learning loop (tracks, courses, slide
lessons, in-browser Python exercises, XP and streaks). One user, localhost only.

- Run: `npm run dev` (binds to 127.0.0.1:3000). First time: `npm install && npm run setup:python`.
- Content is YAML in `content/`; the format is in `content/README.md`. Validate with `npm run content:check`.
- Write lessons with the `lesson-builder` agent (`.claude/agents/lesson-builder.md`).
- Code: `src/lib/content` (schema + loader), `src/lib/exercises.ts` (run/submit/hint/solution), `src/lib/progress.ts` (SQLite progress, XP), `runner/harness.py` (Python executor + test helpers), `src/components/player` (exercise player).
- Design tokens: edit `replica/design/tokens*.json`, then `npm run tokens`. Components use token classes (`bg-surface`, `text-muted`), never raw colours.
- `/api/run` executes arbitrary Python. Never bind the server to anything but 127.0.0.1.
- Planning docs from the replica skills are in `replica/`.
- Checks: `npm run lint` (tsc), `npm test` (vitest), `npx playwright test` (e2e, needs the dev server).
