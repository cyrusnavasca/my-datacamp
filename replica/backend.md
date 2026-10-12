# Backend: my-datacamp

Single learner on localhost. Most of the replica-backend checklist does not apply.

| area | status | notes |
| --- | --- | --- |
| auth | n/a | one user; the server binds to 127.0.0.1 and `src/proxy.ts` guards `/api/*` |
| database | done | SQLite (`node:sqlite`) at `data/progress.db`; migrations in `src/lib/db/migrations/`, tracked with `pragma user_version` |
| access rules | n/a | no second user to isolate |
| seed data | n/a | content is the seed; the sample lesson exercises every type |
| backups | manual | copy `data/progress.db` (gitignored). Content is in git. |
| payments, email, jobs, integrations | n/a | personal tool |
| env vars | none | optional: `PYTHON`, `CONTENT_DIR`, `PROGRESS_DB` |

## Security checklist

- [x] secrets: none used; `.env*` not needed. Future LLM lessons run on fake clients, no keys in content.
- [x] input validated on the server with zod on every route (`src/lib/api/handler.ts`); exercise keys are regex-checked, so no path traversal into content files
- [x] code execution contained to this machine's user: dev/start bind to 127.0.0.1; `src/proxy.ts` rejects non-loopback Host (DNS rebinding), foreign Origin (cross-site POST) and non-JSON bodies (forces CORS preflight, never answered). Tested in `tests/unit/proxy.test.ts` and with curl.
- [x] runaway code: 30 s default timeout, whole process group killed; output capped at 20 KB
- [x] client never receives solutions, tests or answer keys before the learner asks (`toPublic` in `src/lib/exercises.ts`, unit-tested)
- [n/a] rate limits, webhooks, uploads, privacy policy
- [x] `npm audit --omit=dev`: 0 vulnerabilities (katex pinned via `overrides`)

Known limit: learner code runs with your user's permissions (it can read your files). That is inherent to a local
Python runner. Only run lesson content you or the lesson builder wrote.
