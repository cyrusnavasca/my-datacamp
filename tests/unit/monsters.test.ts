import fs from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { db, resetDbForTests } from "@/lib/db";
import { submit } from "@/lib/exercises";
import { MonsterError, choosePartner, getOwned, getPartner, ownedMonsters, starterSlots } from "@/lib/monsters";
import { CATCH_LEVEL, formFor, levelFor, levelProgress, nextEvolution, xpForLevel } from "@/lib/monsters/level";
import { ROSTER } from "@/lib/monsters/roster";
import { drawSprite } from "@/lib/monsters/sprite";
import { resetProgress } from "@/lib/progress";

// The fixture course "demo" has no monster in the real roster; give it a Code one.
vi.mock("@/lib/monsters/roster", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/monsters/roster")>();
  const demo = { ...real.ROSTER.find((l) => l.id === "loopip")!, id: "demomon", course: "demo" };
  const ROSTER = [...real.ROSTER, demo];
  return {
    ...real,
    ROSTER,
    getLine: (id: string) => ROSTER.find((l) => l.id === id),
    lineForCourse: (c: string) => ROSTER.find((l) => l.course === c),
  };
});

const K = (e: string) => `demo/ch1/l1/${e}`;

/** Marks exercises done without running them (coding ones need Python). */
function markDone(...ids: string[]) {
  const t = new Date().toISOString();
  for (const id of ids)
    db()
      .prepare("insert into exercise_progress (exercise_id, course_slug, xp_earned, completed_at, updated_at) values (?, 'demo', 0, ?, ?)")
      .run(K(id), t, t);
}

const setXp = (id: string, xp: number) => db().prepare("update monsters set xp = ? where line_id = ?").run(xp, id);

beforeEach(() => resetDbForTests());

describe("levels", () => {
  it("follows the curve, evolves at 16 and 32, caps at 50", () => {
    expect(levelFor(0)).toBe(1);
    expect(xpForLevel(16)).toBe(4500);
    expect(levelFor(4499)).toBe(15);
    expect(levelFor(4500)).toBe(16);
    expect(levelFor(10_000_000)).toBe(50);
    expect([formFor(15), formFor(16), formFor(31), formFor(32)]).toEqual([0, 1, 1, 2]);
    expect(levelProgress(xpForLevel(3) + 10)).toEqual({ level: 3, into: 10, span: xpForLevel(4) - xpForLevel(3) });
    expect([nextEvolution(1), nextEvolution(16), nextEvolution(32)]).toEqual([16, 32, null]);
  });
});

describe("roster", () => {
  it("has one monster per real course, three starters, and unique names", () => {
    const courses = fs.readdirSync(path.join(process.cwd(), "content", "courses")).sort();
    const real = ROSTER.filter((l) => l.course !== "demo");
    expect(real.flatMap((l) => (l.course ? [l.course] : [])).sort()).toEqual(courses);
    expect(real.filter((l) => l.starter)).toHaveLength(3);
    const names = real.flatMap((l) => l.forms.map((f) => f.name));
    expect(new Set(names).size).toBe(names.length);
  });
});

describe("sprites", () => {
  it("draws every form of every line inside the grid, with eyes", () => {
    for (const line of ROSTER)
      for (const form of [0, 1, 2]) {
        const g = drawSprite(line, form);
        expect(g.filter((v) => v !== 0).length, `${line.id}/${form}`).toBeGreaterThan(40);
        expect(g.includes(5), `${line.id}/${form} eye shine`).toBe(true);
      }
  });
  it("gets bigger as it evolves", () => {
    const filled = (f: number) => drawSprite(ROSTER[0], f).filter((v) => v !== 0).length;
    expect(filled(1)).toBeGreaterThan(filled(0));
    expect(filled(2)).toBeGreaterThan(filled(1));
  });
});

describe("partner", () => {
  it("first starter gets all XP earned so far, then earns from each exercise", async () => {
    expect((await submit(K("v"), {})).monster).toBeUndefined(); // no partner yet
    expect(choosePartner("tabbit").xp).toBe(50);
    expect(getPartner()?.line.id).toBe("tabbit");

    const r = await submit(K("o"), { answer: ["one", "two", "three"] });
    expect(r.monster?.partner).toMatchObject({ id: "tabbit", gained: 50, bonus: false, to: { xp: 100 } });
    expect((await submit(K("o"), { answer: ["one", "two", "three"] })).monster).toBeUndefined(); // already done
  });

  it("gives x1.5 XP when the partner's type matches the course monster", async () => {
    choosePartner("pybble"); // Code, like demomon
    const r = await submit(K("v"), {});
    expect(r.monster?.partner).toMatchObject({ gained: 75, bonus: true });
  });

  it("reports level-ups and evolutions", async () => {
    choosePartner("pybble");
    setXp("pybble", xpForLevel(16) - 10);
    const p = (await submit(K("v"), {})).monster!.partner!;
    expect(p.from).toMatchObject({ level: 15, form: 0 });
    expect(p.to).toMatchObject({ level: 16, form: 1 });
  });

  it("rejects monsters you don't have and starters without a slot", () => {
    expect(() => choosePartner("loopip")).toThrow(MonsterError);
    expect(() => choosePartner("nope")).toThrow(MonsterError);
    choosePartner("pybble");
    expect(() => choosePartner("tabbit")).toThrow("no starter slot open");
  });

  it("opens a starter slot for each monster in its final form", () => {
    choosePartner("pybble");
    expect(starterSlots().open).toBe(0);
    setXp("pybble", xpForLevel(32));
    expect(starterSlots().open).toBe(1);
    expect(choosePartner("tabbit").level).toBe(CATCH_LEVEL);
    expect(getPartner()?.line.id).toBe("tabbit");
    expect(choosePartner("pybble").level).toBe(32); // switching back is free
  });
});

describe("catching", () => {
  it("catches the course monster when a chapter is finished", async () => {
    markDone("v", "c", "o", "k", "s");
    const r = await submit(K("m"), { answer: 1 });
    expect(r.monster?.caught).toEqual([expect.objectContaining({ id: "demomon", level: CATCH_LEVEL })]);
    expect(getOwned("demomon")).not.toBeNull();
    expect(choosePartner("demomon").line.id).toBe("demomon");
  });

  it("does not catch on a partly finished chapter", async () => {
    markDone("v", "c");
    expect((await submit(K("m"), { answer: 1 })).monster).toBeUndefined();
  });

  it("full reset releases every monster", () => {
    choosePartner("plotl");
    resetProgress();
    expect(ownedMonsters()).toEqual([]);
    expect(getPartner()).toBeNull();
  });
});
