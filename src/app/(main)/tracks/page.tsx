import Link from "next/link";
import { EmptyState, PageHeader, ProgressBar } from "@/components/ui";
import { listTracks } from "@/lib/content/loader";
import { trackCourses } from "@/lib/course-progress";

export default function TracksPage() {
  const tracks = listTracks();
  return (
    <>
      <PageHeader title="Tracks">Ordered paths of courses. Work through them top to bottom, or jump in anywhere.</PageHeader>
      {tracks.length === 0 ? (
        <EmptyState title="No tracks yet">
          Add a file to <code className="font-mono">content/tracks/</code>.
        </EmptyState>
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {tracks.map((t) => {
            const courses = trackCourses(t.courses);
            const done = courses.reduce((n, c) => n + (c.status?.done ?? 0), 0);
            const total = courses.reduce((n, c) => n + (c.status?.total ?? 0), 0);
            const hours = courses.reduce((n, c) => n + (c.course?.est_hours ?? 0), 0);
            return (
              <li key={t.slug}>
                <Link href={`/tracks/${t.slug}`} className="block h-full rounded-lg border border-border bg-bg p-5 transition-colors hover:border-border-input">
                  <h2 className="text-lg">{t.title}</h2>
                  <p className="mt-2 text-sm text-text-muted">{t.description}</p>
                  <p className="mt-4 text-xs text-text-muted">
                    {t.courses.length} courses · about {hours} hours
                  </p>
                  <div className="mt-2">
                    <ProgressBar value={done} max={total} label={`${t.title} progress`} />
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
