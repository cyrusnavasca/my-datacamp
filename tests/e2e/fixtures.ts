import AxeBuilder from "@axe-core/playwright";
import { test as base, expect, type Page } from "@playwright/test";

export const LESSON = "/learn/python-for-data-science/python-basics/first-steps";

/** Every test fails on console errors and 5xx responses. */
export const test = base.extend<{ errors: string[]; allow404: boolean }>({
  allow404: [false, { option: true }],
  errors: [
    async ({ page, allow404 }, use) => {
      const errors: string[] = [];
      page.on("console", (m) => {
        if (m.type() !== "error") return;
        if (allow404 && m.text().includes("status of 404")) return;
        errors.push(`console: ${m.text()}`);
      });
      page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
      page.on("response", (r) => {
        if (r.status() >= 500) errors.push(`${r.status()} ${r.url()}`);
      });
      await use(errors);
      expect(errors, "console errors / 5xx").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };

export async function resetProgress(page: Page) {
  const r = await page.request.post("/api/settings", { data: { reset: "all" } });
  expect(r.ok()).toBe(true);
}

export async function expectAccessible(page: Page) {
  const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
}

export async function expectNoHorizontalScroll(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

/** Type into the CodeMirror editor, replacing its content. */
export async function setCode(page: Page, code: string) {
  const editor = page.getByRole("textbox", { name: "Code editor" });
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.press("Delete");
  await editor.evaluate((el, text) => {
    // insertText avoids CodeMirror auto-indent and bracket closing on typed input.
    el.ownerDocument.execCommand("insertText", false, text);
  }, code);
}

/** Feedback banners. Excludes Next's (empty) route announcer, which is also role=alert. */
export const alertBox = (page: Page) => page.locator('[role="alert"]:not(#__next-route-announcer__)');
