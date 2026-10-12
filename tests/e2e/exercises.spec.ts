import { LESSON, alertBox, expect, resetProgress, setCode, test } from "./fixtures";

const RIGHT = "savings = 100\ngrowth = 1.1\nresult = savings * growth ** 7\nprint(result)";

test.beforeEach(async ({ page }) => resetProgress(page));

test.describe("F03 coding exercise", () => {
  test("F03-H1 run then submit the right answer", async ({ page }) => {
    await page.goto(`${LESSON}/savings`);
    await setCode(page, "print(6 * 7)");
    await page.getByRole("button", { name: "Run" }).click();
    await expect(page.locator("[aria-live=polite]").getByText("42")).toBeVisible();

    await setCode(page, RIGHT);
    await page.getByRole("button", { name: "Submit answer" }).click();
    await expect(page.getByText("Correct! +100 XP")).toBeVisible();
    await expect(page.getByText("Money nearly doubles")).toBeVisible();
    await expect(page.getByRole("button", { name: "Continue" })).toBeFocused();
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page).toHaveURL(`${LESSON}/types-quiz`);
  });

  test("F03-N1/N2/N3 blanks, wrong value and runtime errors give feedback", async ({ page }) => {
    await page.goto(`${LESSON}/savings`);
    await page.getByRole("button", { name: "Submit answer" }).click();
    await expect(alertBox(page)).toContainText("Fill in the");

    await setCode(page, "savings = 100\ngrowth = 1.1\nresult = savings * growth ** 6\nprint(result)");
    await page.getByRole("button", { name: "Submit answer" }).click();
    await expect(alertBox(page)).toContainText("should be");

    await setCode(page, "print(1/0)");
    await page.getByRole("button", { name: "Run" }).click();
    await expect(page.getByText("ZeroDivisionError: division by zero")).toBeVisible();
  });

  test("F03-E1/E2 hint costs XP, survives a refresh, answer fills the editor", async ({ page }) => {
    await page.goto(`${LESSON}/savings`);
    await expect(page.getByText("100 XP", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: /Take hint/ }).click();
    await expect(page.getByText("Raise growth to the power")).toBeVisible();
    await expect(page.getByText("70 XP", { exact: true })).toBeVisible();

    await setCode(page, "x = 'kept'");
    await page.getByRole("button", { name: "Run" }).click();
    await expect(page.getByText("Ran without printing anything.")).toBeVisible();
    await page.reload();
    await expect(page.getByText("x = 'kept'")).toBeVisible();
    await expect(page.getByText("Raise growth to the power")).toBeVisible();

    await page.getByRole("button", { name: /Show answer/ }).click();
    await expect(page.getByText("result = savings * growth ** 7")).toBeVisible();
    await page.getByRole("button", { name: "Submit answer" }).click();
    await expect(page.getByText("Correct!", { exact: true })).toBeVisible(); // 0 XP left after hint + answer
  });

  test("F03-E3 Ctrl/Cmd+Enter runs the code", async ({ page }) => {
    await page.goto(`${LESSON}/savings`);
    await setCode(page, "print('shortcut')");
    await page.keyboard.press("ControlOrMeta+Enter");
    await expect(page.locator("[aria-live=polite]").getByText("shortcut")).toBeVisible();
  });

  test("F03-E4 double click on submit awards XP once", async ({ page }) => {
    await page.goto(`${LESSON}/savings`);
    await setCode(page, RIGHT);
    await page.getByRole("button", { name: "Submit answer" }).dblclick();
    await expect(page.getByText("Correct! +100 XP")).toBeVisible();
    await page.goto("/progress");
    await expect(page.getByRole("main").getByRole("listitem").getByText("100 XP")).toBeVisible();
  });
});

test.describe("F04 multiple choice", () => {
  test("F04-H1/E1 wrong then right, with the console", async ({ page }) => {
    await page.goto(`${LESSON}/types-quiz`);
    await setCode(page, "type(x)");
    await page.getByRole("button", { name: "Run" }).click();
    await expect(page.getByText("<class 'float'>")).toBeVisible();

    await page.getByRole("radio", { name: "int" }).check();
    await page.getByRole("button", { name: "Submit answer" }).click();
    await expect(alertBox(page)).toContainText("always returns a float");
    await page.getByRole("radio", { name: "float" }).check();
    await page.getByRole("button", { name: "Submit answer" }).click();
    await expect(page.getByText("Correct! +45 XP")).toBeVisible();
  });
});

test.describe("F05 drag and drop", () => {
  test("F05-H1 parsons with the keyboard", async ({ page }) => {
    await page.goto(`${LESSON}/order-bmi`);
    const order = ["height = 1.79", "weight = 82.0", "bmi = weight / height ** 2", "if bmi > 25:", "print('above 25')"];
    // Move each line to its target position with keyboard sorting.
    for (let target = 0; target < order.length; target++) {
      const labels = await page.getByRole("button", { name: /^Move: / }).evaluateAll((els) => els.map((e) => e.getAttribute("aria-label")!.slice(6)));
      const from = labels.indexOf(order[target]);
      if (from === target) continue;
      await page.getByRole("button", { name: `Move: ${order[target]}` }).focus();
      await page.keyboard.press("Space");
      for (let i = 0; i < from - target; i++) {
        await page.waitForTimeout(150); // let dnd-kit measure before the next move
        await page.keyboard.press("ArrowUp");
      }
      await page.waitForTimeout(150);
      await page.keyboard.press("Space");
      await expect(page.getByRole("button", { name: /^Move: / }).nth(target)).toHaveAttribute("aria-label", `Move: ${order[target]}`);
    }
    await page.getByRole("button", { name: "Check order" }).click();
    await expect(alertBox(page)).toContainText("1 line is in the wrong place or wrongly indented");
    await page.getByRole("button", { name: "Indent: print('above 25')", exact: true }).click();
    await page.getByRole("button", { name: "Check order" }).click();
    await expect(page.getByText(/Correct! \+\d+ XP/)).toBeVisible();
  });

  test("F05-H2 classify", async ({ page }) => {
    await page.goto(`${LESSON}/classify-types`);
    const answers: Record<string, string> = { "42": "int", "-7": "int", "3.14": "float", "2.0": "float", '"hello"': "str", '"42"': "int", True: "bool", False: "bool" };
    for (const [item, zone] of Object.entries(answers)) await page.getByRole("radiogroup", { name: `Group for: ${item}` }).getByRole("radio", { name: zone }).click();
    await page.getByRole("button", { name: "Check groups" }).click();
    await expect(alertBox(page)).toContainText("1 of 8 items are in the wrong group");
    await page.getByRole("radiogroup", { name: 'Group for: "42"' }).getByRole("radio", { name: "str" }).click();
    await page.getByRole("button", { name: "Check groups" }).click();
    await expect(page.getByText("Correct! +45 XP")).toBeVisible();
  });
});
