import { notFound } from "next/navigation";
import { Player, type PlayerProps } from "@/components/player/Player";
import { exerciseKey, flattenCourse, getCourse, getExercise } from "@/lib/content/loader";
import { exerciseXp } from "@/lib/content/schema";
import { toPublic } from "@/lib/exercises";
import { getPartner, view } from "@/lib/monsters";
import { completedSet, getProgress, getState, totalXp } from "@/lib/progress";

type Params = { course: string; chapter: string; lesson: string; exercise: string };

export default async function LearnPage({ params }: { params: Promise<Params> }) {
  const p = await params;
  const course = getCourse(p.course);
  const found = getExercise(p.course, p.chapter, p.lesson, p.exercise);
  if (!course || !found) notFound();

  const key = exerciseKey(p.course, p.chapter, p.lesson, p.exercise);
  const { exercise, lesson } = found;
  const all = flattenCourse(course);
  const idx = all.findIndex((e) => e.key === key);
  const completed = completedSet(p.course);
  const state = getState(key);
  const progress = getProgress(key);
  const partner = getPartner();
  const chapterIdx = course.chapters.findIndex((c) => c.id === p.chapter);
  const chapter = course.chapters[chapterIdx];
  const next = all[idx + 1];
  const lessonExercises = all.filter((e) => e.chapterId === p.chapter && e.lessonId === p.lesson);

  let hint: string | null = null;
  if (state.hint_used && exercise.type !== "video") {
    hint = exercise.type === "sequential" ? (exercise.steps[Math.min(state.steps_done, exercise.steps.length - 1)]?.hint ?? null) : exercise.hint;
  }

  const props: PlayerProps = {
    exerciseKey: key,
    exercise: toPublic(key, exercise),
    course: { slug: course.slug, title: course.title },
    chapter: { id: chapter.id, title: chapter.title, n: chapterIdx + 1 },
    lessonTitle: lesson.title,
    dots: lessonExercises.map((e) => ({ href: e.href, title: e.title, type: e.type, done: completed.has(e.key), current: e.key === key })),
    position: { index: idx + 1, total: all.length },
    prevHref: all[idx - 1]?.href ?? null,
    nextHref: next?.href ?? null,
    endsChapter: !next || next.chapterId !== p.chapter,
    nextChapterTitle: next && next.chapterId !== p.chapter ? course.chapters.find((c) => c.id === next.chapterId)?.title ?? null : null,
    chapterExercises: all.filter((e) => e.chapterId === p.chapter).map((e) => e.key),
    completedKeys: [...completed],
    outline: course.chapters.map((c) => ({
      id: c.id,
      title: c.title,
      lessons: c.lessons.map((l) => ({
        id: l.id,
        title: l.title,
        exercises: (l.exercises ?? []).map((e) => ({ key: e.key, title: e.title, type: e.type, href: `/learn/${course.slug}/${c.id}/${l.id}/${e.id}` })),
      })),
    })),
    initial: {
      done: Boolean(progress),
      xpEarned: progress?.xp_earned ?? null,
      hintUsed: Boolean(state.hint_used),
      solutionUsed: Boolean(state.solution_used),
      wrongCount: state.wrong_count,
      stepsDone: state.steps_done,
      lastCode: state.last_code,
      hint,
    },
    baseXp: exerciseXp(exercise),
    totalXp: totalXp(),
    partner: partner ? view(partner) : null,
  };
  return <Player {...props} />;
}
