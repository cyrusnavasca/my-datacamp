"use client";

import { useState } from "react";
import { Eye, Lightbulb } from "lucide-react";
import { Markdown } from "@/components/Markdown";
import { Button } from "@/components/ui";
import { PENALTY } from "@/lib/xp";

/** "Take hint" then "Show answer", each with its XP cost. */
export function HintControls({
  baseXp,
  hint,
  hintUsed,
  solutionUsed,
  done,
  onHint,
  onSolution,
  solutionLabel = "Show answer",
  hintFree,
  solutionFree,
}: {
  baseXp: number;
  hint: string | null;
  hintUsed: boolean;
  solutionUsed: boolean;
  done: boolean;
  onHint: () => Promise<unknown>;
  /** penalty already paid (e.g. an earlier step of a sequential exercise) */
  hintFree?: boolean;
  solutionFree?: boolean;
  onSolution: () => Promise<void>;
  solutionLabel?: string;
}) {
  const [busy, setBusy] = useState<"hint" | "solution" | null>(null);
  const wrap = (k: "hint" | "solution", fn: () => Promise<unknown>) => async () => {
    setBusy(k);
    try {
      await fn();
    } finally {
      setBusy(null);
    }
  };
  const cost = (p: number, free?: boolean) => (done || free ? "" : ` (-${Math.round(baseXp * p)} XP)`);

  return (
    <div className="space-y-3">
      {hint && (
        <div className="rounded-md bg-surface p-3 text-sm">
          <p className="mb-1 font-semibold">Hint</p>
          <Markdown>{hint}</Markdown>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {!hintUsed && (
          <Button variant="ghost" size="sm" onClick={wrap("hint", onHint)} loading={busy === "hint"}>
            <Lightbulb className="size-4" aria-hidden /> Take hint{cost(PENALTY.hint, hintFree)}
          </Button>
        )}
        {hintUsed && !solutionUsed && (
          <Button variant="ghost" size="sm" onClick={wrap("solution", onSolution)} loading={busy === "solution"}>
            <Eye className="size-4" aria-hidden /> {solutionLabel}
            {cost(PENALTY.solution, solutionFree)}
          </Button>
        )}
      </div>
    </div>
  );
}
