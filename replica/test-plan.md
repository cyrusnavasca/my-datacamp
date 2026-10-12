# Test plan: my-datacamp

Automated: Playwright specs in `tests/e2e/` against a dev server on
127.0.0.1:3100 with its own DB (`data/e2e.db`, wiped per run). Every spec fails on
console errors and 5xx responses. Unit tests in `tests/unit/` cover XP rules,
schema, answer checking, the Python runner and the API guard.

Edge-case list applied per flow; cases that do not apply to a single-user local
app (second user, expired session, payments, time zones across users) are omitted.

## F01 Resume learning (S01)
- F01-H1 New learner: dashboard offers "Start course" and it opens the first exercise. **auto**
- F01-H2 After some progress, "Continue" opens the next unfinished exercise. **auto**
- F01-E1 Everything with content complete: dashboard shows the empty state. **manual** (only one lesson exists; covered by unit logic)
- F01-E2 Mobile width 390px: no horizontal scroll. **auto** (all screens)

## F02 Start a course from a track (S02 → S03 → S04 → S05)
- F02-H1 Tracks → Data Science & ML → Python for Data Science → Start course lands on slide 1. **auto**
- F02-E1 Course with no lessons shows "Content coming" and the plan, no start button. **auto**
- F02-E2 Unknown course/track/exercise URL shows the not-found page. **auto**
- F02-E3 Keyboard only: Tab to a track, Enter, Tab to the course, Enter. **auto**

## F03 Solve a coding exercise (S06)
- F03-H1 Run shows output in the console; Submit with the right code shows success, +XP, Continue. **auto**
- F03-N1 Submit untouched sample code: "Fill in the ____ blanks". **auto**
- F03-N2 Wrong value: specific feedback, no XP. **auto**
- F03-N3 Runtime error: traceback in the console. **auto**
- F03-E1 Take hint: hint shown, instruction XP drops 100 → 70; Show answer fills the editor. **auto**
- F03-E2 Refresh mid-exercise keeps the last run code and the hint. **auto**
- F03-E3 Ctrl/Cmd+Enter runs. **auto**
- F03-E4 Double click Submit awards XP once. **auto**
- F03-E5 Infinite loop stops after the timeout with a message. **unit** (2 s timeout)
- F03-E6 Plot output shows a Plots tab. **unit**

## F04 Multiple choice (S07)
- F04-H1 Wrong option shows its feedback; right option shows success with reduced XP. **auto**
- F04-E1 Console: run `type(x)` against the preloaded setup. **auto**

## F05 Drag and drop (S08)
- F05-H1 Parsons: order with the keyboard, indent, check, correct. **auto**
- F05-N1 Parsons wrong indentation marks the line. **unit**
- F05-H2 Classify: assign every item, wrong item highlighted, then correct. **auto**

## F06 Finish chapter and course (S09 → S11)
- F06-H1 Sequential: step 1 then step 2, then Finish course goes to the course-complete page with XP earned. **auto**
- F06-E1 Course page shows every exercise ticked afterwards. **auto**

## F07 Review progress (S12)
- F07-H1 Progress page lists the course with XP after completing exercises. **auto**

## F08 Jump around (S13)
- F08-H1 Outline drawer opens, lists lessons with done ticks, navigates, closes with Esc. **auto**

## F09 Add lessons (content)
- F09-H1 `npm run content:check` passes on the shipped content. **auto** (CLI)
- F09-N1 Broken lesson file shows the content error page naming the file. **manual**, see bugs.md

## Settings (S14)
- S14-H1 Reset everything asks for confirmation and zeroes XP. **auto**

## Accessibility
- Axe scan (WCAG 2 A/AA rules) on every screen. **auto**
