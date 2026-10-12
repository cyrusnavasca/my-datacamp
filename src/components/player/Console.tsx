"use client";

import { useEffect, useState } from "react";
import { cx } from "@/components/ui";
import type { RunResult } from "./api";

export function Console({ result, running }: { result: RunResult | null; running: boolean }) {
  const images = result?.images ?? [];
  const [tab, setTab] = useState<"output" | "plots">("output");
  useEffect(() => setTab(images.length > 0 ? "plots" : "output"), [result]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex h-full flex-col bg-code-bg text-code-text">
      <div role="tablist" aria-label="Console" className="flex shrink-0 gap-1 border-b border-code-surface px-2 text-xs">
        <button role="tab" aria-selected={tab === "output"} onClick={() => setTab("output")} className={cx("px-3 py-2", tab === "output" ? "border-b-2 border-accent text-code-text" : "text-code-muted")}>
          Output
        </button>
        {images.length > 0 && (
          <button role="tab" aria-selected={tab === "plots"} onClick={() => setTab("plots")} className={cx("px-3 py-2", tab === "plots" ? "border-b-2 border-accent text-code-text" : "text-code-muted")}>
            Plots ({images.length})
          </button>
        )}
        {result && !running && <span className="ml-auto self-center text-code-muted tabular-nums">{(result.ms / 1000).toFixed(1)}s</span>}
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-3 font-mono text-sm" aria-live="polite">
        {running ? (
          <p className="text-code-muted">Running…</p>
        ) : !result ? (
          <p className="text-code-muted">Run your code to see its output here. (Ctrl/Cmd + Enter)</p>
        ) : tab === "plots" ? (
          <div className="flex flex-col gap-3">
            {images.map((src, i) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={i} src={`data:image/png;base64,${src}`} alt={`Plot ${i + 1} from your code`} className="max-w-full rounded-md bg-white" />
            ))}
          </div>
        ) : (
          <>
            {result.stdout && <pre className="whitespace-pre-wrap">{result.stdout}</pre>}
            {result.error && <pre className="mt-2 whitespace-pre-wrap text-code-error">{result.error}</pre>}
            {!result.stdout && !result.error && <p className="text-code-muted">Ran without printing anything.</p>}
          </>
        )}
      </div>
    </div>
  );
}
