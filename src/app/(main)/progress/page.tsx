import Link from "next/link";
import { EmptyState, PageHeader, ProgressBar, Stats } from "@/components/ui";
import { courseStatus, safeGetCourse } from "@/lib/course-progress";
import { db } from "@/lib/db";
import { dailyActivity, localDay, streak, totalXp } from "@/lib/progress";

const WEEKS = 26;

export default function ProgressPage() {
  const activity = new Map(dailyActivity(WEEKS * 7 + 7).map((d) => [d.day, d]));
  const courseRows = db()
    .prepare("select course_slug, count(*) as n, sum(xp_earned) as xp, max(completed_at) as last from exercise_progress group by course_slug order by last desc")
    .all() as { course_slug: string; n: number; xp: number; last: string }[];

  // Calendar: columns are weeks (Mon-Sun), the last column is this week.
  const today = new Date();
  const start = new Date(today);
  start.setDate(start.getDate() - ((today.getDay() + 6) % 7) - (WEEKS - 1) * 7);
  const days: { day: string; xp: number; future: boolean }[] = [];
  for (let i = 0; i < WEEKS * 7; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    const key = localDay(d);
    days.push({ day: key, xp: activity.get(key)?.xp_earned ?? 0, future: d > today });
  }
  const level = (xp: number) => (xp === 0 ? 0 : xp < 100 ? 1 : xp < 300 ? 2 : 3);
  const levelClass = ["bg-surface-2", "bg-accent-soft", "bg-accent/60", "bg-accent"];
  const totalDays = [...activity.values()].filter((d) => d.xp_earned > 0).length;

  return (
    <>
      <PageHeader title="Progress">Your XP, streak and finished work.</PageHeader>
      <Stats
        label="Totals"
        items={[
          { label: "Total XP", value: totalXp().toLocaleString() },
          { label: "Current streak", value: `${streak()} days` },
          { label: "Active days", value: totalDays },
        ]}
      />

      <section className="mt-10" aria-labelledby="cal-h">
        <h2 id="cal-h" className="mb-3 text-lg">
          Last {WEEKS} weeks
        </h2>
        <div className="overflow-x-auto pb-2">
          <div className="grid w-max grid-flow-col grid-rows-7 gap-1" role="img" aria-label={`XP per day over the last ${WEEKS} weeks`}>
            {days.map((d) => (
              <div
                key={d.day}
                title={`${d.day}: ${d.xp} XP`}
                className={`size-3 rounded-sm ${d.future ? "bg-transparent" : levelClass[level(d.xp)]}`}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="mt-10" aria-labelledby="courses-h">
        <h2 id="courses-h" className="mb-3 text-lg">
          Courses
        </h2>
        {courseRows.length === 0 ? (
          <EmptyState title="Nothing finished yet">Complete an exercise and it shows up here.</EmptyState>
        ) : (
          <ul className="divide-y divide-border">
            {courseRows.map((r) => {
              const { course } = safeGetCourse(r.course_slug);
              const status = course ? courseStatus(course) : null;
              return (
                <li key={r.course_slug} className="py-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <Link href={`/courses/${r.course_slug}`} className="font-semibold hover:underline">
                      {course?.title ?? r.course_slug}
                    </Link>
                    <span className="text-sm text-text-muted tabular-nums">{Number(r.xp)} XP</span>
                  </div>
                  {status && (
                    <div className="mt-2">
                      <ProgressBar value={status.done} max={status.total} label={`${course?.title} progress`} />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </>
  );
}
