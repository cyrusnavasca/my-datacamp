import type { ReactNode } from "react";
import { Markdown } from "@/components/Markdown";

/** Left: reading pane. Right: work pane (dark). Stacks under 1024px. */
export function Split({ left, right }: { left: ReactNode; right: ReactNode }) {
  return (
    <div className="flex h-full flex-col overflow-y-auto lg:grid lg:grid-cols-[minmax(320px,38%)_1fr] lg:overflow-hidden">
      <section className="space-y-5 p-5 lg:overflow-y-auto">{left}</section>
      <section className="flex min-h-[70dvh] flex-col bg-code-bg lg:min-h-0">{right}</section>
    </div>
  );
}

export function ExerciseTitle({ title, kind }: { title: string; kind: string }) {
  return (
    <div>
      <p className="text-sm text-text-muted">{kind}</p>
      <h1 className="mt-1 text-lg break-words">{title}</h1>
    </div>
  );
}

export function InstructionsBox({ xp, items, done, title = "Instructions" }: { xp: number; items: string[]; done: boolean; title?: string }) {
  return (
    <div className="rounded-lg bg-surface p-4">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold">{title}</h2>
        <span className="text-xs text-text-muted tabular-nums">{done ? `${xp} XP earned` : `${xp} XP`}</span>
      </div>
      <ol className="list-decimal space-y-2 pl-5 text-sm">
        {items.map((i, n) => (
          <li key={n}>
            <Markdown>{i}</Markdown>
          </li>
        ))}
      </ol>
    </div>
  );
}
