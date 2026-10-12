import { LESSON, expect, resetProgress, setCode, test } from "./fixtures";

test.beforeEach(async ({ page }) => resetProgress(page));

test("F06-H1/E1 finish the lesson: slides, sequential, course complete, outline ticks", async ({ page, request }) => {
  // Complete the middle exercises through the API; the UI paths are covered in exercises.spec.
  const K = "python-for-data-science/python-basics/first-steps";
  const post = (data: object) => request.post("/api/submit", { data });
  await post({ key: `${K}/savings`, code: "savings = 100\ngrowth = 1.1\nresult = savings * growth ** 7\nprint(result)" });
  await post({ key: `${K}/types-quiz`, answer: 1 });
  await post({ key: `${K}/classify-types`, answer: { "42": "int", "-7": "int", "3.14": "float", "2.0": "float", '"hello"': "str", '"42"': "str", True: "bool", False: "bool" } });
  await post({ key: `${K}/order-bmi`, answer: ["height = 1.79", "weight = 82.0", "bmi = weight / height ** 2", "if bmi > 25:", "    print('above 25')"] });

  // Slides, through the UI.
  await page.goto(`${LESSON}/intro`);
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(page.getByText("3 / 3")).toBeVisible();
  await page.getByRole("button", { name: /Got it/ }).click();
  await expect(page.getByText("Correct! +50 XP")).toBeVisible();

  // Sequential, step by step.
  await page.goto(`${LESSON}/trip-budget`);
  await setCode(page, "hotel = 120 * (days - 1)");
  await page.getByRole("button", { name: "Submit answer" }).click();
  await expect(page.getByText("Step 1 of 2 done")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Step 2" })).toBeVisible();
  await setCode(page, "food = 45 * days\ntotal = hotel + food\nprint(total)");
  await page.getByRole("button", { name: "Submit answer" }).click();
  await expect(page.getByText("Correct! +100 XP")).toBeVisible();
  // Finishing the chapter catches the course's monster.
  await page.getByRole("dialog", { name: "You caught Loopip!" }).getByRole("button", { name: "Nice" }).click();
  await page.getByRole("button", { name: "Finish course" }).click();

  await expect(page).toHaveURL("/courses/python-for-data-science/complete");
  await expect(page.getByRole("heading", { name: "Course complete" })).toBeVisible();
  await expect(page.getByRole("main").getByText("XP earned")).toBeVisible();
  await expect(page.getByRole("main").getByText("400", { exact: true })).toBeVisible();

  // F08: outline drawer shows everything done.
  await page.goto(`${LESSON}/savings`);
  await page.getByRole("button", { name: "Course outline" }).click();
  const drawer = page.getByRole("dialog", { name: "Course outline" });
  await expect(drawer.getByLabel("Done")).toHaveCount(6);
  await drawer.getByRole("link", { name: /Plan a trip budget/ }).click();
  await expect(page).toHaveURL(`${LESSON}/trip-budget`);
  await expect(drawer).toBeHidden();
});

test("F01-H2 dashboard continues at the next unfinished exercise", async ({ page, request }) => {
  await request.post("/api/submit", { data: { key: "python-for-data-science/python-basics/first-steps/intro" } });
  await page.goto("/");
  await expect(page.getByText("Pick up where you left off")).toBeVisible();
  await page.getByRole("link", { name: "Continue" }).click();
  await expect(page).toHaveURL(`${LESSON}/savings`);
});

test("F08-H1 outline drawer closes with Escape", async ({ page }) => {
  await page.goto(`${LESSON}/savings`);
  await page.getByRole("button", { name: "Course outline" }).click();
  await expect(page.getByRole("dialog", { name: "Course outline" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Course outline" })).toBeHidden();
  // Opens again after closing with Escape.
  await page.getByRole("button", { name: "Course outline" }).click();
  await expect(page.getByRole("dialog", { name: "Course outline" })).toBeVisible();
});

test("F07-H1 / S14-H1 progress page, then reset everything", async ({ page, request }) => {
  await request.post("/api/submit", { data: { key: "python-for-data-science/python-basics/first-steps/intro" } });
  await page.goto("/progress");
  await expect(page.getByRole("link", { name: "Python for Data Science" })).toBeVisible();
  await expect(page.getByRole("main").getByRole("listitem").getByText("50 XP")).toBeVisible();

  await page.goto("/settings");
  await page.getByRole("button", { name: "Reset…" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Reset", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Progress reset.");
  await page.goto("/progress");
  await expect(page.getByText("Nothing finished yet")).toBeVisible();
});
