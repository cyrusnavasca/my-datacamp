import { notFound } from "next/navigation";
import { ButtonLink, Card, Stats } from "@/components/ui";
import { getCourse, listTracks } from "@/lib/content/loader";
import { courseStatus, safeGetCourse } from "@/lib/course-progress";
import { db } from "@/lib/db";

export default async function CourseComplete({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const course = getCourse(slug);
  if (!course) notFound();
  const status = courseStatus(course);
  const { xp, hints, solutions } = db()
    .prepare(
      "select coalesce(sum(xp_earned),0) as xp, coalesce(sum(hint_used),0) as hints, coalesce(sum(solution_used),0) as solutions from exercise_progress where course_slug = ?",
    )
    .get(slug) as { xp: number; hints: number; solutions: number };

  const track = listTracks().find((t) => t.courses.includes(slug));
  const nextSlug = track ? track.courses[track.courses.indexOf(slug) + 1] : undefined;
  const next = nextSlug ? safeGetCourse(nextSlug).course : null;

  return (
    <div className="mx-auto max-w-xl text-center">
      <h1 className="text-xl">{status.state === "done" ? "Course complete" : "Almost there"}</h1>
      <p className="mt-2 text-text-muted">{course.title}</p>
      <div className="mt-8 text-left">
        <Stats
          label="Course results"
          items={[
            { label: "XP earned", value: Number(xp) },
            { label: "Hints used", value: Number(hints) },
            { label: "Answers shown", value: Number(solutions) },
          ]}
        />
      </div>
      {status.state !== "done" && (
        <p className="mt-6 text-sm text-text-muted">
          {status.total - status.done} exercises are still open. Finish them to complete the course.
        </p>
      )}
      {next ? (
        <Card className="mt-8 text-left">
          <p className="text-sm text-text-muted">Next in {track?.title}</p>
          <h2 className="mt-1 text-lg">{next.title}</h2>
          <p className="mt-1 text-sm text-text-muted">{next.description}</p>
          <ButtonLink href={`/courses/${nextSlug}`} className="mt-4">
            Go to next course
          </ButtonLink>
        </Card>
      ) : (
        <ButtonLink href="/" className="mt-8">
          Back to dashboard
        </ButtonLink>
      )}
    </div>
  );
}
