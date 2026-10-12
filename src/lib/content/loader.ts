import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";
import type { z } from "zod";
import {
  CourseFile,
  LessonFile,
  TrackFile,
  exerciseXp,
  type Exercise,
  type CourseFile as CourseFileT,
} from "./schema";

// Content is read from disk on every call so lesson files written by the
// lesson-builder agent show up on the next page load, no restart.

export const CONTENT_DIR = process.env.CONTENT_DIR ?? path.join(process.cwd(), "content");
export const DATA_DIR = path.join(CONTENT_DIR, "datasets");

export class ContentError extends Error {
  constructor(
    public file: string,
    public issues: string[],
  ) {
    super(`${file}: ${issues.join("; ")}`);
  }
}

function readYaml<T extends z.ZodType>(file: string, schema: T): z.infer<T> {
  const rel = path.relative(CONTENT_DIR, file);
  let raw: unknown;
  try {
    raw = YAML.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    throw new ContentError(rel, [(e as Error).message]);
  }
  const parsed = schema.safeParse(raw);
  if (!parsed.success) {
    throw new ContentError(
      rel,
      parsed.error.issues.map((i) => `${i.path.join(".") || "(root)"}: ${i.message}`),
    );
  }
  return parsed.data;
}

export type Track = z.infer<typeof TrackFile> & { slug: string };

export type LessonRef = {
  id: string;
  title: string;
  chapterId: string;
  /** null when the lesson file has not been written yet, or is broken */
  exercises: ExerciseRef[] | null;
  /** validation error, when the lesson file exists but is broken */
  error?: string;
};

export type ExerciseRef = {
  /** stable id used in the progress DB: course/chapter/lesson/exercise */
  key: string;
  id: string;
  type: Exercise["type"];
  title: string;
  xp: number;
};

export type Chapter = { id: string; title: string; description: string; lessons: LessonRef[] };

export type Course = Omit<CourseFileT, "chapters"> & {
  slug: string;
  chapters: Chapter[];
  exerciseCount: number;
  xpTotal: number;
  hasContent: boolean;
};

export function exerciseKey(course: string, chapter: string, lesson: string, exercise: string) {
  return `${course}/${chapter}/${lesson}/${exercise}`;
}

export function listTracks(): Track[] {
  const dir = path.join(CONTENT_DIR, "tracks");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".yaml"))
    .map((f) => ({ ...readYaml(path.join(dir, f), TrackFile), slug: f.replace(/\.yaml$/, "") }))
    .sort((a, b) => a.order - b.order || a.title.localeCompare(b.title));
}

export function getTrack(slug: string): Track | null {
  return listTracks().find((t) => t.slug === slug) ?? null;
}

export function courseExists(slug: string) {
  return fs.existsSync(path.join(CONTENT_DIR, "courses", slug, "course.yaml"));
}

function lessonPath(course: string, chapter: string, lesson: string) {
  return path.join(CONTENT_DIR, "courses", course, chapter, `${lesson}.yaml`);
}

export function getLesson(course: string, chapter: string, lesson: string) {
  const file = lessonPath(course, chapter, lesson);
  if (!fs.existsSync(file)) return null;
  return readYaml(file, LessonFile);
}

export function getCourse(slug: string): Course | null {
  const file = path.join(CONTENT_DIR, "courses", slug, "course.yaml");
  if (!fs.existsSync(file)) return null;
  const c = readYaml(file, CourseFile);
  let exerciseCount = 0;
  let xpTotal = 0;
  const chapters: Chapter[] = c.chapters.map((ch) => ({
    id: ch.id,
    title: ch.title,
    description: ch.description,
    lessons: ch.lessons.map((lessonId): LessonRef => {
      // A broken lesson only breaks itself; the course page shows the error.
      let lesson: ReturnType<typeof getLesson>;
      try {
        lesson = getLesson(slug, ch.id, lessonId);
      } catch (e) {
        if (!(e instanceof ContentError)) throw e;
        return { id: lessonId, title: lessonId, chapterId: ch.id, exercises: null, error: e.message };
      }
      const exercises =
        lesson?.exercises.map((e) => {
          exerciseCount++;
          xpTotal += exerciseXp(e);
          return {
            key: exerciseKey(slug, ch.id, lessonId, e.id),
            id: e.id,
            type: e.type,
            title: e.title,
            xp: exerciseXp(e),
          };
        }) ?? null;
      return { id: lessonId, title: lesson?.title ?? lessonId, chapterId: ch.id, exercises };
    }),
  }));
  return { ...c, slug, chapters, exerciseCount, xpTotal, hasContent: exerciseCount > 0 };
}

/** All exercises of a course in play order, with their location. */
export function flattenCourse(course: Course) {
  const out: (ExerciseRef & { chapterId: string; lessonId: string; href: string })[] = [];
  for (const ch of course.chapters)
    for (const l of ch.lessons)
      for (const e of l.exercises ?? [])
        out.push({ ...e, chapterId: ch.id, lessonId: l.id, href: `/learn/${course.slug}/${ch.id}/${l.id}/${e.id}` });
  return out;
}

export function getExercise(course: string, chapter: string, lesson: string, exercise: string) {
  const l = getLesson(course, chapter, lesson);
  const e = l?.exercises.find((x) => x.id === exercise);
  return e && l ? { lesson: l, exercise: e } : null;
}

export function getExerciseByKey(key: string) {
  const [course, chapter, lesson, exercise] = key.split("/");
  if (!course || !chapter || !lesson || !exercise) return null;
  return getExercise(course, chapter, lesson, exercise);
}
