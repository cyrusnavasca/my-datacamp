-- Local SQLite database (data/progress.db). Single user: no owner columns, no auth.
-- Content (tracks, courses, lessons, exercises) lives in files under content/,
-- not here. Rows reference content by its stable string id:
--   "<course-slug>/<chapter-id>/<lesson-id>/<exercise-id>"
-- Times are ISO-8601 UTC text; daily_activity.day is the learner's local date.

create table if not exists exercise_progress (
  exercise_id   text primary key,
  course_slug   text not null,
  status        text not null default 'done' check (status in ('done')),
  xp_earned     integer not null check (xp_earned >= 0),
  hint_used     integer not null default 0 check (hint_used in (0,1)),
  solution_used integer not null default 0 check (solution_used in (0,1)),
  wrong_count   integer not null default 0 check (wrong_count >= 0),
  completed_at  text not null,
  updated_at    text not null
);
create index if not exists exercise_progress_course on exercise_progress (course_slug);
create index if not exists exercise_progress_completed on exercise_progress (completed_at);

-- Penalties taken before the exercise is complete (hint, solution, wrong MC answer).
create table if not exists exercise_state (
  exercise_id   text primary key,
  hint_used     integer not null default 0 check (hint_used in (0,1)),
  solution_used integer not null default 0 check (solution_used in (0,1)),
  wrong_count   integer not null default 0 check (wrong_count >= 0),
  steps_done    integer not null default 0 check (steps_done >= 0),  -- sequential exercises
  last_code     text,
  updated_at    text not null
);

create table if not exists attempts (
  id            integer primary key autoincrement,
  exercise_id   text not null,
  kind          text not null check (kind in ('run','submit')),
  correct       integer check (correct in (0,1)),
  payload       text not null,          -- submitted code or answer json
  feedback      text,
  created_at    text not null
);
create index if not exists attempts_exercise on attempts (exercise_id, created_at);

create table if not exists daily_activity (
  day             text primary key,     -- YYYY-MM-DD, local
  xp_earned       integer not null default 0,
  exercises_done  integer not null default 0
);

create table if not exists settings (
  key   text primary key,
  value text not null
);
