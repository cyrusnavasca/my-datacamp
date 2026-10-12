# Architecture: my-datacamp (a personal rebuild of DataCamp's learning loop)

Single learner, runs on localhost. No accounts, payments, email or hosting.
Content is plain files so a lesson-builder agent can write it.

## Stack

| layer | choice | why |
| --- | --- | --- |
| web | Next.js 16 (App Router) + TypeScript | server components read content files directly; route handlers for the runner and progress |
| styling | Tailwind CSS v4, tokens from replica-design | tokens as CSS variables, light and dark |
| editor | CodeMirror 6 (`@uiw/react-codemirror`, `@codemirror/lang-python`) | small, good Python mode, easy keybindings |
| content | YAML files under `content/`, validated with zod | agent-friendly: one file per lesson, code in block scalars, schema errors point at the file |
| database | SQLite via Node's built-in `node:sqlite` at `data/progress.db` | progress only; zero native deps, no server |
| ORM | raw SQL in `src/lib/db.ts` | 5 tables, single user |
| code runner | local Python 3 subprocess in a repo `.venv`, harness in `runner/harness.py` | real numpy/pandas/sklearn/torch; Pyodide cannot load torch or LLM libs |
| auth | none, server bound to 127.0.0.1 | single user; binding to localhost is the access rule |
| payments, email, jobs, hosting | none | personal tool |

## Content layout (the lesson-builder contract)

```
content/
  tracks/<track-slug>.yaml                 title, description, order, courses: [course-slug, ...]
  courses/<course-slug>/course.yaml        title, description, level, est_hours, prerequisites, objectives,
                                           chapters: [{id, title, description, lessons: [lesson-id, ...]}]
  courses/<course-slug>/<chapter-id>/<lesson-id>.yaml   title, exercises: [ {id, type, ...} ]
  datasets/<file>.csv                      data files exercises can load (path exposed as DATA_DIR)
```

Exercise types and fields (zod schema in `src/lib/content/schema.ts`):

- `video`: `slides` (markdown, slides split by `---`), xp 50
- `coding`: `context`, `instructions[]`, `hint`, `pre_code`, `sample_code`, `solution`, `tests`, `success_msg`, xp 100
- `mc`: `question`, `options[] {text, correct, feedback}`, `hint`, optional `pre_code` (enables console), xp 50
- `order` / `parsons`: `prompt`, `items[]` (correct order; parsons items carry indent), xp 50
- `classify`: `prompt`, `zones[]`, `items[] {text, zone}`, xp 50
- `sequential`: shared `context`, `pre_code`, `steps[]` each a coding exercise without pre_code; state carries over, xp split

`tests` is Python run after the learner's code. Helpers available:
`check_object(name)`, `check_equal(name, expected=None)` (defaults to the
solution's value), `check_output_contains(text)`, `check_called(fn_name)` and
plain `assert cond, "feedback"`. First failing message is the feedback.

`npm run content:check` validates every file, ids, references and runs every
`solution` against its `tests` (solution must pass).

## Schema

Tables: 5. Access rules: none needed (single user, localhost). See `src/lib/db/migrations/` (applied on startup, tracked with `pragma user_version`).

## API

| method path | does | who | input | output | flow |
| --- | --- | --- | --- | --- | --- |
| GET pages `/`, `/tracks`, `/tracks/[slug]`, `/courses/[slug]`, `/progress`, `/settings` | server-rendered from content + db | local | | HTML | F01, F02, F07 |
| GET page `/learn/[course]/[chapter]/[lesson]/[exercise]` | exercise player | local | | HTML | F03-F06, F08 |
| POST `/api/run` | run code, return stdout/stderr/figures | local | `{exerciseId, code, step?}` | `{stdout, stderr, error, images[], ms}` | F03 |
| POST `/api/submit` | run code + tests, or check answer; on pass record progress and XP | local | `{exerciseId, code? , answer?, step?}` | `{correct, feedback, xpEarned, output}` | F03-F05 |
| POST `/api/hint` | mark hint used (penalty) and return it | local | `{exerciseId}` | `{hint}` | F03 |
| POST `/api/solution` | mark solution used and return it | local | `{exerciseId, step?}` | `{solution}` | F03 |
| POST `/api/settings` | update goal, reset progress | local | `{dailyGoal?, reset?}` | `{ok}` | S14 |

No webhooks, no jobs.

## The parts that bite

- **Code execution is arbitrary code.** Fine for one person on their own machine; the dev server must bind to `127.0.0.1` so nothing on the LAN can POST to `/api/run`. Timeout every run (default 30 s, per-exercise override) and kill the process group.
- **Cold start.** A fresh Python process per run re-imports pandas/sklearn/torch (1-5 s). Acceptable for the scaffold; a persistent per-exercise worker is the upgrade.
- **Test isolation.** Solution and learner code run in separate namespaces in the same process, both after `pre_code`, with the same random seed.
- **Time zones.** Streaks use the learner's local date (server local time, since it is the same machine).
- **Idempotency.** Submitting a completed exercise again never re-awards XP (primary key on `exercise_progress`).
- **Content drift.** Exercise ids are stable strings; renaming one orphans its progress. `content:check` warns about progress rows with no content.
- **Python 3.14 wheels.** Pin libraries in `requirements.txt`; torch and LLM libs are optional extras for the AI Engineering track.

## Build order

1. **Vertical slice:** content loader + schema, one sample course with one lesson (video, coding, mc), S04 course page, player S05/S06/S07, `/api/run`, `/api/submit`, progress table. Proves Python runner and content format.
2. **Must-haves:** S01 dashboard with resume, S02/S03 tracks, hint/solution penalties, chapter and course completion (S10, S11), XP header, content validator, both track skeletons (Data Science/ML, AI Engineering) with planned course outlines.
3. **Should-haves:** streak and daily goal, order/parsons/classify, sequential, plots and dataframe tables, outline drawer S13, progress page S12, settings S14.
4. **Could-haves:** keyboard shortcuts, dark mode, lesson-builder agent definition (next phase).
5. Fixes from replica-entrepreneur: skipped (personal tool).
