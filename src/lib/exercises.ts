import { getExerciseByKey } from "./content/loader";
import { exerciseXp, type Exercise } from "./content/schema";
import * as monsters from "./monsters";
import * as progress from "./progress";
import { runPython, type RunResult } from "./runner";

// Server-side exercise logic. The client only ever sees PublicExercise:
// no solutions, no tests, no answer keys.

export type PublicExercise =
  | { type: "video"; id: string; title: string; xp: number; slides: string }
  | {
      type: "coding";
      id: string;
      title: string;
      xp: number;
      context: string;
      instructions: string[];
      sample_code: string;
    }
  | {
      type: "mc";
      id: string;
      title: string;
      xp: number;
      question: string;
      context?: string;
      options: string[];
      hasConsole: boolean;
    }
  | { type: "order"; id: string; title: string; xp: number; prompt: string; items: string[] }
  | { type: "parsons"; id: string; title: string; xp: number; prompt: string; lines: string[] }
  | { type: "classify"; id: string; title: string; xp: number; prompt: string; zones: string[]; items: string[] }
  | {
      type: "sequential";
      id: string;
      title: string;
      xp: number;
      context: string;
      steps: { instructions: string[]; sample_code: string }[];
    };

/** Deterministic shuffle so a reload shows the same order. Never returns the solved order. */
export function seededShuffle<T>(items: T[], seedText: string): T[] {
  let h = 2166136261;
  for (const c of seedText) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  const rand = () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
  const a = [...items];
  for (let attempt = 0; attempt < 5; attempt++) {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    if (a.some((x, i) => x !== items[i])) return a;
  }
  return [...a.slice(1), a[0]];
}

export function toPublic(key: string, e: Exercise): PublicExercise {
  const common = { id: e.id, title: e.title, xp: exerciseXp(e) };
  switch (e.type) {
    case "video":
      return { ...common, type: "video", slides: e.slides };
    case "coding":
      return { ...common, type: "coding", context: e.context, instructions: e.instructions, sample_code: e.sample_code };
    case "mc":
      return {
        ...common,
        type: "mc",
        question: e.question,
        context: e.context,
        options: e.options.map((o) => o.text),
        hasConsole: Boolean(e.pre_code?.trim()),
      };
    case "order":
      return { ...common, type: "order", prompt: e.prompt, items: seededShuffle(e.items, key) };
    case "parsons":
      return { ...common, type: "parsons", prompt: e.prompt, lines: seededShuffle(e.lines.map((l) => l.trim()), key) };
    case "classify":
      return { ...common, type: "classify", prompt: e.prompt, zones: e.zones, items: seededShuffle(e.items.map((i) => i.text), key) };
    case "sequential":
      return {
        ...common,
        type: "sequential",
        context: e.context,
        steps: e.steps.map((s) => ({ instructions: s.instructions, sample_code: s.sample_code })),
      };
  }
}

/** Setup code for a run: the exercise's pre_code plus, for sequential step k, the solutions of steps before it. */
function setupFor(e: Exercise, step = 0): string {
  if (e.type === "coding") return e.pre_code;
  if (e.type === "mc") return e.pre_code ?? "";
  if (e.type === "sequential") return [e.pre_code, ...e.steps.slice(0, step).map((s) => s.solution)].join("\n");
  return "";
}

function timeoutOf(e: Exercise) {
  return "timeout" in e ? e.timeout : undefined;
}

export class ExerciseNotFound extends Error {}

function load(key: string) {
  const found = getExerciseByKey(key);
  if (!found) throw new ExerciseNotFound(key);
  return found.exercise;
}

export async function run(key: string, code: string, step = 0): Promise<RunResult> {
  const e = load(key);
  if (e.type !== "coding" && e.type !== "sequential" && e.type !== "mc") throw new Error(`cannot run code for ${e.type}`);
  progress.saveCode(key, code);
  const res = await runPython({ mode: "run", pre_code: setupFor(e, step), code, timeoutSec: timeoutOf(e) });
  progress.logAttempt(key, "run", code, null);
  return res;
}

export type SubmitResult = {
  correct: boolean;
  feedback: string;
  xpEarned: number;
  /** partner XP, level-ups, evolutions and catches this answer caused */
  monster?: monsters.MonsterEvent;
  /** for sequential: steps completed so far */
  stepsDone?: number;
  /** for order/parsons: positions the learner got wrong */
  wrong?: number[];
  /** for classify: item texts in the wrong group */
  wrongItems?: string[];
  output?: RunResult;
  successMsg?: string;
};

export type Answer = number | string[] | Record<string, string>;

