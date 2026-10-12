"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Markdown } from "@/components/Markdown";
import { Button } from "@/components/ui";
import type { PublicExercise } from "@/lib/exercises";
import { api } from "../api";
import type { ViewApi } from "../Player";

type Video = Extract<PublicExercise, { type: "video" }>;

/** Lesson intro as markdown slides (slides separated by a line with just ---). */
export function VideoView({ exercise: e, view, onContinue }: { exercise: Video; view: ViewApi; onContinue: () => void }) {
  const slides = e.slides.split(/\n-{3,}\s*\n/).map((s) => s.trim()).filter(Boolean);
  const [i, setI] = useState(0);
  const [busy, setBusy] = useState(false);
  const last = i === slides.length - 1;

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if ((ev.target as HTMLElement).closest("input, textarea, [contenteditable]")) return;
      if (ev.key === "ArrowRight") setI((x) => Math.min(slides.length - 1, x + 1));
      if (ev.key === "ArrowLeft") setI((x) => Math.max(0, x - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [slides.length]);

  const finish = async () => {
    if (view.done) return onContinue();
    setBusy(true);
    try {
      view.onResult(await api.submit(view.exerciseKey, {}));
    } catch (err) {
      view.onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-surface">
      <div className="mx-auto flex min-h-full max-w-3xl flex-col gap-4 p-5 py-8">
        <p className="text-sm text-text-muted">Lesson · {e.title}</p>
        <article
          className="flex min-h-[50dvh] flex-1 flex-col justify-center rounded-lg border border-border bg-bg p-8 sm:p-12"
          aria-roledescription="slide"
          aria-label={`Slide ${i + 1} of ${slides.length}`}
        >
          <Markdown className="text-base sm:text-lg">{slides[i] ?? ""}</Markdown>
        </article>
        <div className="flex items-center justify-between gap-3">
          <Button variant="secondary" onClick={() => setI(i - 1)} disabled={i === 0} aria-label="Previous slide">
            <ChevronLeft className="size-4" aria-hidden />
          </Button>
          <span className="text-sm text-text-muted tabular-nums" aria-live="polite">
            {i + 1} / {slides.length}
          </span>
          {last ? (
            view.done && !view.feedback ? (
              <Button onClick={onContinue}>Continue</Button>
            ) : !view.feedback ? (
              <Button onClick={finish} loading={busy}>
                Got it (+{e.xp} XP)
              </Button>
            ) : (
              <span />
            )
          ) : (
            <Button onClick={() => setI(i + 1)} aria-label="Next slide">
              <ChevronRight className="size-4" aria-hidden />
            </Button>
          )}
        </div>
        {view.feedback}
      </div>
    </div>
  );
}
