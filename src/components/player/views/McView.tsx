"use client";

import { useState } from "react";
import { Markdown } from "@/components/Markdown";
import { Button, cx } from "@/components/ui";
import type { PublicExercise } from "@/lib/exercises";
import { api } from "../api";
import { HintControls } from "../HintControls";
import type { ViewApi } from "../Player";
import { CodePane } from "./CodePane";
import { ExerciseTitle, Split } from "./Split";

type Mc = Extract<PublicExercise, { type: "mc" }>;

export function McView({ exercise: e, view }: { exercise: Mc; view: ViewApi }) {
  const [choice, setChoice] = useState<number | null>(null);
  const [wrong, setWrong] = useState<Set<number>>(new Set());
  const [correct, setCorrect] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [code, setCode] = useState("# Explore the data here, then answer on the left.\n");

  const submit = async () => {
    if (choice === null) return;
    setBusy(true);
    view.clearFeedback();
    try {
      const r = await api.submit(view.exerciseKey, { answer: choice });
      view.onResult(r);
      if (r.correct) setCorrect(choice);
      else setWrong((w) => new Set(w).add(choice));
    } catch (err) {
      view.onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const form = (
    <form
      onSubmit={(ev) => {
        ev.preventDefault();
        submit();
      }}
      className="space-y-5"
    >
      <fieldset>
        <legend className="mb-3 w-full">
          <Markdown>{e.question}</Markdown>
        </legend>
        <div className="space-y-2">
          {e.options.map((o, i) => (
            <label
              key={i}
              className={cx(
                "flex cursor-pointer items-start gap-3 rounded-md border p-3 text-sm",
                correct === i ? "border-success bg-success-soft" : wrong.has(i) ? "border-danger bg-danger-soft" : choice === i ? "border-accent bg-accent-soft" : "border-border hover:bg-surface",
              )}
            >
              <input type="radio" name="option" className="mt-1 accent-accent" checked={choice === i} onChange={() => setChoice(i)} disabled={correct !== null} />
              <Markdown className="min-w-0 flex-1">{o}</Markdown>
            </label>
          ))}
        </div>
      </fieldset>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={choice === null || correct !== null} loading={busy}>
          Submit answer
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
          if (typeof r.answer === "number") setChoice(r.answer);
        }}
      />
      {view.feedback}
    </form>
  );

  if (e.hasConsole)
    return (
      <Split
        left={
          <>
            <ExerciseTitle title={e.title} kind="Question" />
            {e.context && <Markdown>{e.context}</Markdown>}
            {form}
          </>
        }
        right={<CodePane view={view} code={code} setCode={setCode} sampleCode="" />}
      />
    );

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl space-y-5 p-5 py-10">
        <ExerciseTitle title={e.title} kind="Question" />
        {e.context && <Markdown>{e.context}</Markdown>}
        {form}
      </div>
    </div>
  );
}
