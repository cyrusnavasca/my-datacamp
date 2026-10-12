"use client";

import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Markdown } from "@/components/Markdown";
import { cx } from "@/components/ui";
import type { PublicExercise } from "@/lib/exercises";
import { api } from "../api";
import { HintControls } from "../HintControls";
import type { ViewApi } from "../Player";
import { CodePane } from "./CodePane";
import { ExerciseTitle, InstructionsBox, Split } from "./Split";

type Sequential = Extract<PublicExercise, { type: "sequential" }>;

/** Several steps on one shared context; each step's setup is the solutions of the steps before it. */
export function SequentialView({ exercise: e, view }: { exercise: Sequential; view: ViewApi }) {
  const total = e.steps.length;
  const [stepsDone, setStepsDone] = useState(view.done ? total : view.initial.stepsDone);
  const [step, setStep] = useState(Math.min(stepsDone, total - 1));
  const [codes, setCodes] = useState(() => e.steps.map((s) => s.sample_code));
  // Hint and answer are per step in content, but penalties apply once per exercise.
  const [stepHint, setStepHint] = useState<Record<number, string>>(() => (view.hint ? { [step]: view.hint } : {}));
  const s = e.steps[step];
  const setCode = (c: string) => setCodes((all) => all.map((x, i) => (i === step ? c : x)));

  return (
    <Split
      left={
        <>
          <ExerciseTitle title={e.title} kind={`Multi-step exercise · step ${step + 1} of ${total}`} />
          <Markdown>{e.context}</Markdown>
          <ol className="flex gap-2" aria-label="Steps">
            {e.steps.map((_, i) => (
              <li key={i}>
                <button
                  onClick={() => setStep(i)}
                  disabled={i > stepsDone}
                  aria-current={i === step ? "step" : undefined}
                  className={cx(
                    "flex h-8 items-center gap-1 rounded-pill px-3 text-xs font-semibold disabled:opacity-40",
                    i === step ? "bg-accent text-on-accent" : i < stepsDone ? "bg-success-soft text-success" : "bg-surface-2",
                  )}
                >
                  {i < stepsDone && <CheckCircle2 className="size-3.5" aria-hidden />} Step {i + 1}
                </button>
              </li>
            ))}
          </ol>
          <InstructionsBox xp={view.xpNow} items={s.instructions} done={view.done} title={`Step ${step + 1}`} />
          <HintControls
            baseXp={e.xp}
            hint={stepHint[step] ?? null}
            hintUsed={step in stepHint}
            solutionUsed={false}
            done={view.done}
            hintFree={view.hintUsed}
            solutionFree={view.solutionUsed}
            onHint={async () => {
              const h = await view.takeHint(step);
              setStepHint((all) => ({ ...all, [step]: h }));
            }}
            onSolution={async () => {
              const r = await view.revealSolution(step);
              if (r.code) setCode(r.code);
            }}
          />
          {view.feedback}
          {step < stepsDone && step + 1 < total && !view.done && (
            <button className="text-sm font-semibold text-accent-text underline" onClick={() => (view.clearFeedback(), setStep(step + 1))}>
              Go to step {step + 2}
            </button>
          )}
        </>
      }
      right={
        <CodePane
          key={step}
          view={view}
          step={step}
          code={codes[step]}
          setCode={setCode}
          sampleCode={s.sample_code}
          onSubmit={async (c) => {
            const r = await api.submit(view.exerciseKey, { code: c, step });
            view.onResult(r);
            if (r.correct && r.stepsDone !== undefined) {
              setStepsDone(r.stepsDone);
              if (r.stepsDone < total) setStep(r.stepsDone);
            }
            return r.output;
          }}
        />
      }
    />
  );
}
