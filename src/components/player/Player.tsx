"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowLeft, ChevronLeft, ChevronRight, Menu, Zap } from "lucide-react";
import { Button, ButtonLink, cx } from "@/components/ui";
import type { ExerciseType } from "@/lib/content/schema";
import type { PublicExercise } from "@/lib/exercises";
import type { MonsterEvent, MonsterView } from "@/lib/monsters";
import { getLine } from "@/lib/monsters/roster";
import { Sprite } from "@/components/monsters/Sprite";
import { computeXp } from "@/lib/xp";
import { api, type Reveal, type SubmitResult } from "./api";
import { Feedback, type FeedbackState } from "./Feedback";
import { MonsterDialog } from "./MonsterDialog";
import { Outline, type OutlineChapter } from "./Outline";
import { ClassifyView } from "./views/ClassifyView";
import { CodingView } from "./views/CodingView";
import { McView } from "./views/McView";
import { OrderView } from "./views/OrderView";
import { SequentialView } from "./views/SequentialView";
import { VideoView } from "./views/VideoView";

export type PlayerProps = {
  exerciseKey: string;
  exercise: PublicExercise;
  course: { slug: string; title: string };
  chapter: { id: string; title: string; n: number };
  lessonTitle: string;
  dots: { href: string; title: string; type: ExerciseType; done: boolean; current: boolean }[];
  position: { index: number; total: number };
  prevHref: string | null;
  nextHref: string | null;
  endsChapter: boolean;
  nextChapterTitle: string | null;
  chapterExercises: string[];
  completedKeys: string[];
  outline: OutlineChapter[];
  initial: {
    done: boolean;
    xpEarned: number | null;
    hintUsed: boolean;
    solutionUsed: boolean;
    wrongCount: number;
    stepsDone: number;
    lastCode: string | null;
    hint: string | null;
  };
  baseXp: number;
  totalXp: number;
  partner: MonsterView | null;
};

/** What every exercise view gets from the player. */
export type ViewApi = {
  exerciseKey: string;
  done: boolean;
  xpNow: number;
  hint: string | null;
  hintUsed: boolean;
  solutionUsed: boolean;
  takeHint: (step?: number) => Promise<string>;
  revealSolution: (step?: number) => Promise<Reveal>;
  /** Report a submit result; the player shows feedback and awards XP. */
  onResult: (r: SubmitResult) => void;
  /** Show an error (network, runner) in the feedback bar. */
  onError: (message: string) => void;
  clearFeedback: () => void;
  feedback: ReactNode;
  initial: PlayerProps["initial"];
};

