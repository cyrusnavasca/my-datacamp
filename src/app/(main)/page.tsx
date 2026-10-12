import Link from "next/link";
import { Sprite } from "@/components/monsters/Sprite";
import { ButtonLink, Card, EmptyState, ProgressBar, Stats } from "@/components/ui";
import { listTracks } from "@/lib/content/loader";
import { resumeTarget, trackCourses } from "@/lib/course-progress";
import { getPartner } from "@/lib/monsters";
import { levelProgress, nextEvolution } from "@/lib/monsters/level";
import { STARTERS } from "@/lib/monsters/roster";
import { dailyGoal, streak, todayXp, totalXp } from "@/lib/progress";

export default function Dashboard() {
  const resume = resumeTarget();
  const tracks = listTracks().map((t) => {
    const courses = trackCourses(t.courses);
    const done = courses.reduce((n, c) => n + (c.status?.done ?? 0), 0);
    const total = courses.reduce((n, c) => n + (c.status?.total ?? 0), 0);
    return { ...t, done, total, ready: courses.filter((c) => c.status && c.status.total > 0).length };
  });
  const goal = dailyGoal();
  const today = todayXp();

  return (
    <div className="space-y-10">
      <section aria-labelledby="resume-h">
        <h1 id="resume-h" className="sr-only">
          Dashboard
        </h1>
        {resume ? (
          <Card className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="text-sm text-text-muted">{resume.status.state === "todo" ? "Start learning" : "Pick up where you left off"}</p>
              <h2 className="mt-1 text-lg break-words">{resume.course.title}</h2>
              <div className="mt-3 max-w-md">
                <ProgressBar value={resume.status.done} max={resume.status.total} label="Course progress" />
              </div>
            </div>
            {resume.status.nextHref && (
              <ButtonLink href={resume.status.nextHref} size="lg">
                {resume.status.state === "todo" ? "Start course" : "Continue"}
              </ButtonLink>
            )}
          </Card>
        ) : (
          <EmptyState title="No lessons to work on yet">
            The tracks are outlined but have no lesson files. Ask the lesson builder to write the first course, then reload.
          </EmptyState>
        )}
      </section>

      <PartnerSummary />

      <Stats
        label="Stats"
        items={[
          { label: "Total XP", value: totalXp().toLocaleString() },
          { label: "Day streak", value: streak() },
          { label: "XP today", value: today },
          {
            label: "Daily goal",
            value: (
              <>
                {Math.min(today, goal)}
                <span className="text-sm font-normal text-text-muted"> / {goal}</span>
              </>
            ),
            sub: <ProgressBar value={Math.min(today, goal)} max={goal} label="Daily goal" thin />,
          },
        ]}
      />

      <section aria-labelledby="tracks-h">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 id="tracks-h" className="text-lg">
            Your tracks
          </h2>
          <Link href="/tracks" className="text-sm text-accent-text hover:underline">
            All tracks
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {tracks.map((t) => (
            <Link key={t.slug} href={`/tracks/${t.slug}`} className="rounded-lg border border-border bg-bg p-5 transition-colors hover:border-border-input">
              <h3 className="font-semibold">{t.title}</h3>
              <p className="mt-1 line-clamp-2 text-sm text-text-muted">{t.description}</p>
              <p className="mt-3 text-xs text-text-muted">
                {t.courses.length} courses · {t.ready} with lessons
              </p>
              <div className="mt-2">
                <ProgressBar value={t.done} max={t.total} label={`${t.title} progress`} />
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function PartnerSummary() {
  const partner = getPartner();
  if (!partner)
    return (
      <Link href="/dex" className="flex items-center gap-4 rounded-lg border border-dashed border-border-input p-4 hover:bg-surface">
        <div className="flex">
          {STARTERS.map((s) => (
            <Sprite key={s.id} id={s.id} size={48} />
          ))}
        </div>
        <div className="min-w-0">
          <p className="font-semibold">Choose your first partner</p>
          <p className="text-sm text-text-muted">A monster that levels up and evolves with the XP you earn.</p>
        </div>
      </Link>
    );
  const { into, span } = levelProgress(partner.xp);
  const evolveAt = nextEvolution(partner.level);
  return (
    <Link href="/dex" className="flex items-center gap-4 rounded-lg border border-border p-4 transition-colors hover:border-border-input">
      <Sprite id={partner.line.id} form={partner.form} size={64} />
      <div className="min-w-0 flex-1">
        <p className="text-sm text-text-muted">Partner</p>
        <p className="font-semibold">
          {partner.line.forms[partner.form].name} <span className="font-normal text-text-muted tabular-nums">Lv {partner.level}</span>
        </p>
        <div className="mt-2 max-w-xs">
          <ProgressBar value={into} max={span} label="Partner XP to next level" thin />
        </div>
      </div>
      {evolveAt && <p className="hidden text-sm text-text-muted sm:block">Evolves at Lv {evolveAt}</p>}
    </Link>
  );
}
