import { test, expect } from '@playwright/test';

/**
 * Playwright E2E Multi-Role UI Verification Suite for DIRS Phase 3B AI Intelligence:
 * Tests genuine browser user interactions in Government Command Center UI against live backend and frontend.
 * Absolutely NO mocked endpoints.
 */

test.describe('DIRS Phase 3B AI Intelligence Browser E2E Workflow', () => {

  const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
  const API_URL = process.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

  test('Government Officer authentic UI workflow: Command Center -> Incident Inspection -> Phase 3B AI Intelligence Panel -> Apply AI Override -> Verify Incident', async ({ page, request }) => {

    // Step 1: Login via UI
    await test.step('Government Officer logs into Command Center via UI form', async () => {
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', 'admin@dirs.gov');
      await page.fill('input[type="password"]', 'Admin123!');
      await page.click('button:has-text("Sign In to DIRS")');

      await page.waitForSelector('h1:has-text("GOVERNMENT COMMAND CENTER")', { timeout: 10000 });
      await expect(page.locator('h1:has-text("GOVERNMENT COMMAND CENTER")')).toBeVisible();
    });

    // Step 2: Interact with Priority Queue UI Table & Inspect Incident
    await test.step('Officer selects and inspects priority incident row', async () => {
      await page.waitForSelector('text=Priority Incident Queue (AI Weighted 0-100)', { timeout: 10000 });
      await expect(page.locator('text=Priority Incident Queue (AI Weighted 0-100)')).toBeVisible();

      const inspectBtn = page.locator('button:has-text("Inspect")').first();
      await expect(inspectBtn).toBeVisible();
      await inspectBtn.click();
    });

    // Step 3: Verify Phase 3B AI Panel rendered in UI
    await test.step('Verify Phase 3B Computer Vision, Risk & Resource Demand breakdown in UI', async () => {
      await page.waitForSelector('text=CV Damage & Intelligence Breakdown', { timeout: 10000 });
      await expect(page.locator('text=CV Damage & Intelligence Breakdown')).toBeVisible();
      await expect(page.locator('text=Phase 3B AI')).toBeVisible();
      await expect(page.locator('text=CV Damage Class:')).toBeVisible();
      await expect(page.locator('text=Disaster Risk Level:')).toBeVisible();
      await expect(page.locator('text=Forecasted Demand:')).toBeVisible();
    });

    // Step 4: Execute Government AI Override via UI Button
    await test.step('Government Officer applies AI prediction override via UI button', async () => {
      const overrideBtn = page.locator('button:has-text("Apply Government AI Override")');
      await expect(overrideBtn).toBeVisible();

      // Handle browser dialog/alert
      page.once('dialog', async dialog => {
        expect(dialog.message()).toContain('AI Override');
        await dialog.accept();
      });

      await overrideBtn.click();
    });

    // Step 5: Execute Incident Verification via UI Button
    await test.step('Government Officer verifies incident via UI button', async () => {
      const verifyBtn = page.locator('button:has-text("Verify Incident")');
      await expect(verifyBtn).toBeVisible();
      await verifyBtn.click();
    });

    // Step 6: Direct API Verification to ensure no mocking occurred
    await test.step('Verify live backend API response consistency without mocking', async () => {
      const loginRes = await request.post(`${API_URL}/auth/login`, {
        form: { username: 'admin@dirs.gov', password: 'Admin123!' }
      });
      expect(loginRes.status()).toBe(200);
      const token = (await loginRes.json()).access_token;

      const incRes = await request.get(`${API_URL}/incidents`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      expect(incRes.status()).toBe(200);
      const incidents = await incRes.json();
      expect(incidents.length).toBeGreaterThan(0);
      const incId = incidents[0].id;

      const cvRes = await request.post(`${API_URL}/ai/incidents/${incId}/vision`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      expect(cvRes.status()).toBe(200);
      expect((await cvRes.json())).toHaveProperty('damage_class');

      const riskRes = await request.post(`${API_URL}/ai/incidents/${incId}/risk`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      expect(riskRes.status()).toBe(200);
      expect((await riskRes.json())).toHaveProperty('risk_score');

      const demandRes = await request.post(`${API_URL}/ai/incidents/${incId}/resource-demand`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      expect(demandRes.status()).toBe(200);
      expect((await demandRes.json())).toHaveProperty('predictions');
    });
  });
});
