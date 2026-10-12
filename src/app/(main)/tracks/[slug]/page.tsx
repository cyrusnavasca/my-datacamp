import Link from "next/link";
import { notFound } from "next/navigation";
import { CourseStep } from "@/components/CourseCard";
import { PageHeader, ProgressBar } from "@/components/ui";
import { getTrack } from "@/lib/content/loader";
import { trackCourses } from "@/lib/course-progress";

export default async function TrackPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const track = getTrack(slug);
  if (!track) notFound();
  const courses = trackCourses(track.courses);
  const done = courses.reduce((n, c) => n + (c.status?.done ?? 0), 0);
  const total = courses.reduce((n, c) => n + (c.status?.total ?? 0), 0);
  const hours = courses.reduce((n, c) => n + (c.course?.est_hours ?? 0), 0);

  return (
    <>
      <PageHeader
        title={track.title}
        eyebrow={
          <Link href="/tracks" className="hover:underline">
            Tracks
          </Link>
        }
      >
        {track.description}
      </PageHeader>
      <div className="mb-8 max-w-md">
        <p className="mb-2 text-sm text-text-muted">
          {courses.length} courses · about {hours} hours
        </p>
        <ProgressBar value={done} max={total} label="Track progress" />
      </div>
      <ol className="max-w-3xl divide-y divide-border border-t border-border">
        {courses.map((c, i) => (
          <CourseStep key={c.slug} n={i + 1} item={c} />
        ))}
      </ol>
    </>
  );
}
