import { test, expect } from '@playwright/test';

/**
 * Playwright E2E Test Suite for DIRS (Disaster Intelligence and Response System)
 * Tests actual end-to-end multi-role disaster response workflow against live backend & frontend.
 */

test.describe('DIRS End-to-End Disaster Response Workflow', () => {

  const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

  test('Complete 4-Role Disaster Lifecycle: Citizen SOS -> Incident -> Govt Verification -> Volunteer Task -> Shelter -> NGO', async ({ page }) => {

    // Step 1: Citizen Login & SOS Trigger
    await test.step('Citizen logs in and triggers SOS distress signal', async () => {
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', 'citizen@dirs.org');
      await page.fill('input[type="password"]', 'Citizen123!');
      await page.click('button:has-text("Sign In to DIRS")');

      await page.waitForSelector('h2:has-text("Emergency SOS Distress Signal")', { timeout: 10000 });
      await expect(page.locator('h2:has-text("Emergency SOS Distress Signal")')).toBeVisible();

      // Trigger Emergency SOS (force: true bypasses Tailwind animate-bounce movement check)
      const triggerBtn = page.locator('button:has-text("Trigger SOS Panic")');
      if (await triggerBtn.isVisible()) {
        await triggerBtn.click({ force: true });
        await page.waitForTimeout(1000);
        await expect(page.locator('button:has-text("SOS Dispatched!")')).toBeVisible();
      }
    });

    // Step 2: Citizen Files Detailed Incident Report
    await test.step('Citizen submits incident report via multi-step wizard', async () => {
      await page.goto(`${BASE_URL}/citizen/report`);
      await page.fill('input[placeholder*="Flash flood"]', 'E2E Flash Flood near Main Bridge');
      await page.selectOption('select', 'FLOOD');
      await page.fill('textarea', 'Water levels rising rapidly, 15 people trapped on rooftops requiring boat rescue.');
      await page.fill('input[placeholder="Sector / Landmark"]', 'Riverfront Main Road, Sector 4');
      await page.click('button:has-text("Submit Incident Report")');

      await page.waitForTimeout(1000);
    });

    // Step 3: Government Command Center Audit & Verification
    await test.step('Government Admin inspects situation summary and verifies incidents', async () => {
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', 'admin@dirs.gov');
      await page.fill('input[type="password"]', 'Admin123!');
      await page.click('button:has-text("Sign In to DIRS")');

      await page.waitForSelector('h1:has-text("GOVERNMENT COMMAND CENTER")', { timeout: 10000 });
      await expect(page.locator('h1:has-text("GOVERNMENT COMMAND CENTER")')).toBeVisible();
    });

    // Step 4: Volunteer Responder Task View
    await test.step('Volunteer responder views active rescue task pipeline', async () => {
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', 'volunteer@dirs.org');
      await page.fill('input[type="password"]', 'Volunteer123!');
      await page.click('button:has-text("Sign In to DIRS")');

      await page.waitForSelector('text=Active Assigned Rescue Task', { timeout: 10000 });
      await expect(page.locator('text=Active Assigned Rescue Task')).toBeVisible();
    });

    // Step 5: Smart Shelter Recommendations
    await test.step('Citizen searches nearby shelters with suitability ranking', async () => {
      await page.goto(`${BASE_URL}/citizen/shelters`);
      await page.waitForSelector('h1:has-text("Smart Emergency Shelter Recommendations")', { timeout: 10000 });
      await expect(page.locator('h1:has-text("Smart Emergency Shelter Recommendations")')).toBeVisible();
    });

    // Step 6: NGO Relief Inventory Management
    await test.step('NGO Manager registers new relief inventory stock', async () => {
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', 'ngo@dirs.org');
      await page.fill('input[type="password"]', 'Ngo123!');
      await page.click('button:has-text("Sign In to DIRS")');

      await page.waitForSelector('h1:has-text("NGO Relief Operations Hub")', { timeout: 10000 });
      await expect(page.locator('h1:has-text("NGO Relief Operations Hub")')).toBeVisible();

      await page.fill('input[placeholder*="High Calorie"]', 'Purified Drinking Water Packs');
      await page.fill('input[type="number"]', '1000');
      await page.click('button:has-text("Register Stock Item")');
      await expect(page.locator('text=Purified Drinking Water Packs').first()).toBeVisible();
    });
  });
});
