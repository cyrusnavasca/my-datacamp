# Recon map: DataCamp (web)

Scope: the learning loop only. Tracks, courses, chapters, lessons, the in-browser
exercise player (video/slides, coding, multiple choice, drag and drop), XP,
progress, streaks and a personal dashboard. No catalog marketplace, no teams,
no billing, no certification.
For: one learner (the owner of this repo), run locally. First two tracks:
**Data Science / ML** and **AI Engineering**. Lesson content is authored later
by a lesson-builder agent; this build ships the scaffold plus one sample course.
Date: 2026-10-06

## Sources

| # | source | URL | notes |
| --- | --- | --- | --- |
| 1 | public course page | https://www.datacamp.com/courses/intro-to-python-for-data-science | 4 chapters, 11 videos, 46 exercises, 3,900 XP, 4h, 50-100 XP per exercise |
| 2 | public track page | https://www.datacamp.com/tracks/associate-ai-engineer-for-data-scientists | 13 ordered courses, ~40h, prerequisites, certification (premium) |
| 3 | instructor docs: exercise types | https://instructor-support.datacamp.com/en/articles/2360969-exercise-types | video, coding, iterative, sequential, MC, MC with console, drag and drop (classify/order/parsons) |
| 4 | instructor docs: coding exercises | https://instructor-support.datacamp.com/en/articles/2375526-course-coding-exercises | context <=780 chars, 1-4 instructions, sample code <=15 lines with `____` blanks |
| 5 | instructor docs: course outline | https://instructor-support.datacamp.com/en/articles/2360750-course-outline | 4 chapters, ch1 3 lessons, ch2-4 3-4 lessons, each lesson = video then exercises |
| 6 | instructor docs: drag and drop | https://instructor-support.datacamp.com/en/articles/3039539-course-drag-and-drop-exercises | classify, order, parsons variants |
| 7 | instructor docs index | https://instructor-support.datacamp.com/llms.txt | hints, sequential, iterative, MC with console, quality metrics |
| 8 | general product knowledge | n/a | XP penalties for hint/solution, streaks, dashboard layout. Confidence medium. |

No account login used. No bundles, no network capture.

## Core loop

Pick a course in a track, open the next lesson, watch a short slide/video
segment, then solve 2-4 bite-size exercises in the browser (write code, run,
submit, get instant feedback and XP), and repeat until the chapter and course
are complete.

## Screens

| ID | screen | route / how to reach | purpose | key components | states seen |
| --- | --- | --- | --- | --- | --- |
| S01 | Dashboard | `/` | resume where you left off, XP, streak, track progress | ResumeCard, StatTile (XP, streak), TrackProgressCard, WeeklyGoal | empty (new user), filled |
| S02 | Tracks list | `/tracks` | all learning paths | TrackCard, ProgressBar, Tag | empty, filled |
| S03 | Track detail | `/tracks/:slug` | ordered courses in a path | TrackHeader, CourseStep (numbered), ProgressBar, StatusBadge | not started, in progress, complete |
| S04 | Course detail | `/courses/:slug` | outline + start/continue | CourseHeader (hours, videos, exercises, XP), ChapterAccordion, LessonRow, ContinueButton | not started, in progress, complete, locked chapter |
| S05 | Exercise player: video/slides | `/courses/:slug/:lessonId/:exerciseIdx` | lesson intro | SlideViewer, Transcript, NextButton, ExerciseProgressDots | loading, filled |
| S06 | Exercise player: coding | same route | write and test code | ContextPane, Instructions, CodeEditor (tabs), Console/Output, PlotPane, Run/Submit, Hint, ShowSolution, Feedback toast, XP counter | idle, running, error, incorrect feedback, correct, hint shown, solution shown |
| S07 | Exercise player: multiple choice | same route | concept check | QuestionText, OptionList, optional Console, Submit, per-option feedback | unanswered, wrong (feedback), correct |
| S08 | Exercise player: drag and drop | same route | classify / order / parsons | DraggableCard, DropZone, Check | partial, wrong, correct |
| S09 | Exercise player: sequential / iterative | same route | multi-step exercise with sub-steps | StepTabs, CodeEditor, carry-over code | step n of m, all done |
| S10 | Chapter complete | modal after last exercise of chapter | celebrate, XP earned, next chapter | Modal, XP summary, NextButton | filled |
| S11 | Course complete | `/courses/:slug/complete` | summary, next course in track | Summary, NextCourseCard | filled |
| S12 | Progress / profile | `/progress` | XP history, streak calendar, completed courses | StreakCalendar, XPChart, CourseList | empty, filled |
| S13 | Course outline sidebar | drawer inside player | jump between lessons | Drawer, LessonRow with status | open, closed |
| S14 | Settings | `/settings` | daily XP goal, editor theme, reset progress | Form, Select, Toggle, DangerButton | filled |

Player is one screen (S05-S09) that swaps its main pane by exercise type.

## Flows

