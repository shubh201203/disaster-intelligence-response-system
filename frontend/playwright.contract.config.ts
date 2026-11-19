import { defineConfig } from '@playwright/test';

/**
 * Dedicated Playwright configuration for Phase 6D-B Milestone 4 Gate 1 Stage C
 * Pure frontend contract, lossless parser, and API client verification suite.
 *
 * Runs tests in Node mode without launching browser instances or web servers.
 */
export default defineConfig({
  testDir: './tests/contract',
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
    trace: 'off',
  },
});