export function Player(p: PlayerProps) {
  const router = useRouter();
  const [done, setDone] = useState(p.initial.done);
  const [hint, setHint] = useState(p.initial.hint);
  const [penalties, setPenalties] = useState({
    hint_used: Number(p.initial.hintUsed),
    solution_used: Number(p.initial.solutionUsed),
    wrong_count: p.initial.wrongCount,
  });
  const [xpTotal, setXpTotal] = useState(p.totalXp);
  const [xpGain, setXpGain] = useState<number | null>(null);
  const [partner, setPartner] = useState(p.partner);
  const [monsterEvent, setMonsterEvent] = useState<MonsterEvent | null>(null);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [outlineOpen, setOutlineOpen] = useState(false);
  const chapterDialog = useRef<HTMLDialogElement>(null);
  const [completed, setCompleted] = useState(() => new Set(p.completedKeys));

  // New exercise: reset transient UI (the component is reused across client navigations).
  useEffect(() => {
    setDone(p.initial.done);
    setHint(p.initial.hint);
    setPenalties({ hint_used: Number(p.initial.hintUsed), solution_used: Number(p.initial.solutionUsed), wrong_count: p.initial.wrongCount });
    setFeedback(null);
    setXpTotal(p.totalXp);
    setPartner(p.partner);
    setCompleted(new Set(p.completedKeys));
  }, [p.exerciseKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const xpNow = done && p.initial.xpEarned !== null ? p.initial.xpEarned : computeXp(p.baseXp, penalties);

  const goNext = useCallback(() => {
    const chapterDone = p.chapterExercises.every((k) => completed.has(k) || k === p.exerciseKey);
    if (p.endsChapter && chapterDone && p.nextHref) {
      chapterDialog.current?.showModal();
      return;
    }
    router.push(p.nextHref ?? `/courses/${p.course.slug}/complete`);
  }, [p, completed, router]);

  const onResult = useCallback(
    (r: SubmitResult) => {
      if (!r.correct) {
        setPenalties((s) => ({ ...s, wrong_count: s.wrong_count + 1 }));
        setFeedback({ kind: "incorrect", text: r.feedback || "Not quite. Try again." });
        return;
      }
      if (p.exercise.type === "sequential" && r.stepsDone !== undefined && r.stepsDone < p.exercise.steps.length) {
        setFeedback({ kind: "step", text: `Step ${r.stepsDone} of ${p.exercise.steps.length} done. On to the next one.` });
        return;
      }
      setDone(true);
      setCompleted((c) => new Set(c).add(p.exerciseKey));
      if (r.xpEarned > 0) {
        setXpTotal((x) => x + r.xpEarned);
        setXpGain(r.xpEarned);
        setTimeout(() => setXpGain(null), 800);
      }
      if (r.monster?.partner) setPartner(r.monster.partner.to);
      if (r.monster) setMonsterEvent(r.monster);
      setFeedback({ kind: "success", text: r.successMsg || r.feedback || "Correct!", xp: r.xpEarned, monster: r.monster });
    },
    [p.exercise, p.exerciseKey],
  );

  const view: ViewApi = {
    exerciseKey: p.exerciseKey,
    done,
    xpNow,
    hint,
    hintUsed: Boolean(penalties.hint_used),
    solutionUsed: Boolean(penalties.solution_used),
    takeHint: async (step) => {
      const r = await api.hint(p.exerciseKey, step);
      setHint(r.hint);
      setPenalties((s) => ({ ...s, hint_used: 1 }));
      return r.hint;
    },
    revealSolution: async (step) => {
      const r = await api.solution(p.exerciseKey, step);
      setPenalties((s) => ({ ...s, solution_used: 1 }));
      return r;
    },
    onResult,
    onError: (text) => setFeedback({ kind: "error", text }),
    clearFeedback: () => setFeedback(null),
    feedback: feedback && <Feedback state={feedback} onContinue={goNext} isLast={!p.nextHref} />,
    initial: p.initial,
  };

  const e = p.exercise;
  let body: ReactNode;
  switch (e.type) {
    case "video":
      body = <VideoView exercise={e} view={view} onContinue={goNext} />;
      break;
    case "coding":
      body = <CodingView key={p.exerciseKey} exercise={e} view={view} />;
      break;
    case "mc":
      body = <McView key={p.exerciseKey} exercise={e} view={view} />;
      break;
    case "order":
    case "parsons":
      body = <OrderView key={p.exerciseKey} exercise={e} view={view} />;
      break;
    case "classify":
      body = <ClassifyView key={p.exerciseKey} exercise={e} view={view} />;
      break;
    case "sequential":
      body = <SequentialView key={p.exerciseKey} exercise={e} view={view} />;
      break;
  }

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex h-[52px] shrink-0 items-center gap-3 border-b border-border bg-bg px-3">
        <Link href={`/courses/${p.course.slug}`} className="rounded-md p-2 hover:bg-surface-2" aria-label={`Back to ${p.course.title}`}>
          <ArrowLeft className="size-4" aria-hidden />
        </Link>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs text-text-muted">
            {p.course.title} · Chapter {p.chapter.n}
          </p>
          <p className="truncate text-sm font-semibold">{p.lessonTitle}</p>
        </div>
        <nav aria-label="Exercises in this lesson" className="hidden items-center gap-1.5 md:flex">
          {p.dots.map((d, i) => (
            <Link
              key={d.href}
              href={d.href}
              title={d.title}
              aria-label={`Exercise ${i + 1}: ${d.title}${d.done || (d.current && done) ? " (done)" : ""}`}
              aria-current={d.current ? "step" : undefined}
              className={cx(
                "size-2.5 rounded-pill",
                d.current ? "bg-accent ring-2 ring-accent/30" : d.done ? "bg-success" : "border border-border-input",
              )}
            />
          ))}
        </nav>
        <div className="relative">
          <span className="inline-flex items-center gap-1 text-sm font-semibold">
            <Zap className="size-4 text-xp" aria-hidden />
            <span className="tabular-nums">{xpTotal.toLocaleString()}</span>
            <span className="sr-only">total XP</span>
          </span>
          {xpGain !== null && (
            <span className="xp-float pointer-events-none absolute -top-1 right-0 text-xs font-bold text-xp" aria-live="polite">
              +{xpGain}
            </span>
          )}
        </div>
        {partner && (
          <span className="hidden items-center gap-1 text-sm sm:inline-flex" title={`Partner: ${getLine(partner.id)?.forms[partner.form].name}`}>
            <Sprite id={partner.id} form={partner.form} size={24} />
            <span className="tabular-nums">Lv {partner.level}</span>
            <span className="sr-only">partner level</span>
          </span>
        )}
        <div className="flex items-center">
          {p.prevHref && (
            <Link href={p.prevHref} className="rounded-md p-2 hover:bg-surface-2" aria-label="Previous exercise">
              <ChevronLeft className="size-4" aria-hidden />
            </Link>
          )}
          {p.nextHref && (
            <Link href={p.nextHref} className="rounded-md p-2 hover:bg-surface-2" aria-label="Skip to next exercise">
              <ChevronRight className="size-4" aria-hidden />
            </Link>
          )}
          <button className="rounded-md p-2 hover:bg-surface-2" onClick={() => setOutlineOpen(true)} aria-label="Course outline">
            <Menu className="size-4" aria-hidden />
          </button>
        </div>
      </header>

      <div className="min-h-0 flex-1">{body}</div>

      <Outline
        open={outlineOpen}
        onClose={() => setOutlineOpen(false)}
        chapters={p.outline}
        currentKey={p.exerciseKey}
        completed={completed}
        courseTitle={p.course.title}
      />

      <MonsterDialog event={monsterEvent} onClose={() => setMonsterEvent(null)} />

      <dialog ref={chapterDialog} className="m-auto w-[min(28rem,calc(100vw-2rem))] rounded-lg bg-bg p-6 text-center text-text shadow-pop backdrop:bg-text/40">
        <h2 className="text-lg">Chapter {p.chapter.n} complete</h2>
        <p className="mt-1 text-sm text-text-muted">{p.chapter.title}</p>
        {p.nextChapterTitle && (
          <p className="mt-4 text-sm">
            Up next: <span className="font-semibold">{p.nextChapterTitle}</span>
          </p>
        )}
        <div className="mt-6 flex justify-center gap-2">
          <Button variant="secondary" onClick={() => chapterDialog.current?.close()}>
            Stay here
          </Button>
          {p.nextHref && (
            <ButtonLink href={p.nextHref} autoFocus onClick={() => chapterDialog.current?.close()}>
              Next chapter
            </ButtonLink>
          )}
        </div>
      </dialog>
    </div>
  );
}