```
F01 Resume learning
    S01 Dashboard -> click "Continue" -> S06 exercise player at next unfinished exercise
    happy path clicks: 1
    edge: nothing started yet (pick first course of first track), all done (show next course)

F02 Start a course from a track
    S02 -> S03 -> S04 -> "Start course" -> S05 first video
    happy path clicks: 3
    edge: course has no content yet (lesson builder not run), previous course in track unfinished (allowed, warn)

F03 Solve a coding exercise
    S06: read context -> edit sample code -> Run (output in console) -> Submit
      -> incorrect: feedback message, try again
      -> correct: success message, +XP, auto-advance option
    happy path clicks: 2 (run, submit)
    edge: syntax error, runtime error, infinite loop/timeout, hint taken (-30% XP), solution shown (0 XP for exercise remaining), plot output, kernel not ready

F04 Answer multiple choice
    S07: pick option -> Submit -> feedback for that option -> retry until correct
    happy path clicks: 2
    edge: wrong answers reduce XP

F05 Drag and drop (parsons / order / classify)
    S08: drag cards -> Check -> highlighted wrong positions
    happy path clicks: n drags + 1

F06 Finish chapter and course
    last exercise -> S10 chapter modal -> next chapter ... -> S11 course complete -> next course in track
    happy path clicks: 1 per transition

F07 Review progress
    S01 -> S12
    happy path clicks: 1

F08 Jump around within a course
    S06 -> open S13 outline drawer -> pick lesson
    happy path clicks: 2

F09 (clone-only) Add lessons
    lesson-builder agent writes content files -> app picks them up on reload
    happy path clicks: 0 (file-based)
```

## Components

| component | variants | states | used on |
| --- | --- | --- | --- |
| Button | primary, secondary, ghost, danger | default, hover, focus, disabled, loading | all |
| ProgressBar | thin, labelled | 0, partial, 100 | S01-S04, S12 |
| StatTile | xp, streak, goal | default | S01, S12 |
| TrackCard | default | not started, in progress, done | S02 |
| CourseStep | numbered list item in track | locked-ish, current, done | S03 |
| ChapterAccordion | default | collapsed, expanded | S04 |
| LessonRow | video, exercise | todo, current, done | S04, S13 |
| StatusBadge | todo, in progress, done | | S03, S04 |
| CodeEditor | python, sql, shell | editable, read-only, error line | S06, S09 |
| Console/Output | text, error, plot image, dataframe table | empty, running, filled | S06, S07 |
| Instructions | bullet list with checkable steps | | S06, S09 |
| HintPanel | hint, solution | hidden, shown | S06-S09 |
| FeedbackToast | success, incorrect, error | | S06-S09 |
| SlideViewer | markdown slides | slide n of m | S05 |
| OptionList | radio options | selected, wrong, correct | S07 |
| DragCard / DropZone | classify, order, parsons (with indent) | idle, dragging, wrong, correct | S08 |
| XPCounter | header pill | animate on gain | player header |
| Modal | chapter complete, confirm reset | | S10, S14 |
| Drawer | outline | open/closed | S13 |
| TopNav | app | active link | all |

## Inferred data model

```
Track        id, slug, title, description, order, course_ids (ordered)
             evidence: source 2 (ordered course list, hours)
             confidence: high

Course       id, slug, title, description, track_id, order_in_track, prerequisites[],
             est_hours, xp_total (derived), language (python|sql|...)
             evidence: source 1 header (hours, videos, exercises, XP), prerequisites block
             confidence: high

Chapter      id, course_id, order, title, description
             evidence: source 1, source 5 (4 chapters)
             confidence: high

Lesson       id, chapter_id, order, title   (DataCamp calls each row in the outline a "lesson/exercise";
             each lesson = 1 video + 2-4 exercises)
             evidence: source 5
             confidence: medium

Exercise     id, lesson_id, order, type (video|coding|mc|mc_console|dragdrop|sequential|iterative),
             xp (video 50, coding 100, mc 50), title, context_md, instructions[], hint_md,
             pre_exercise_code, sample_code, solution_code, sct (tests), success_msg,
             options[] {text, correct, feedback} (mc), items/zones (dragdrop),
             steps[] (sequential/iterative), slides_md (video)
             evidence: sources 3, 4, 6, 7
             confidence: high for fields, medium for exact XP numbers

ExerciseAttempt  id, exercise_id, submitted_code/answer, correct (bool), feedback, created_at
             evidence: retry behaviour in F03/F04
             confidence: medium

ExerciseProgress exercise_id, status (todo|done), xp_earned, hint_used, solution_used, completed_at
             evidence: XP counter, hint penalty
             confidence: medium (penalty amounts are a guess: hint -30%, solution -70%)

DailyActivity date, xp_earned, exercises_done   (drives streak and charts)
             evidence: streak and XP history on dashboard
             confidence: medium

Settings     daily_xp_goal, editor_theme, auto_advance
             confidence: guess
```

Relationships: Track 1-n Course (ordered), Course 1-n Chapter, Chapter 1-n Lesson,
Lesson 1-n Exercise, Exercise 1-n ExerciseAttempt, Exercise 1-1 ExerciseProgress.
Single user, so no User table needed.

## Feature matrix

See `features.csv`. Must: 20, should: 11, could: 7, skip: 9.

## Out of scope (cannot or should not be cloned)

- DataCamp's course content: videos, slides, exercises, datasets, scripts. All lessons here are written fresh by the lesson-builder agent.
- Instructors, voice-over audio and screencasts.
- Certifications and the certificate network.
- Teams, groups, B2B admin, leaderboards against other users.
- Billing, subscriptions, premium gating.
- DataLab (hosted notebooks) as a product. A local notebook-style pane is fine.
- Mobile apps, push notifications, marketing site, SEO pages.
- DataCamp branding: name, logo, owl/mascot, green palette as-is, copy.

## Size

Screens 14, flows 9, entities 8. Hard parts:
1. In-browser code execution with real feedback (Python with numpy/pandas/sklearn, plus PyTorch/LLM libs for AI Engineering, which are too big for Pyodide: needs a local Python runner).
2. Submission correctness tests (SCT): a safe, simple test format the lesson-builder agent can author reliably.
3. A content format that a lesson-builder agent can write at scale and that the app validates.

Size: M (scaffold in a session, content over weeks).
