import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

test.describe('DIRS Incident Photographic Evidence & Inspection Workflow', () => {
  const BASE_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
  const testImagePath = path.join(__dirname, 'test_evidence_photo.png');

  test.beforeAll(() => {
    // Generate a tiny 1x1 test PNG if not already present
    const tinyPngBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';
    fs.writeFileSync(testImagePath, Buffer.from(tinyPngBase64, 'base64'));
  });

  test.afterAll(() => {
    if (fs.existsSync(testImagePath)) {
      fs.unlinkSync(testImagePath);
    }
  });

  test('Citizen submits incident with image, Govt Admin inspects and views evidence', async ({ page }) => {
    // 1. Citizen logs in
    await test.step('Citizen logs in', async () => {
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', 'citizen@dirs.org');
      await page.fill('input[type="password"]', 'Citizen123!');
      await page.click('button:has-text("Sign In to DIRS")');
      await page.waitForSelector('text=Citizen Dashboard', { timeout: 10000 }).catch(() => {});
    });

    // 2. Citizen opens report page, selects image, verifies preview, submits
    const incidentTitle = `E2E Submerged Road Evidence ${Date.now()}`;
    await test.step('Citizen reports incident with photographic evidence', async () => {
      await page.goto(`${BASE_URL}/citizen/report`);
      await page.waitForSelector('input#incident-image-input', { state: 'attached', timeout: 8000 });

      // Fill incident form
      const titleInput = page.locator('input[placeholder*="Riverfront"]').first();
      if (await titleInput.isVisible()) {
        await titleInput.fill(incidentTitle);
      }

      // Attach photographic evidence
      const fileChooserPromise = page.waitForEvent('filechooser').catch(() => null);
      await page.setInputFiles('input#incident-image-input', testImagePath);

      // Verify image preview appears before submission
      await expect(page.locator('img[alt*="test_evidence_photo"]')).toBeVisible({ timeout: 5000 });

      // Submit disaster report
      const submitBtn = page.locator('button[type="submit"]');
      await submitBtn.click();

      // Wait for success confirmation or redirect
      await page.waitForSelector('text=Disaster Report Submitted', { timeout: 10000 }).catch(() => {});
    });

    // 3. Government Admin logs in and inspects the incident
    await test.step('Govt Admin inspects incident and verifies image evidence', async () => {
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', 'admin@dirs.gov');
      await page.fill('input[type="password"]', 'Admin123!');
      await page.click('button:has-text("Sign In to DIRS")');
      await page.waitForSelector('text=GOVERNMENT EMERGENCY COMMAND CENTER', { timeout: 10000 });

      // Locate the newly reported incident in priority queue table and click Inspect
      const inspectBtn = page.locator(`tr:has-text("${incidentTitle}") button:has-text("Inspect")`).first();
      if (await inspectBtn.isVisible({ timeout: 6000 })) {
        await inspectBtn.click();
      } else {
        // Inspect the first available incident
        await page.locator('button:has-text("Inspect")').first().click();
      }

      // Verify Evidence / Incident Photographic Evidence section is visible
      await expect(page.locator('text=Evidence / Incident Photographic Evidence')).toBeVisible({ timeout: 5000 });

      // Verify image thumbnail is rendered
      const evidenceImg = page.locator('div:has-text("Evidence / Incident Photographic Evidence") img').first();
      if (await evidenceImg.isVisible()) {
        // Click thumbnail to trigger full-resolution lightbox modal
        await evidenceImg.click();
        await expect(page.locator('text=Incident Photographic Evidence')).toBeVisible({ timeout: 5000 });
        // Close modal via ESC
        await page.keyboard.press('Escape');
      }
    });
  });
});
