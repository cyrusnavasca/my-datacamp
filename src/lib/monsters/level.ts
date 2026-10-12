// Monster levelling rules. Pure, safe for client code.
//   Total XP to reach level L is 20 * (L - 1)^2, capped at level 50.
//   Forms change at level 16 and level 32.
//   The partner gets every XP point the learner earns, x1.5 when its type
//   matches the type of the course's own monster.
//   Caught monsters join at level 5.

export const MAX_LEVEL = 50;
export const EVOLVE_AT = [16, 32] as const;
export const CATCH_LEVEL = 5;
export const TYPE_BONUS = 1.5;

export function xpForLevel(level: number): number {
  const l = Math.min(Math.max(level, 1), MAX_LEVEL);
  return 20 * (l - 1) ** 2;
}

export function levelFor(xp: number): number {
  return Math.min(MAX_LEVEL, Math.floor(Math.sqrt(Math.max(0, xp) / 20)) + 1);
}

/** Form index 0, 1 or 2. */
export function formFor(level: number): 0 | 1 | 2 {
  return level >= EVOLVE_AT[1] ? 2 : level >= EVOLVE_AT[0] ? 1 : 0;
}

/** Progress through the current level, for an XP bar. */
export function levelProgress(xp: number): { level: number; into: number; span: number } {
  const level = levelFor(xp);
  if (level >= MAX_LEVEL) return { level, into: 1, span: 1 };
  const start = xpForLevel(level);
  return { level, into: xp - start, span: xpForLevel(level + 1) - start };
}

/** Level at which the next form arrives, or null for a final form. */
export function nextEvolution(level: number): number | null {
  return EVOLVE_AT.find((l) => l > level) ?? null;
}
