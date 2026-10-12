import Link from "next/link";
import { Sprite, TypeBadge } from "@/components/monsters/Sprite";
import { Badge, Card, PageHeader, ProgressBar } from "@/components/ui";
import { safeGetCourse } from "@/lib/course-progress";
import { getPartner, ownedMonsters, seenCourses, starterSlots, syncCatches, type Owned } from "@/lib/monsters";
import { CATCH_LEVEL, EVOLVE_AT, MAX_LEVEL, TYPE_BONUS, levelProgress, nextEvolution } from "@/lib/monsters/level";
import { ROSTER, STARTERS, TYPE_LABEL } from "@/lib/monsters/roster";
import { totalXp } from "@/lib/progress";
import { PartnerButton } from "./PartnerButton";

export default function DexPage() {
  syncCatches(); // catches earned before monsters existed, or content added since
  const owned = new Map(ownedMonsters().map((o) => [o.line.id, o]));
  const partner = getPartner();
  const slots = starterSlots([...owned.values()]);
  const seen = seenCourses();
  const courseTitle = (slug: string) => safeGetCourse(slug).course?.title ?? slug;

  return (
    <div className="space-y-12">
      <PageHeader title="Dex">
        Monsters you raise by learning. Your partner gets the XP from every exercise you finish, levels up and evolves.
      </PageHeader>

      {partner ? <PartnerPanel p={partner} /> : slots.open > 0 && <StarterPicker xp={totalXp()} />}

      <section aria-labelledby="rules-h">
        <h2 id="rules-h" className="text-lg">
          How it works
        </h2>
        <ul className="mt-3 max-w-2xl list-disc space-y-1.5 pl-5 text-sm text-text-muted">
          <li>Your partner gets the XP from every exercise you finish, hints and penalties included.</li>
          <li>
            Type match: ×{TYPE_BONUS} XP when your partner shares a type with the course&apos;s own monster, like a{" "}
            {TYPE_LABEL.code} partner in Python for Data Science.
          </li>
          <li>
            Monsters evolve at Lv {EVOLVE_AT[0]} and Lv {EVOLVE_AT[1]}.
          </li>
          <li>Finish any chapter of a course to catch its monster. It joins at Lv {CATCH_LEVEL}.</li>
          <li>Every monster that reaches its final form opens a slot to adopt another starter.</li>
        </ul>
      </section>

      <section aria-labelledby="dex-h">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 id="dex-h" className="text-lg">
            Collection
          </h2>
          <p className="text-sm text-text-muted tabular-nums">
            {owned.size} of {ROSTER.length} caught
          </p>
        </div>
        <ol className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {ROSTER.map((line, i) => {
            const o = owned.get(line.id);
            const known = Boolean(o) || line.starter || (line.course !== undefined && seen.has(line.course));
            const name = o ? line.forms[o.form].name : known ? line.forms[0].name : "???";
            return (
              <li key={line.id} className="flex flex-col items-center gap-2 rounded-lg border border-border p-4 text-center">
                <span className="self-start text-xs text-text-muted tabular-nums">#{String(i + 1).padStart(3, "0")}</span>
                <Sprite id={line.id} form={o?.form ?? 0} size={80} silhouette={!o} />
                <p className="font-semibold">{name}</p>
                {known && <TypeBadge type={line.type} />}
                <div className="mt-auto flex min-h-8 flex-col items-center justify-end gap-1 pt-1 text-xs text-text-muted">
                  {o ? (
                    <>
                      <span className="tabular-nums">Lv {o.level}</span>
                      {partner?.line.id === line.id ? (
                        <Badge tone="progress">Partner</Badge>
                      ) : (
                        <PartnerButton id={line.id}>Make partner</PartnerButton>
                      )}
                    </>
                  ) : line.starter ? (
                    slots.open === 0 ? (
                      <span>Starter. A slot opens when a monster reaches its final form.</span>
                    ) : partner ? (
                      <PartnerButton id={line.id}>Adopt</PartnerButton>
                    ) : (
                      <span>Starter. Choose one above.</span>
                    )
                  ) : (
                    line.course && (
                      <span>
                        Finish a chapter of{" "}
                        <Link href={`/courses/${line.course}`} className="text-accent-text hover:underline">
                          {courseTitle(line.course)}
                        </Link>
                      </span>
                    )
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}

function PartnerPanel({ p }: { p: Owned }) {
  const { into, span } = levelProgress(p.xp);
  const evolveAt = nextEvolution(p.level);
  const form = p.line.forms[p.form];
  return (
    <section aria-labelledby="partner-h">
      <Card className="flex flex-col gap-6 sm:flex-row sm:items-center">
        <div className="flex justify-center rounded-md bg-surface p-4">
          <Sprite id={p.line.id} form={p.form} size={160} label={form.name} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-text-muted">Your partner</p>
          <h2 id="partner-h" className="mt-1 text-xl">
            {form.name}
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <TypeBadge type={p.line.type} />
            <span className="text-sm font-semibold tabular-nums">Lv {p.level}</span>
          </div>
          <p className="mt-3 max-w-prose text-sm">{form.dex}</p>
          <div className="mt-4 max-w-md">
            <ProgressBar value={into} max={span} label="XP to next level" />
            <p className="mt-1 text-xs text-text-muted tabular-nums">
              {p.level >= MAX_LEVEL ? "Max level" : `${(span - into).toLocaleString()} XP to Lv ${p.level + 1}`}
            </p>
          </div>
          <p className="mt-3 flex items-center gap-2 text-sm text-text-muted">
            {evolveAt ? (
              <>
                <Sprite id={p.line.id} form={p.form + 1} size={32} silhouette />
                Evolves at Lv {evolveAt}
              </>
            ) : (
              "Final form"
            )}
          </p>
        </div>
      </Card>
    </section>
  );
}

function StarterPicker({ xp }: { xp: number }) {
  return (
    <section aria-labelledby="starter-h">
      <h2 id="starter-h" className="text-lg">
        Choose your partner
      </h2>
      <p className="mt-1 max-w-2xl text-sm text-text-muted">
        {xp > 0
          ? `Your starter begins with the ${xp.toLocaleString()} XP you've already earned.`
          : "Your starter grows with every exercise you finish."}
      </p>
      <ul className="mt-4 grid gap-4 sm:grid-cols-3">
        {STARTERS.map((s) => (
          <li key={s.id}>
            <Card className="flex h-full flex-col items-center gap-2 text-center">
              <Sprite id={s.id} size={112} label={s.forms[0].name} />
              <h3 className="font-semibold">{s.forms[0].name}</h3>
              <TypeBadge type={s.type} />
              <p className="text-sm text-text-muted">{s.forms[0].dex}</p>
              <div className="mt-auto pt-2">
                <PartnerButton id={s.id} size="md">
                  Choose {s.forms[0].name}
                </PartnerButton>
              </div>
            </Card>
          </li>
        ))}
      </ul>
    </section>
  );
}
