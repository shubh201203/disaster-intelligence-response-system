import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'python -m uvicorn app.main:app --port 8001',
      cwd: './backend',
      port: 8001,
      reuseExistingServer: false,
      env: {
        DATABASE_URL: 'sqlite:///C:/Users/shubh/Downloads/DIRS/dirs_dev.db'
      }
    },
    {
      command: 'npx vite --port 5173',
      cwd: './frontend',
      port: 5173,
      reuseExistingServer: false,
      env: {
        VITE_API_BASE_URL: 'http://localhost:8001/api/v1'
      }
    }
  ],
});
