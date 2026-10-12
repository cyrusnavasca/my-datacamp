import { beforeEach, describe, expect, it } from "vitest";
import { flattenCourse, getCourse, getExerciseByKey, listTracks } from "@/lib/content/loader";
import { Exercise, LessonFile } from "@/lib/content/schema";
import { resetDbForTests } from "@/lib/db";
import { hint, seededShuffle, solution, submit, toPublic } from "@/lib/exercises";
import { completedSet, getState, streak, totalXp } from "@/lib/progress";
import { computeXp } from "@/lib/xp";

const K = (e: string) => `demo/ch1/l1/${e}`;

beforeEach(() => resetDbForTests());

describe("xp", () => {
  it("applies hint, solution and wrong-answer penalties", () => {
    expect(computeXp(100, { hint_used: 0, solution_used: 0, wrong_count: 0 })).toBe(100);
    expect(computeXp(100, { hint_used: 1, solution_used: 0, wrong_count: 0 })).toBe(70);
    expect(computeXp(100, { hint_used: 1, solution_used: 1, wrong_count: 0 })).toBe(0);
    expect(computeXp(50, { hint_used: 0, solution_used: 0, wrong_count: 2 })).toBe(40);
    expect(computeXp(50, { hint_used: 0, solution_used: 0, wrong_count: 99 })).toBe(25);
    expect(computeXp(100, { hint_used: 1, solution_used: 1, wrong_count: 3 })).toBe(0);
  });
});

describe("schema", () => {
  it("rejects mc without exactly one correct option", () => {
    const r = Exercise.safeParse({
      id: "q", type: "mc", title: "t", question: "q", hint: "h",
      options: [{ text: "a", feedback: "f" }, { text: "b", feedback: "f" }],
    });
    expect(r.success).toBe(false);
  });
  it("rejects classify items with unknown zones", () => {
    const r = Exercise.safeParse({ id: "c", type: "classify", title: "t", prompt: "p", hint: "h", zones: ["x", "y"], items: [{ text: "a", zone: "z" }, { text: "b", zone: "x" }] });
    expect(r.success).toBe(false);
  });
  it("rejects bad ids and empty lessons", () => {
    expect(LessonFile.safeParse({ title: "t", exercises: [] }).success).toBe(false);
    expect(Exercise.safeParse({ id: "Bad Id", type: "video", title: "t", slides: "s" }).success).toBe(false);
  });
});

describe("loader", () => {
  it("loads tracks, courses and marks missing lesson files", () => {
    expect(listTracks().map((t) => t.slug)).toEqual(["demo-track"]);
    const c = getCourse("demo")!;
    expect(c.exerciseCount).toBe(6);
    expect(c.chapters[1].lessons[0].exercises).toBeNull();
    expect(flattenCourse(c).map((e) => e.id)).toEqual(["v", "c", "m", "o", "k", "s"]);
    expect(getExerciseByKey("demo/ch1/l1/nope")).toBeNull();
  });
});

describe("public exercises", () => {
  it("never leaks answers", () => {
    const c = getExerciseByKey(K("c"))!.exercise;
    const pub = JSON.stringify(toPublic(K("c"), c));
    expect(pub).not.toContain("read_csv");
    const m = JSON.stringify(toPublic(K("m"), getExerciseByKey(K("m"))!.exercise));
    expect(m).not.toContain("correct");
    expect(m).not.toContain("feedback");
  });
  it("shuffles deterministically and never returns the solved order", () => {
    const items = ["a", "b", "c", "d"];
    expect(seededShuffle(items, "x")).toEqual(seededShuffle(items, "x"));
    for (const seed of ["a", "b", "c", "d", "e", "f"]) expect(seededShuffle(items, seed)).not.toEqual(items);
    expect(seededShuffle(["a", "b"], "k")).toEqual(["b", "a"]);
  });
});

describe("submit", () => {
  it("awards XP once, with penalties, and records the day", async () => {
    expect((await submit(K("m"), { answer: 0 })).correct).toBe(false);
    hint(K("m"));
    const r = await submit(K("m"), { answer: 1 });
    expect(r).toMatchObject({ correct: true, xpEarned: 30 }); // 50 - 30% hint - 10% wrong
    expect((await submit(K("m"), { answer: 1 })).xpEarned).toBe(0);
    expect(totalXp()).toBe(30);
    expect(streak()).toBe(1);
    expect(completedSet("demo").has(K("m"))).toBe(true);
  });

  it("checks order and classify answers", async () => {
    expect(await submit(K("o"), { answer: ["two", "one", "three"] })).toMatchObject({ correct: false, wrong: [0, 1] });
    expect((await submit(K("o"), { answer: ["one", "two", "three"] })).correct).toBe(true);
    expect(await submit(K("k"), { answer: { a: "y", b: "y" } })).toMatchObject({ correct: false, wrongItems: ["a"] });
    expect((await submit(K("k"), { answer: { a: "x", b: "y" } })).correct).toBe(true);
  });

  it("solution reveal marks the penalty and returns the answer", () => {
    expect(solution(K("o"))).toEqual({ answer: ["one", "two", "three"] });
    expect(getState(K("o")).solution_used).toBe(1);
  });

  it("runs coding exercises with datasets", async () => {
    expect((await submit(K("c"), { code: "df = ____" })).feedback).toMatch(/blanks/);
    const r = await submit(K("c"), { code: "df = pd.read_csv('tiny.csv')" });
    expect(r.correct).toBe(true);
    expect(r.xpEarned).toBe(100);
  });

  it("completes sequential exercises step by step", async () => {
    const s1 = await submit(K("s"), { code: "a = 1", step: 0 });
    expect(s1).toMatchObject({ correct: true, stepsDone: 1, xpEarned: 0 });
    const s2 = await submit(K("s"), { code: "b = a + 1", step: 1 });
    expect(s2).toMatchObject({ correct: true, stepsDone: 2, xpEarned: 100 });
  });

  it("video completes on submit", async () => {
    expect(await submit(K("v"), {})).toMatchObject({ correct: true, xpEarned: 50 });
  });
});
