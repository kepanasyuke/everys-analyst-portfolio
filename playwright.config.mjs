import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  retries: 1,
  expect: { timeout: 10_000 },
  workers: 1,
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8077",
    channel: "msedge",
    headless: true,
    viewport: { width: 1440, height: 950 },
    trace: "retain-on-failure",
    launchOptions: { args: ["--disable-gpu", "--disable-dev-shm-usage", "--disable-extensions"] },
  },
  webServer: {
    command: "python -X utf8 -m uvicorn --app-dir . app.main:app --host 127.0.0.1 --port 8077",
    url: "http://127.0.0.1:8077/api/health",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
