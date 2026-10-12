import { db } from "./db";
import { computeXp } from "./xp";

export { computeXp, PENALTY } from "./xp";

export type ExerciseState = {
  hint_used: number;
  solution_used: number;
  wrong_count: number;
  steps_done: number;
  last_code: string | null;
};

export type ProgressRow = {
  exercise_id: string;
  course_slug: string;
  xp_earned: number;
  hint_used: number;
  solution_used: number;
  completed_at: string;
};

const now = () => new Date().toISOString();

/** Local calendar date, YYYY-MM-DD. */
export function localDay(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function getState(exerciseId: string): ExerciseState {
  const row = db()
    .prepare("select hint_used, solution_used, wrong_count, steps_done, last_code from exercise_state where exercise_id = ?")
    .get(exerciseId) as ExerciseState | undefined;
  return row ?? { hint_used: 0, solution_used: 0, wrong_count: 0, steps_done: 0, last_code: null };
}

function upsertState(exerciseId: string, patch: Partial<ExerciseState>) {
  const s = { ...getState(exerciseId), ...patch };
  db()
    .prepare(
      `insert into exercise_state (exercise_id, hint_used, solution_used, wrong_count, steps_done, last_code, updated_at)
       values (?, ?, ?, ?, ?, ?, ?)
       on conflict(exercise_id) do update set hint_used = excluded.hint_used, solution_used = excluded.solution_used,
         wrong_count = excluded.wrong_count, steps_done = excluded.steps_done, last_code = excluded.last_code,
         updated_at = excluded.updated_at`,
    )
    .run(exerciseId, s.hint_used, s.solution_used, s.wrong_count, s.steps_done, s.last_code, now());
  return s;
}

export const markHint = (id: string) => upsertState(id, { hint_used: 1 });
export const markSolution = (id: string) => upsertState(id, { solution_used: 1 });
export const markWrong = (id: string) => upsertState(id, { wrong_count: getState(id).wrong_count + 1 });
export const saveCode = (id: string, code: string) => upsertState(id, { last_code: code });
export const setStepsDone = (id: string, n: number) => upsertState(id, { steps_done: n });

export function getProgress(exerciseId: string): ProgressRow | null {
  return (
    (db().prepare("select * from exercise_progress where exercise_id = ?").get(exerciseId) as ProgressRow | undefined) ??
    null
  );
}

/** Records completion. Returns XP awarded now (0 if it was already complete). */
export function completeExercise(exerciseId: string, baseXp: number): number {
  if (getProgress(exerciseId)) return 0;
  const s = getState(exerciseId);
  const xp = computeXp(baseXp, s);
  const t = now();
  const course = exerciseId.split("/")[0];
  const d = db();
  d.exec("begin");
  try {
    d.prepare(
      `insert into exercise_progress (exercise_id, course_slug, status, xp_earned, hint_used, solution_used, wrong_count, completed_at, updated_at)
       values (?, ?, 'done', ?, ?, ?, ?, ?, ?)`,
    ).run(exerciseId, course, xp, s.hint_used, s.solution_used, s.wrong_count, t, t);
    d.prepare(
      `insert into daily_activity (day, xp_earned, exercises_done) values (?, ?, 1)
       on conflict(day) do update set xp_earned = xp_earned + excluded.xp_earned, exercises_done = exercises_done + 1`,
    ).run(localDay(), xp);
    d.exec("commit");
  } catch (e) {
    d.exec("rollback");
    throw e;
  }
  return xp;
}

export function logAttempt(exerciseId: string, kind: "run" | "submit", payload: string, correct: boolean | null, feedback?: string) {
  db()
    .prepare("insert into attempts (exercise_id, kind, correct, payload, feedback, created_at) values (?, ?, ?, ?, ?, ?)")
    .run(exerciseId, kind, correct === null ? null : correct ? 1 : 0, payload, feedback ?? null, now());
}

export function completedSet(courseSlug?: string): Set<string> {
  const rows = (
    courseSlug
      ? db().prepare("select exercise_id from exercise_progress where course_slug = ?").all(courseSlug)
      : db().prepare("select exercise_id from exercise_progress").all()
  ) as { exercise_id: string }[];
  return new Set(rows.map((r) => r.exercise_id));
}

export function totalXp(): number {
  const r = db().prepare("select coalesce(sum(xp_earned), 0) as xp from exercise_progress").get() as { xp: number };
  return Number(r.xp);
}

export function lastCompleted(): ProgressRow | null {
  return (
    (db().prepare("select * from exercise_progress order by completed_at desc limit 1").get() as ProgressRow | undefined) ??
    null
  );
}

export function dailyActivity(days = 365): { day: string; xp_earned: number; exercises_done: number }[] {
  return db()
    .prepare("select day, xp_earned, exercises_done from daily_activity order by day desc limit ?")
    .all(days) as { day: string; xp_earned: number; exercises_done: number }[];
}

/** Consecutive days with XP, ending today (or yesterday, if today has none yet). */
export function streak(today = new Date()): number {
  const days = new Set(dailyActivity().filter((d) => d.xp_earned > 0 || d.exercises_done > 0).map((d) => d.day));
  const cursor = new Date(today);
  if (!days.has(localDay(cursor))) cursor.setDate(cursor.getDate() - 1);
  let n = 0;
  while (days.has(localDay(cursor))) {
    n++;
    cursor.setDate(cursor.getDate() - 1);
  }
  return n;
}

export function todayXp(): number {
  const r = db().prepare("select xp_earned from daily_activity where day = ?").get(localDay()) as
    | { xp_earned: number }
    | undefined;
  return r?.xp_earned ?? 0;
}

export function getSetting(key: string, fallback: string): string {
  const r = db().prepare("select value from settings where key = ?").get(key) as { value: string } | undefined;
  return r?.value ?? fallback;
}

export function setSetting(key: string, value: string) {
  db()
    .prepare("insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value")
    .run(key, value);
}

export const dailyGoal = () => Number(getSetting("daily_goal", "300"));

export function resetProgress(courseSlug?: string) {
  const d = db();
  if (courseSlug) {
    d.prepare("delete from exercise_progress where course_slug = ?").run(courseSlug);
    d.prepare("delete from exercise_state where exercise_id like ?").run(`${courseSlug}/%`);
    d.prepare("delete from attempts where exercise_id like ?").run(`${courseSlug}/%`);
  } else {
    d.exec(
      "delete from exercise_progress; delete from exercise_state; delete from attempts; delete from daily_activity; delete from monsters; delete from settings where key = 'partner';",
    );
  }
}
