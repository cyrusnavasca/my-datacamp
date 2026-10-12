import { cx } from "@/components/ui";
import { getLine, TYPE_LABEL, type MonsterType } from "@/lib/monsters/roster";
import { PX, spriteRuns } from "@/lib/monsters/sprite";

// Works in server and client components: no hooks, no browser APIs.
// Fills use the --c-* token variables from tokens.css: Tailwind inlines its
// --color-* theme values into utilities, so those don't exist at runtime.

const mix = (a: string, pct: number, b: string) => `color-mix(in oklab, var(--c-${a}) ${pct}%, var(--c-${b}))`;

function fills(type: MonsterType, part: MonsterType): Record<number, string> {
  return {
    [PX.body]: `var(--c-type-${type})`,
    [PX.light]: mix(`type-${type}`, 45, "sprite-light"),
    [PX.shade]: mix(`type-${type}`, 70, "sprite-ink"),
    [PX.ink]: "var(--c-sprite-ink)",
    [PX.shine]: "var(--c-sprite-light)",
    [PX.part]: `var(--c-type-${part})`,
    [PX.partShade]: mix(`type-${part}`, 70, "sprite-ink"),
  };
}

/**
 * A monster's pixel sprite. `silhouette` hides it (not caught yet).
 * Decorative unless `label` is given.
 */
export function Sprite({
  id,
  form = 0,
  size = 64,
  silhouette,
  label,
  className,
}: {
  id: string;
  form?: number;
  size?: number;
  silhouette?: boolean;
  label?: string;
  className?: string;
}) {
  const line = getLine(id);
  if (!line) return null;
  const { runs, box } = spriteRuns(line, form);
  const paths = new Map<number, string>();
  for (const r of runs) {
    const v = silhouette ? PX.body : r.v;
    paths.set(v, (paths.get(v) ?? "") + `M${r.x} ${r.y}h${r.w}v1h-${r.w}z`);
  }
  const fill = fills(line.type, line.art.part);
  return (
    <svg
      viewBox={`${box.x} ${box.y} ${box.size} ${box.size}`}
      width={size}
      height={size}
      shapeRendering="crispEdges"
      className={cx("shrink-0", className)}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      {[...paths].map(([v, d]) => (
        <path key={v} d={d} style={{ fill: silhouette ? "var(--c-border-input)" : fill[v] }} />
      ))}
    </svg>
  );
}

const TYPE_DOT: Record<MonsterType, string> = {
  code: "bg-type-code",
  data: "bg-type-data",
  chart: "bg-type-chart",
  stats: "bg-type-stats",
  model: "bg-type-model",
  neural: "bg-type-neural",
  lingo: "bg-type-lingo",
  ops: "bg-type-ops",
};

export function TypeBadge({ type }: { type: MonsterType }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-pill bg-surface-2 px-2 py-0.5 text-xs font-medium text-text">
      <span className={cx("size-2 rounded-pill", TYPE_DOT[type])} aria-hidden />
      {TYPE_LABEL[type]}
    </span>
  );
}
