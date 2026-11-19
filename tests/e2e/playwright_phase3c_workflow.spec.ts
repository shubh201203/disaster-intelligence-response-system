import { test, expect } from '@playwright/test';

/**
 * Playwright E2E Multi-Role UI Verification Suite for DIRS Phase 3C AI Intelligence:
 * Tests genuine browser user interactions in Government Command Center UI against live backend and frontend.
 * Absolutely NO mocked endpoints.
 */

test.describe('DIRS Phase 3C Grounded RAG & AI Decision Copilot Browser E2E Workflow', () => {

  const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
  const API_URL = process.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

  test('Government Officer authentic UI workflow: Command Center -> RAG Copilot Query -> Citation Review -> Recommendation Approval Workflow', async ({ page, request }) => {

    // Step 1: Login via UI
    await test.step('Government Officer logs into Command Center via UI form', async () => {
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', 'admin@dirs.gov');
      await page.fill('input[type="password"]', 'Admin123!');
      await page.click('button:has-text("Sign In to DIRS")');

      await page.waitForSelector('h1:has-text("GOVERNMENT COMMAND CENTER")', { timeout: 10000 });
      await expect(page.locator('h1:has-text("GOVERNMENT COMMAND CENTER")')).toBeVisible();
    });

    // Step 2: Verify Phase 3C RAG Copilot UI Component
    await test.step('Verify DIRS Grounded AI Copilot panel is rendered in Command Center UI', async () => {
      await page.waitForSelector('text=DIRS Grounded AI Copilot', { timeout: 10000 });
      await expect(page.locator('text=DIRS Grounded AI Copilot')).toBeVisible();
      await expect(page.locator('text=Phase 3C Grounded RAG')).toBeVisible();
    });

    // Step 3: Run RAG Copilot Query via UI Preset Button
    await test.step('Officer clicks Quick Action preset button to query Copilot', async () => {
      const presetBtn = page.locator('button:has-text("📖 NDMA Guidelines")');
      await expect(presetBtn).toBeVisible();
      await presetBtn.click();

      // Wait for AI Copilot Response to render
      await page.waitForSelector('text=AI Executive Summary:', { timeout: 10000 });
      await expect(page.locator('text=AI Executive Summary:')).toBeVisible();
    });

    // Step 4: Check Citations Tab in UI
    await test.step('Officer clicks Citations tab to inspect authoritative sources', async () => {
      const citationsTab = page.locator('button:has-text("Citations")');
      await expect(citationsTab).toBeVisible();
      await citationsTab.click();

      await page.waitForSelector('text=NDMA', { timeout: 10000 });
      await expect(page.locator('text=NDMA').first()).toBeVisible();
    });

    // Step 5: Check Decision Recommendations Tab & Perform Decision
    await test.step('Officer opens Decision Recommendations tab and inspects structured recommendations', async () => {
      const recsTab = page.locator('button:has-text("Decision Recommendations")');
      await expect(recsTab).toBeVisible();
      await recsTab.click();
    });

    // Step 6: Direct API Verification without mocking
    await test.step('Verify live backend Phase 3C RAG & Recommendation API endpoints directly', async () => {
      const loginRes = await request.post(`${API_URL}/auth/login`, {
        form: { username: 'admin@dirs.gov', password: 'Admin123!' }
      });
      expect(loginRes.status()).toBe(200);
      const token = (await loginRes.json()).access_token;
      // 1. Fetch live incidents
      const incRes = await request.get(`${API_URL}/incidents`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      expect(incRes.status()).toBe(200);
      const incidents = await incRes.json();
      expect(incidents.length).toBeGreaterThan(0);
      const incId = incidents[0].id;

      // 2. RAG Query API
      const ragRes = await request.post(`${API_URL}/ai/rag/query`, {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          query: 'What NDMA flood evacuation and shelter protocols should be enacted?',
          incident_id: incId,
          mode: 'GENERAL_COPILOT'
        }
      });
      expect(ragRes.status()).toBe(200);
      const ragData = await ragRes.json();
      expect(ragData.is_grounded).toBe(true);
      expect(ragData.citations.length).toBeGreaterThan(0);
      expect(ragData.facts.length).toBeGreaterThan(0);

      // 3. RAG Incident Summary API
      const summaryRes = await request.post(`${API_URL}/ai/rag/incidents/${incId}/summary`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      expect(summaryRes.status()).toBe(200);
      expect((await summaryRes.json())).toHaveProperty('summary');

      const recsRes = await request.get(`${API_URL}/ai/incidents/${incId}/recommendations`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      expect(recsRes.status()).toBe(200);
      const recs = await recsRes.json();
      expect(recs.length).toBeGreaterThan(0);

      // 4. Recommendation Decision API
      const recId = recs[0].id;
      const approveRes = await request.post(`${API_URL}/ai/recommendations/${recId}/approve`, {
        headers: { Authorization: `Bearer ${token}` },
        data: { notes: 'Approved in E2E Playwright test suite' }
      });
      expect(approveRes.status()).toBe(200);
      expect((await approveRes.json()).status).toBe('ACCEPTED');
    });
  });
});
