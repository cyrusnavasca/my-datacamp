"use client";

import { useState } from "react";
import { Markdown } from "@/components/Markdown";
import type { PublicExercise } from "@/lib/exercises";
import { api } from "../api";
import { HintControls } from "../HintControls";
import type { ViewApi } from "../Player";
import { CodePane } from "./CodePane";
import { ExerciseTitle, InstructionsBox, Split } from "./Split";

type Coding = Extract<PublicExercise, { type: "coding" }>;

export function CodingView({ exercise: e, view }: { exercise: Coding; view: ViewApi }) {
  const [code, setCode] = useState(view.initial.lastCode ?? e.sample_code);

  return (
    <Split
      left={
        <>
          <ExerciseTitle title={e.title} kind="Exercise" />
          <Markdown>{e.context}</Markdown>
          <InstructionsBox xp={view.xpNow} items={e.instructions} done={view.done} />
          <HintControls
            baseXp={e.xp}
            hint={view.hint}
            hintUsed={view.hintUsed}
            solutionUsed={view.solutionUsed}
            done={view.done}
            onHint={() => view.takeHint()}
            onSolution={async () => {
              const r = await view.revealSolution();
              if (r.code) setCode(r.code);
            }}
          />
          {view.feedback}
        </>
      }
      right={
        <CodePane
          view={view}
          code={code}
          setCode={setCode}
          sampleCode={e.sample_code}
          onSubmit={async (c) => {
            const r = await api.submit(view.exerciseKey, { code: c });
            view.onResult(r);
            return r.output;
          }}
        />
      }
    />
  );
}
