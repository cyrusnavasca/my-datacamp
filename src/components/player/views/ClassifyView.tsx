"use client";

import { useState } from "react";
import { Markdown } from "@/components/Markdown";
import { Button, cx } from "@/components/ui";
import type { PublicExercise } from "@/lib/exercises";
import { api } from "../api";
import { HintControls } from "../HintControls";
import type { ViewApi } from "../Player";
import { ExerciseTitle } from "./Split";

type Classify = Extract<PublicExercise, { type: "classify" }>;

/**
 * Sort items into groups. Each item gets a row of group buttons (works with
 * keyboard and touch).
 */
export function ClassifyView({ exercise: e, view }: { exercise: Classify; view: ViewApi }) {
  const [placed, setPlaced] = useState<Record<string, string>>({});
  const [wrong, setWrong] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const allPlaced = e.items.every((i) => placed[i]);

  const submit = async () => {
    setBusy(true);
    view.clearFeedback();
    try {
      const r = await api.submit(view.exerciseKey, { answer: placed });
      setWrong(new Set(r.wrongItems ?? []));
      view.onResult(r);
    } catch (err) {
      view.onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-5 p-5 py-10">
        <ExerciseTitle title={e.title} kind="Sort into groups" />
        <Markdown>{e.prompt}</Markdown>
        <ul className="divide-y divide-border border-y border-border">
          {e.items.map((item) => (
            <li key={item} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center">
              <span className={cx("min-w-0 flex-1 font-mono text-sm break-words", wrong.has(item) && "text-danger")}>
                {item}
                {wrong.has(item) && <span className="ml-2 font-sans text-xs">wrong group</span>}
              </span>
              <div role="radiogroup" aria-label={`Group for: ${item}`} className="flex flex-wrap gap-1">
                {e.zones.map((z) => (
                  <button
                    key={z}
                    role="radio"
                    aria-checked={placed[item] === z}
                    disabled={view.done}
                    onClick={() => {
                      setPlaced((p) => ({ ...p, [item]: z }));
                      setWrong((w) => {
                        const n = new Set(w);
                        n.delete(item);
                        return n;
                      });
                    }}
                    className={cx("rounded-pill border px-3 py-1 text-xs font-medium", placed[item] === z ? "border-accent bg-accent text-on-accent" : "border-border hover:bg-surface")}
                  >
                    {z}
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={submit} loading={busy} disabled={!allPlaced || view.done}>
            Check groups
          </Button>
          <span className="text-xs text-text-muted tabular-nums">{view.done ? `${view.xpNow} XP earned` : `${view.xpNow} XP`}</span>
        </div>
        <HintControls
          baseXp={e.xp}
          hint={view.hint}
          hintUsed={view.hintUsed}
          solutionUsed={view.solutionUsed}
          done={view.done}
          onHint={() => view.takeHint()}
          onSolution={async () => {
            const r = await view.revealSolution();
            if (r.answer && typeof r.answer === "object" && !Array.isArray(r.answer)) setPlaced(r.answer);
            setWrong(new Set());
          }}
        />
        {view.feedback}
      </div>
    </div>
  );
}
