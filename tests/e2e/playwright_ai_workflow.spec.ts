import { test, expect } from '@playwright/test';

/**
 * DIRS Phase 3A AI Intelligence Playwright E2E Verification Suite
 * Tests live AI severity, confidence scoring, explainable AI factor breakdown,
 * and priority scoring in the Government Command Center.
 */

test.describe('DIRS Phase 3A AI Intelligence Workflow', () => {
  const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

  test('Government Officer inspects AI severity, confidence, explainability, and priority scores', async ({ page }) => {

    // Step 1: Login as Government Admin using Quick Demo button
    await test.step('Government Admin logs into Command Center', async () => {
      await page.goto(`${BASE_URL}/login`);
      await page.click('button:has-text("Govt Command")');

      await page.waitForSelector('h1:has-text("GOVERNMENT COMMAND CENTER")', { timeout: 10000 });
      await expect(page.locator('h1:has-text("GOVERNMENT COMMAND CENTER")')).toBeVisible();
    });

    // Step 2: Inspect Priority Queue table containing AI weighted scores
    await test.step('Verify AI Priority Incident Queue table rendering', async () => {
      await expect(page.locator('text=Priority Incident Queue (AI Weighted 0-100)')).toBeVisible();
      const inspectButtons = page.locator('button:has-text("Inspect")');
      await expect(inspectButtons.first()).toBeVisible();
    });

    // Step 3: Inspect incident details and verify AI severity, confidence, and explainability breakdown
    await test.step('Inspect incident to verify AI severity, confidence, and explainability factors', async () => {
      const inspectBtn = page.locator('button:has-text("Inspect")').first();
      await inspectBtn.click();

      // Verify AI Severity & Confidence card header
      await expect(page.locator('text=AI Severity & Confidence')).toBeVisible();

      // Verify Explainable AI scoring breakdown header and factors
      await expect(page.locator('text=CV Damage & Intelligence Breakdown:')).toBeVisible();

      // Verify action buttons
      await expect(page.locator('button:has-text("Verify Incident")')).toBeVisible();
    });
  });
});
