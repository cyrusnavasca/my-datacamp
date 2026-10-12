// XP rules (ours, modelled on the original's behaviour). Pure, safe for client code.
//   hint     -30% of the exercise's XP
//   solution -70%
//   each wrong multiple-choice / drag answer -10%, at most -50%
// Never below zero. XP is awarded once, the first time an exercise is completed.

export const PENALTY = { hint: 0.3, solution: 0.7, wrong: 0.1, wrongMax: 0.5 } as const;

export type PenaltyState = { hint_used: number; solution_used: number; wrong_count: number };

export function computeXp(base: number, s: PenaltyState) {
  const penalty =
    (s.hint_used ? PENALTY.hint : 0) +
    (s.solution_used ? PENALTY.solution : 0) +
    Math.min(PENALTY.wrongMax, s.wrong_count * PENALTY.wrong);
  return Math.max(0, Math.round(base * (1 - penalty)));
}
