import { defineConfig, devices } from "@playwright/test";

// E2E runs its own dev server on port 3100 with a throwaway progress DB, so it
// never touches your real progress. Stop `npm run dev` first if Next complains
// about a second dev server in the same folder.
export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  globalSetup: "./tests/e2e/global-setup.ts",
  use: { baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
  webServer: {
    command: "next dev -H 127.0.0.1 -p 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
    timeout: 120_000,
    env: { PROGRESS_DB: "data/e2e.db" },
  },
});
