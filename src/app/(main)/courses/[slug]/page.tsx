import Link from "next/link";
import { notFound } from "next/navigation";
import { CheckCircle2, Circle, Clock, FileText, Zap } from "lucide-react";
import { StatusBadge } from "@/components/CourseCard";
import { ExerciseIcon } from "@/components/ExerciseIcon";
import { ButtonLink, EmptyState, PageHeader, ProgressBar } from "@/components/ui";
import { getCourse, listTracks } from "@/lib/content/loader";
import { courseStatus } from "@/lib/course-progress";
import { completedSet } from "@/lib/progress";

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

export default async function CoursePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const course = getCourse(slug);
  if (!course) notFound();
  const completed = completedSet(slug);
  const status = courseStatus(course, completed);
  const track = listTracks().find((t) => t.courses.includes(slug));
  const videos = course.chapters.flatMap((c) => c.lessons.flatMap((l) => l.exercises ?? [])).filter((e) => e.type === "video").length;

  return (
    <>
      <PageHeader
        title={course.title}
        eyebrow={
          track ? (
            <Link href={`/tracks/${track.slug}`} className="hover:underline">
              {track.title}
            </Link>
          ) : (
            "Course"
          )
        }
      >
        {course.description}
      </PageHeader>

      <div className="mb-8 flex flex-col gap-6 lg:flex-row lg:items-start">
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-text-muted">
          <span className="inline-flex items-center gap-1.5">
            <Clock className="size-4" aria-hidden /> {course.est_hours} hours
          </span>
          <span className="inline-flex items-center gap-1.5">
            <FileText className="size-4" aria-hidden /> {plural(videos, "lesson")}, {plural(status.total - videos, "exercise")}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Zap className="size-4" aria-hidden /> {course.xpTotal.toLocaleString()} XP
          </span>
          <StatusBadge state={status.state} />
        </div>
        {status.nextHref && (
          <div className="lg:ml-auto">
            <ButtonLink href={status.nextHref} size="lg">
              {status.state === "todo" ? "Start course" : status.state === "done" ? "Review course" : "Continue course"}
            </ButtonLink>
          </div>
        )}
      </div>

      {status.total > 0 && (
        <div className="mb-8 max-w-md">
          <ProgressBar value={status.done} max={status.total} label="Course progress" />
        </div>
      )}

      {course.objectives.length > 0 && (
        <section className="mb-10 max-w-3xl">
          <h2 className="font-semibold">What you will be able to do</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-text-muted marker:text-border-input">
            {course.objectives.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
        </section>
      )}

      {!course.hasContent && (
        <div className="mb-8 max-w-3xl">
          <EmptyState title="No lessons in this course yet">
            The outline below is the plan. The lesson builder writes the lesson files into{" "}
            <code className="font-mono">content/courses/{slug}/</code>.
          </EmptyState>
        </div>
      )}

      <ol className="max-w-3xl space-y-3">
        {course.chapters.map((ch, i) => {
          const exercises = ch.lessons.flatMap((l) => l.exercises ?? []);
          const chDone = exercises.filter((e) => completed.has(e.key)).length;
          return (
            <li key={ch.id}>
              <details className="group rounded-lg border border-border bg-bg" open={i === 0 || (chDone > 0 && chDone < exercises.length)}>
                <summary className="flex cursor-pointer list-none items-start gap-4 p-5">
                  <span className="w-5 shrink-0 pt-0.5 text-right text-sm font-semibold text-text-muted tabular-nums" aria-hidden>
                    {i + 1}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-semibold break-words">{ch.title}</span>
                    {ch.description && <span className="mt-1 block text-sm text-text-muted">{ch.description}</span>}
                  </span>
                  <span className="shrink-0 text-xs text-text-muted tabular-nums">
                    {exercises.length > 0 ? `${chDone}/${exercises.length}` : "planned"}
                  </span>
                </summary>
                <div className="border-t border-border px-5 py-3">
                  {ch.lessons.length === 0 && <p className="py-2 text-sm text-text-muted">No lessons yet.</p>}
                  {ch.lessons.map((l) => (
                    <div key={l.id} className="py-2">
                      <p className="text-sm font-medium">{l.title}</p>
                      {l.error ? (
                        <p className="font-mono text-xs break-words text-danger">{l.error}</p>
                      ) : l.exercises === null ? (
                        <p className="text-xs text-text-muted">Lesson file not written yet.</p>
                      ) : (
                        <ul className="mt-1">
                          {l.exercises.map((e) => {
                            const isDone = completed.has(e.key);
                            return (
                              <li key={e.key}>
                                <Link
                                  href={`/learn/${slug}/${ch.id}/${l.id}/${e.id}`}
                                  className="flex items-center gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-surface"
                                >
                                  <ExerciseIcon type={e.type} />
                                  <span className="min-w-0 flex-1 truncate">{e.title}</span>
                                  <span className="text-xs text-text-muted tabular-nums">{e.xp} XP</span>
                                  {isDone ? (
                                    <CheckCircle2 className="size-4 text-success" aria-label="Done" />
                                  ) : (
                                    <Circle className="size-4 text-border-input" aria-label="Not done" />
                                  )}
                                </Link>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              </details>
            </li>
          );
        })}
      </ol>
    </>
  );
}
