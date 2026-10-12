import { LESSON, expect, expectAccessible, expectNoHorizontalScroll, resetProgress, test } from "./fixtures";

test.beforeEach(async ({ page }) => resetProgress(page));

test("dex: choose a starter, earn type-bonus XP, catch the course monster", async ({ page, request }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Choose your first partner/ }).click();
  await expect(page).toHaveURL("/dex");
  await expectAccessible(page);
  await page.getByRole("button", { name: "Choose Pybble" }).click();
  await expect(page.getByRole("heading", { name: "Pybble", level: 2 })).toBeVisible();
  await expect(page.getByRole("banner").getByText("Lv 1")).toBeVisible();

  // Finish the rest of the chapter through the API, the slides through the UI.
  const K = "python-for-data-science/python-basics/first-steps";
  const post = (data: object) => request.post("/api/submit", { data });
  await post({ key: `${K}/savings`, code: "savings = 100\ngrowth = 1.1\nresult = savings * growth ** 7\nprint(result)" });
  await post({ key: `${K}/types-quiz`, answer: 1 });
  await post({ key: `${K}/classify-types`, answer: { "42": "int", "-7": "int", "3.14": "float", "2.0": "float", '"hello"': "str", '"42"': "str", True: "bool", False: "bool" } });
  await post({ key: `${K}/order-bmi`, answer: ["height = 1.79", "weight = 82.0", "bmi = weight / height ** 2", "if bmi > 25:", "    print('above 25')"] });
  await post({ key: `${K}/trip-budget`, code: "hotel = 120 * (days - 1)", step: 0 });
  await post({ key: `${K}/trip-budget`, code: "food = 45 * days\ntotal = hotel + food\nprint(total)", step: 1 });

  await page.goto(`${LESSON}/intro`);
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.getByRole("button", { name: /Got it/ }).click();
  await expect(page.getByText("Correct! +50 XP")).toBeVisible();
  await expect(page.getByText(/Pybble \+75 XP \(type bonus\)/)).toBeVisible();
  const dialog = page.getByRole("dialog", { name: "You caught Loopip!" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Nice" }).click();
  await expect(dialog).toBeHidden();

  await page.goto("/dex");
  await expect(page.getByText("2 of 19 caught")).toBeVisible();
  await page.getByRole("listitem").filter({ hasText: "Loopip" }).getByRole("button", { name: "Make partner" }).click();
  await expect(page.getByRole("heading", { name: "Loopip", level: 2 })).toBeVisible();
  await expectNoHorizontalScroll(page);
});
