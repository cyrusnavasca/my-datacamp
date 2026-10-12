"use client";

import { useCallback, useRef, useState } from "react";
import { Play, RotateCcw, Send } from "lucide-react";
import { Button } from "@/components/ui";
import { api, type RunResult } from "../api";
import { CodeEditor } from "../CodeEditor";
import { Console } from "../Console";
import type { ViewApi } from "../Player";

/** Editor + toolbar + console. Used by coding, sequential and mc-with-console. */
export function CodePane({
  view,
  code,
  setCode,
  sampleCode,
  step,
  onSubmit,
  submitLabel = "Submit answer",
  readOnly,
}: {
  view: ViewApi;
  code: string;
  setCode: (c: string) => void;
  sampleCode: string;
  step?: number;
  /** omit for a console-only pane (mc with console) */
  onSubmit?: (code: string) => Promise<RunResult | undefined>;
  submitLabel?: string;
  readOnly?: boolean;
}) {
  const [result, setResult] = useState<RunResult | null>(null);
  const [busy, setBusy] = useState<"run" | "submit" | null>(null);
  const codeRef = useRef(code);
  codeRef.current = code;

  const run = useCallback(async () => {
    if (busy) return;
    setBusy("run");
    view.clearFeedback();
    try {
      setResult(await api.run(view.exerciseKey, codeRef.current, step));
    } catch (e) {
      view.onError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }, [busy, view, step]);

  const submit = useCallback(async () => {
    if (busy || !onSubmit) return;
    setBusy("submit");
    view.clearFeedback();
    try {
      const out = await onSubmit(codeRef.current);
      if (out) setResult(out);
    } catch (e) {
      view.onError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }, [busy, onSubmit, view]);

  return (
    <>
      <div className="flex shrink-0 items-center gap-2 border-b border-code-surface px-3 py-2">
        <span className="font-mono text-xs text-code-muted">script.py</span>
        <div className="ml-auto flex gap-2">
          <button
            className="inline-flex h-8 items-center rounded-md px-2 text-code-muted hover:bg-code-surface hover:text-code-text"
            onClick={() => setCode(sampleCode)}
            aria-label="Reset code to the starting point"
            title="Reset code"
          >
            <RotateCcw className="size-4" aria-hidden />
          </button>
          <Button variant="secondary" size="sm" onClick={run} loading={busy === "run"} title="Run code (Ctrl/Cmd+Enter)">
            <Play className="size-4" aria-hidden /> Run
          </Button>
          {onSubmit && (
            <Button size="sm" onClick={submit} loading={busy === "submit"} disabled={readOnly} title="Submit (Ctrl/Cmd+Shift+Enter)">
              <Send className="size-4" aria-hidden /> {submitLabel}
            </Button>
          )}
        </div>
      </div>
      <div className="min-h-[220px] flex-[3] overflow-hidden">
        <CodeEditor value={code} onChange={setCode} onRun={run} onSubmit={onSubmit ? submit : undefined} readOnly={readOnly} label="Code editor" />
      </div>
      <div className="min-h-[160px] flex-[2] border-t border-code-surface">
        <Console result={result} running={busy !== null} />
      </div>
    </>
  );
}