export async function submit(key: string, input: { code?: string; answer?: Answer; step?: number }): Promise<SubmitResult> {
  const e = load(key);
  const base = exerciseXp(e);
  const done = (msg?: string): SubmitResult => {
    const firstTime = !progress.getProgress(key);
    const xpEarned = progress.completeExercise(key, base);
    const monster = firstTime ? monsters.onExerciseComplete(key, xpEarned) : undefined;
    return { correct: true, feedback: "", xpEarned, monster, successMsg: msg };
  };
  const wrong = (feedback: string, extra: Partial<SubmitResult> = {}): SubmitResult => {
    progress.markWrong(key);
    return { correct: false, feedback, xpEarned: 0, ...extra };
  };

  switch (e.type) {
    case "video":
      return done();

    case "coding": {
      const code = input.code ?? "";
      progress.saveCode(key, code);
      const out = await runPython({ mode: "submit", pre_code: e.pre_code, code, solution: e.solution, tests: e.tests, timeoutSec: e.timeout });
      progress.logAttempt(key, "submit", code, Boolean(out.correct), out.feedback);
      if (!out.correct) return { correct: false, feedback: out.feedback ?? "Not quite.", xpEarned: 0, output: out };
      return { ...done(e.success_msg), output: out };
    }

    case "sequential": {
      const step = input.step ?? 0;
      const s = e.steps[step];
      if (!s) throw new Error(`no step ${step}`);
      const code = input.code ?? "";
      const out = await runPython({ mode: "submit", pre_code: setupFor(e, step), code, solution: s.solution, tests: s.tests, timeoutSec: e.timeout });
      progress.logAttempt(key, "submit", JSON.stringify({ step, code }), Boolean(out.correct), out.feedback);
      if (!out.correct) return { correct: false, feedback: out.feedback ?? "Not quite.", xpEarned: 0, output: out };
      const stepsDone = Math.max(progress.getState(key).steps_done, step + 1);
      progress.setStepsDone(key, stepsDone);
      if (stepsDone < e.steps.length) return { correct: true, feedback: "", xpEarned: 0, stepsDone, output: out };
      return { ...done(e.success_msg), stepsDone, output: out };
    }

    case "mc": {
      const i = Number(input.answer);
      const opt = e.options[i];
      if (!opt) throw new Error("answer out of range");
      progress.logAttempt(key, "submit", String(i), opt.correct, opt.feedback);
      return opt.correct ? { ...done(), feedback: opt.feedback } : wrong(opt.feedback);
    }

    case "order":
    case "parsons": {
      const expected = e.type === "order" ? e.items : e.lines.map((l) => l.trimEnd());
      const given = (Array.isArray(input.answer) ? input.answer : []).map((l) => l.trimEnd());
      const bad = expected.flatMap((x, i) => (given[i] === x ? [] : [i]));
      progress.logAttempt(key, "submit", JSON.stringify(given), bad.length === 0);
      if (bad.length === 0) return done();
      const n = bad.length;
      const what =
        e.type === "parsons"
          ? `${n} ${n === 1 ? "line is" : "lines are"} in the wrong place or wrongly indented.`
          : `${n} ${n === 1 ? "item is" : "items are"} in the wrong place.`;
      return wrong(what, { wrong: bad });
    }

    case "classify": {
      const given = (input.answer ?? {}) as Record<string, string>;
      const bad = e.items.flatMap((it, i) => (given[it.text] === it.zone ? [] : [i]));
      progress.logAttempt(key, "submit", JSON.stringify(given), bad.length === 0);
      if (bad.length === 0) return done();
      // The client shuffled the items, so report them by text, not index.
      return wrong(`${bad.length} of ${e.items.length} ${e.items.length === 1 ? "item is" : "items are"} in the wrong group.`, {
        wrongItems: bad.map((i) => e.items[i].text),
      });
    }
  }
}

export function hint(key: string, step = 0): string {
  const e = load(key);
  if (e.type === "video") return "";
  progress.markHint(key);
  return e.type === "sequential" ? (e.steps[step]?.hint ?? "") : e.hint;
}

export type Reveal = { code?: string; answer?: Answer };

export function solution(key: string, step = 0): Reveal {
  const e = load(key);
  progress.markSolution(key);
  switch (e.type) {
    case "coding":
      return { code: e.solution };
    case "sequential":
      return { code: e.steps[step]?.solution };
    case "mc":
      return { answer: e.options.findIndex((o) => o.correct) };
    case "order":
      return { answer: e.items };
    case "parsons":
      return { answer: e.lines };
    case "classify":
      return { answer: Object.fromEntries(e.items.map((i) => [i.text, i.zone])) };
    case "video":
      return {};
  }
}
