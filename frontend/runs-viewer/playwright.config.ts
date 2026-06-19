/**
 * Playwright configuration for the RF Runs Viewer E2E suite.
 *
 * Strategy: run against `vite preview` which serves the static export fixture
 * bundled by the app. The app in static mode (no VITE_RUNS_FRONTEND_LOOPBACK_API)
 * reads the bundled fixture import directly, so the dev server (port 5175)
 * works equally well for E2E without requiring a production build first.
 *
 * webServer uses `vite dev` (faster, no build step needed for E2E).
 * Tests live in e2e/ directory.
 */

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // Parallel to speed up; use 1 worker for now (static fixture, no flake risk)
  workers: 1,
  // Retry once on CI-style flake
  retries: process.env.CI ? 2 : 0,
  // Timeout per test
  timeout: 30_000,
  // Reporter
  reporter: [["list"], ["html", { open: "never" }]],

  use: {
    // Base URL — vite dev server
    baseURL: "http://localhost:5175",
    // Only capture on failure
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    // Headless by default
    headless: true,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: {
    command: "pnpm run dev",
    url: "http://localhost:5175",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    // Pipe output to help debug failures
    stdout: "pipe",
    stderr: "pipe",
  },
});
