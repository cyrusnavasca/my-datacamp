import { ContentError, flattenCourse, getCourse, listTracks, type Course } from "./content/loader";
import { completedSet, lastCompleted } from "./progress";

export type CourseStatus = {
  done: number;
  total: number;
  state: "empty" | "todo" | "progress" | "done";
  /** next unfinished exercise, or the first one when the course is complete */
  nextHref: string | null;
};

export function courseStatus(course: Course, completed = completedSet(course.slug)): CourseStatus {
  const all = flattenCourse(course);
  const done = all.filter((e) => completed.has(e.key)).length;
  const next = all.find((e) => !completed.has(e.key)) ?? all[0];
  const state = all.length === 0 ? "empty" : done === 0 ? "todo" : done === all.length ? "done" : "progress";
  return { done, total: all.length, state, nextHref: next?.href ?? null };
}

export type TrackCourse = { slug: string; course: Course | null; status: CourseStatus | null; error?: string };

/** getCourse, but a broken course.yaml becomes an error instead of a crash. */
export function safeGetCourse(slug: string): { course: Course | null; error?: string } {
  try {
    return { course: getCourse(slug) };
  } catch (e) {
    if (e instanceof ContentError) return { course: null, error: e.message };
    throw e;
  }
}

export function trackCourses(courseSlugs: string[]): TrackCourse[] {
  const completed = completedSet();
  return courseSlugs.map((slug) => {
    const { course, error } = safeGetCourse(slug);
    return { slug, course, error, status: course ? courseStatus(course, completed) : null };
  });
}

/** Where "Continue" on the dashboard goes. */
export function resumeTarget(): { course: Course; status: CourseStatus } | null {
  const last = lastCompleted();
  if (last) {
    const { course } = safeGetCourse(last.course_slug);
    if (course) {
      const status = courseStatus(course);
      if (status.state !== "done") return { course, status };
    }
  }
  // Otherwise: first course with content that is not finished, in track order.
  const completed = completedSet();
  for (const t of listTracks())
    for (const slug of t.courses) {
      const { course } = safeGetCourse(slug);
      if (!course) continue;
      const status = courseStatus(course, completed);
      if (status.state === "todo" || status.state === "progress") return { course, status };
    }
  return null;
}
