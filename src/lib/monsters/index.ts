import { getCourse } from "../content/loader";
import { db } from "../db";
import { completedSet, getSetting, setSetting, totalXp } from "../progress";
import { CATCH_LEVEL, EVOLVE_AT, TYPE_BONUS, formFor, levelFor, xpForLevel } from "./level";
import { ROSTER, getLine, lineForCourse, type MonsterLine } from "./roster";

// Server-side monster state: which lines are owned, the partner, and what
// happens when an exercise is finished. Rules are in level.ts.

export class MonsterError extends Error {}

export type Owned = { line: MonsterLine; xp: number; level: number; form: 0 | 1 | 2; caughtAt: string };

/** What the client needs to draw and label a monster. */
export type MonsterView = { id: string; xp: number; level: number; form: 0 | 1 | 2 };

export type MonsterEvent = {
  /** XP the partner got from this exercise, and where it ended up. */
  partner?: { id: string; gained: number; bonus: boolean; from: MonsterView; to: MonsterView };
  /** Lines caught by this exercise. */
  caught: MonsterView[];
};

const now = () => new Date().toISOString();

function toOwned(row: { line_id: string; xp: number; caught_at: string }): Owned | null {
  const line = getLine(row.line_id);
  if (!line) return null; // a line removed from the roster
  const level = levelFor(row.xp);
  return { line, xp: row.xp, level, form: formFor(level), caughtAt: row.caught_at };
}

export const view = (o: Owned): MonsterView => ({ id: o.line.id, xp: o.xp, level: o.level, form: o.form });

export function ownedMonsters(): Owned[] {
  const rows = db().prepare("select line_id, xp, caught_at from monsters order by caught_at").all() as {
    line_id: string;
    xp: number;
    caught_at: string;
  }[];
  return rows.map(toOwned).filter((o): o is Owned => o !== null);
}

export function getOwned(id: string): Owned | null {
  const row = db().prepare("select line_id, xp, caught_at from monsters where line_id = ?").get(id) as
    | { line_id: string; xp: number; caught_at: string }
    | undefined;
  return row ? toOwned(row) : null;
}

export function getPartner(): Owned | null {
  const id = getSetting("partner", "");
  return id ? getOwned(id) : null;
}

/** One starter to begin with, plus one more for every monster in its final form. */
export function starterSlots(owned = ownedMonsters()) {
  const used = owned.filter((o) => o.line.starter).length;
  const total = 1 + owned.filter((o) => o.level >= EVOLVE_AT[1]).length;
  return { used, total, open: Math.max(0, total - used) };
}

function insert(id: string, xp: number) {
  db().prepare("insert into monsters (line_id, xp, caught_at) values (?, ?, ?)").run(id, xp, now());
}

/**
 * Makes an owned monster the partner, or adopts a starter into an open slot.
 * The first partner ever chosen as a starter gets all XP earned so far.
 */
export function choosePartner(id: string): Owned {
  const line = getLine(id);
  if (!line) throw new MonsterError(`no monster called ${id}`);
  if (!getOwned(id)) {
    if (!line.starter) throw new MonsterError(`${line.forms[0].name} has not been caught yet`);
    if (starterSlots().open === 0) throw new MonsterError("no starter slot open");
    insert(id, getSetting("partner", "") ? xpForLevel(CATCH_LEVEL) : totalXp());
  }
  setSetting("partner", id);
  return getOwned(id)!;
}

/** Chapters with at least one exercise, where every exercise is done. */
function hasFinishedChapter(courseSlug: string): boolean {
  const course = getCourse(courseSlug);
  if (!course) return false;
  const done = completedSet(courseSlug);
  return course.chapters.some((ch) => {
    const keys = ch.lessons.flatMap((l) => (l.exercises ?? []).map((e) => e.key));
    return keys.length > 0 && keys.every((k) => done.has(k));
  });
}

/** Catches every course monster whose course has a finished chapter. Returns the new ones. */
export function syncCatches(courseSlugs = ROSTER.flatMap((l) => (l.course ? [l.course] : []))): Owned[] {
  const caught: Owned[] = [];
  for (const slug of courseSlugs) {
    const line = lineForCourse(slug);
    if (!line || getOwned(line.id) || !hasFinishedChapter(slug)) continue;
    insert(line.id, xpForLevel(CATCH_LEVEL));
    caught.push(getOwned(line.id)!);
  }
  return caught;
}

/** Courses the learner has started: their monsters show up in the Dex as seen. */
export function seenCourses(): Set<string> {
  const rows = db().prepare("select distinct course_slug from exercise_progress").all() as { course_slug: string }[];
  return new Set(rows.map((r) => r.course_slug));
}

/** Called after an exercise is finished for the first time with the XP it earned. */
export function onExerciseComplete(exerciseKey: string, xp: number): MonsterEvent | undefined {
  const course = exerciseKey.split("/")[0];
  const caught = syncCatches([course]).map(view);
  let partner: MonsterEvent["partner"];
  const p = getPartner();
  if (p && xp > 0) {
    const bonus = lineForCourse(course)?.type === p.line.type;
    const gained = Math.round(xp * (bonus ? TYPE_BONUS : 1));
    db().prepare("update monsters set xp = xp + ? where line_id = ?").run(gained, p.line.id);
    partner = { id: p.line.id, gained, bonus, from: view(p), to: view(getOwned(p.line.id)!) };
  }
  return partner || caught.length ? { partner, caught } : undefined;
}
