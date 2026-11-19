import { defineConfig, devices } from '@playwright/test';

/**
 * DIRS Phase 6D-B Milestone 4 Gate 3
 * Dedicated Playwright Configuration for End-to-End Workflow & Acceptance Testing.
 *
 * Architecture Invariants:
 * 1. Chromium Exclusive: Uses local pre-installed Chromium runtime (chromium-1243).
 * 2. Port Isolation: Targets frontend dev server on port 5173.
 * 3. Independent: Does not modify or overwrite playwright.contract.config.ts.
 * 4. Deterministic: Single worker execution for Windows environment stability.
 */
export default defineConfig({
  testDir: './tests/e2e',
  testMatch: /.*\.spec\.ts/,
  timeout: 30 * 1000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npx vite --port 5173',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60 * 1000,
    env: {
      NODE_OPTIONS: '--max-old-space-size=4096',
    },
  },
});
