import { LESSON, expect, expectAccessible, expectNoHorizontalScroll, resetProgress, test } from "./fixtures";

test.beforeEach(async ({ page }) => resetProgress(page));

test("F01-H1 / F02-H1 start the first course from the dashboard and from the track", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Start learning")).toBeVisible();
  await expect(page.getByRole("link", { name: "Start course" })).toHaveAttribute("href", `${LESSON}/intro`);

  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Tracks" }).click();
  await page.getByRole("link", { name: /Data Science & Machine Learning/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Data Science & Machine Learning" })).toBeVisible();
  await page.getByRole("link", { name: /Python for Data Science/ }).click();
  await page.getByRole("link", { name: "Start course" }).click();
  await expect(page.getByText("Lesson · Python as a calculator")).toBeVisible();
  await expect(page.getByText("1 / 3")).toBeVisible();
});

test("F02-E1 a course without lessons shows its plan and no start button", async ({ page }) => {
  await page.goto("/courses/rag-systems");
  await expect(page.getByText("No lessons in this course yet")).toBeVisible();
  await expect(page.getByText("Content coming")).toBeVisible();
  await expect(page.getByRole("link", { name: /Start course/ })).toHaveCount(0);
  await expect(page.getByText("Chunking and indexing")).toBeVisible();
});

test.describe("not found", () => {
  test.use({ allow404: true });
  test("F02-E2 unknown URLs show not found", async ({ page }) => {
  for (const url of ["/courses/nope", "/tracks/nope", `${LESSON}/nope`]) {
    const r = await page.goto(url);
    expect(r?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "Nothing here" })).toBeVisible();
  }
  });
});

test("F02-E3 keyboard only from tracks to a course", async ({ page }) => {
  await page.goto("/tracks");
  const link = page.getByRole("link", { name: /AI Engineering/ });
  for (let i = 0; i < 20 && !(await link.evaluate((el) => el === document.activeElement)); i++) await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { level: 1, name: "AI Engineering" })).toBeVisible();
});

const SCREENS = [
  "/",
  "/tracks",
  "/tracks/data-science-ml",
  "/courses/python-for-data-science",
  "/courses/rag-systems",
  `${LESSON}/intro`,
  `${LESSON}/savings`,
  `${LESSON}/types-quiz`,
  `${LESSON}/classify-types`,
  `${LESSON}/order-bmi`,
  `${LESSON}/trip-budget`,
  "/courses/python-for-data-science/complete",
  "/progress",
  "/settings",
];

for (const url of SCREENS) {
  test(`a11y + mobile: ${url}`, async ({ page }) => {
    await page.goto(url);
    await page.waitForLoadState("networkidle");
    await expectAccessible(page);
    await page.setViewportSize({ width: 390, height: 844 });
    await expectNoHorizontalScroll(page);
  });
}
