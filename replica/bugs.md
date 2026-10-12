# Bugs

Found while building and testing (2026-10-06). Build: uncommitted working tree. Browser: Chromium (Playwright), 1440px and 390px.

### BUG-001: one broken lesson file takes down every page that lists courses

- Severity: S3
- Flow / case: F09-N1
- Screen: S01, S03, S04
- Steps
  1. Make any lesson file invalid (e.g. an `mc` exercise with no `correct: true` option).
  2. Open the dashboard.
- Expected: the app works; the broken lesson shows its validation error on its course page.
- Actual: the dashboard, track page and course page all render the error page.
- Evidence: manual run with a broken copy of `content/`; `tests/unit/broken-content.test.ts` (failed before the fix).
- Status: fixed. Lesson errors are contained per lesson (`LessonRef.error`), course errors per course (`safeGetCourse`); `content:check` reports them as errors.

### BUG-002: random data in setup code differed between learner and solution

- Severity: S2
- Flow / case: F03-H1
- Screen: S06
- Steps
  1. Exercise with `pre_code` that builds data with `np.random`, test `check_equal`.
  2. Submit the exact solution.
- Expected: correct.
- Actual: "`avg` is not quite right" because the RNG was seeded after `pre_code`.
- Evidence: `tests/unit/runner.test.ts` "uses the same random state ... including setup code".
- Status: fixed. `runner/harness.py` seeds `random` and NumPy before setup and before each code run.

### BUG-003: page horizontal scroll on phones

- Severity: S3
- Flow / case: F01-E2
- Screen: every screen with the top nav
- Steps: open `/` at 390px wide.
- Expected: no horizontal scroll.
- Actual: the nav row is 470px wide.
- Evidence: `replica/clone-screens/S01-mobile.png` (before), navigation.spec "a11y + mobile" tests.
- Status: fixed. Nav links wrap to a second row below 640px.

### BUG-004: hydration mismatch on drag exercises

- Severity: S4
- Flow / case: F05-H1
- Screen: S08
- Steps: open `/learn/.../order-bmi`, look at the console.
- Expected: no console errors.
- Actual: React hydration warning on dnd-kit `aria-describedby` ids.
- Status: fixed. Stable `id` passed to `DndContext` via `useId()`.

### BUG-005: any website could run Python through the local API

- Severity: S1
- Flow / case: security
- Screen: `/api/run`
- Steps: from any page in the same browser, `fetch("http://127.0.0.1:3000/api/run", {method: "POST", mode: "no-cors", body: JSON.stringify({...})})`.
- Expected: rejected.
- Actual (before the fix): found by code review, not reproduced before fixing: the route parsed JSON regardless of content type and checked no origin, so a no-cors POST would have reached the runner.
- Evidence (after the fix): curl with `origin: https://evil.example`, `content-type: text/plain`, `host: attacker.example`; `tests/unit/proxy.test.ts`.
- Status: fixed. `src/proxy.ts` requires a loopback Host, a matching Origin when present, and `application/json`.

## To check (not reproduced)

- Very long outputs (MBs) are capped at 20 KB per run; not tested with binary output.
- Two browser tabs on the same exercise: last write wins for saved code; XP is still awarded once (primary key).
