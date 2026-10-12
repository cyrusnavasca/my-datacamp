"use client";

import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { Button, cx } from "@/components/ui";
import { Markdown } from "@/components/Markdown";
import type { MonsterEvent } from "@/lib/monsters";
import { getLine } from "@/lib/monsters/roster";

export type FeedbackState = { kind: "success" | "incorrect" | "error" | "step"; text: string; xp?: number; monster?: MonsterEvent };

function PartnerLine({ p }: { p: NonNullable<MonsterEvent["partner"]> }) {
  const name = getLine(p.id)?.forms[p.to.form].name ?? p.id;
  return (
    <p className="text-text">
      {name} +{p.gained} XP{p.bonus && " (type bonus)"}
      {p.to.level > p.from.level && <span className="font-semibold">. Level up! Lv {p.to.level}</span>}
    </p>
  );
}

export function Feedback({ state, onContinue, isLast }: { state: FeedbackState; onContinue: () => void; isLast: boolean }) {
  const success = state.kind === "success";
  const Icon = success || state.kind === "step" ? CheckCircle2 : state.kind === "error" ? AlertTriangle : XCircle;
  return (
    <div
      role={success || state.kind === "step" ? "status" : "alert"}
      className={cx(
        "flex flex-col gap-3 rounded-md p-4 text-sm sm:flex-row sm:items-start",
        success || state.kind === "step" ? "bg-success-soft text-success" : "bg-danger-soft text-danger",
      )}
    >
      <Icon className="mt-0.5 size-5 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1">
        {success && state.xp !== undefined && (
          <p className="font-semibold">{state.xp > 0 ? `Correct! +${state.xp} XP` : "Correct!"}</p>
        )}
        {success && state.monster?.partner && <PartnerLine p={state.monster.partner} />}
        {!(success && state.text === "Correct!") && <Markdown className="text-text [&_pre]:text-xs">{state.text}</Markdown>}
      </div>
      {success && (
        <Button onClick={onContinue} autoFocus className="shrink-0">
          {isLast ? "Finish course" : "Continue"}
        </Button>
      )}
    </div>
  );
}
