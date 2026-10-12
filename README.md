# my-datacamp

A personal, local learning app modelled on how DataCamp structures learning:
tracks of courses, short slide lessons, and bite-size exercises you solve in the
browser with real Python, with XP, streaks and progress.

Two tracks are outlined: **Data Science & Machine Learning** and **AI Engineering**
(8 courses each). One sample lesson exists; the rest are written by the
lesson-builder agent.

## Run it

```bash
npm install
npm run setup:python      # creates .venv with numpy, pandas, matplotlib, scikit-learn, scipy
npm run dev               # http://127.0.0.1:3000
```

For the AI Engineering track: `.venv/bin/pip install -r runner/requirements-ai.txt` (torch, transformers, anthropic).

## Add lessons

Ask Claude Code to use the `lesson-builder` agent, e.g.
"use the lesson-builder agent to write chapter 1 of python-for-data-science".
The format is documented in [`content/README.md`](content/README.md).
Validate with `npm run content:check`.

## Checks

```bash
npm run lint              # type-check
npm test                  # unit tests (content, XP, exercises, Python runner)
npx playwright test       # end-to-end (starts the dev server if needed)
npm run content:check     # every lesson file, every solution against its tests
```

## Notes

- Everything is local. Progress lives in `data/progress.db` (SQLite). Delete it to start over, or use Settings.
- The server runs your Python code, so it only listens on 127.0.0.1. Keep it that way.
- Planning docs (recon, architecture, design tokens, feature matrix) are in `replica/`.
- No DataCamp content, branding or code is used. Lessons are original.
