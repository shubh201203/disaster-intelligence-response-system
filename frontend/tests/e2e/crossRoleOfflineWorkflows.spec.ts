/**
 * DIRS Phase 6G / Accelerated Programme Work Package 3
 * Cross-Role UI Integration & Offline Resilience E2E Browser Test Suite.
 *
 * Verifies real browser workflows:
 * 1. TC-WP3-E2E-01: Citizen saves offline incident draft, views banner and queue in DraftSyncManager, survives reload.
 * 2. TC-WP3-E2E-02: Citizen dashboard displays municipal recovery & essential services indicators.
 * 3. TC-WP3-E2E-03: Volunteer switches to Field Damage Inspection tab, completes inspection form and saves draft.
 * 4. TC-WP3-E2E-04: NGO views Organization Profile, toggles inventory scope (All Hubs vs My Org), and views field relief demands.
 * 5. TC-WP3-E2E-05: Government Command Center views Field Inspections Verification tab and certifier modal.
 */

import { test, expect } from '@playwright/test';
import { setupMockAuth } from './fixtures/recoveryMockFixtures';

test.describe('WP3 Cross-Role UI Integration & Offline Workflows E2E Suite', () => {
  // --------------------------------------------------------------------------
  // 1. Citizen Offline Incident Draft Workflow
  // --------------------------------------------------------------------------
  test('TC-WP3-E2E-01: Citizen creates offline incident draft and inspects queue', async ({ page }) => {
    await setupMockAuth(page, 'CITIZEN');

    // Intercept incidents list to avoid page error
    await page.route('**/api/v1/incidents*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/citizen/report');
    await page.waitForLoadState('networkidle');

    // 1. Verify Page header
    await expect(page.locator('h3:has-text("Report Emergency Disaster Incident")')).toBeVisible();

    // 2. Fill in incident form using exact placeholders
    await page.fill('input[placeholder*="flood water"]', 'Severe Inundation at Market Road');
    await page.fill('textarea[placeholder*="Describe current danger"]', 'Water logging up to 1 meter obstructing all vehicular movement');
    await page.fill('input[placeholder*="Street address"]', 'Market Road Ward 4');

    // 3. Click "Save Local Draft" button
    const saveDraftBtn = page.locator('button:has-text("Save Local Draft")');
    await expect(saveDraftBtn).toBeVisible();
    await saveDraftBtn.click();

    // 4. Verify offline banner reflects queued draft
    await expect(page.locator('text=NETWORK RESTORED')).toBeVisible();
    await expect(page.locator('text=1 local draft ready for synchronization')).toBeVisible();

    // 5. Verify draft appears in DraftSyncManager queue
    await expect(page.locator('text=Local Incident Report Drafts (IndexedDB)')).toBeVisible();
    await expect(page.locator('text=Severe Inundation at Market Road')).toBeVisible();
    await expect(page.locator('text=DRAFT').first()).toBeVisible();

    // 6. Reload page to verify IndexedDB persistence across page loads
    await page.reload();
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Severe Inundation at Market Road')).toBeVisible();
    await expect(page.locator('text=DRAFT').first()).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // 2. Citizen Community Recovery Status Overview
  // --------------------------------------------------------------------------
  test('TC-WP3-E2E-02: Citizen dashboard displays municipal recovery status card', async ({ page }) => {
    await setupMockAuth(page, 'CITIZEN');

    // Mock community summary endpoint
    await page.route('**/api/v1/recovery/monitoring/community-metrics/summary', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_wards_monitored: 15,
          average_recovery_score: 84.5,
          sector_restoration_averages: {
            power: 90.0,
            water: 85.0,
            health: 80.0,
            schools: 88.0,
            livelihoods: 75.0,
          },
          freshness_distribution: { FRESH: 12, MODERATE: 3, STALE_AMBER: 0, EXPIRED_RED: 0 },
        }),
      });
    });

    await page.route('**/api/v1/incidents*', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.goto('/citizen');
    await page.waitForLoadState('networkidle');

    // Verify Municipal Recovery & Essential Services Status card
    await expect(page.locator('text=Municipal Recovery & Essential Services Status')).toBeVisible();
    await expect(page.locator('text=84.5%')).toBeVisible();
    await expect(page.locator('text=15 monitored wards')).toBeVisible();
    await expect(page.locator('text=Power Restoration')).toBeVisible();
    await expect(page.locator('text=Clean Water Access')).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // 3. Volunteer Field Inspection & Tab Navigation
  // --------------------------------------------------------------------------
  test('TC-WP3-E2E-03: Volunteer switches to Field Damage Inspection and saves draft', async ({ page }) => {
    await setupMockAuth(page, 'VOLUNTEER');

    await page.route('**/api/v1/volunteers/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'vol-profile-01',
          user_id: 'usr-volunteer-001',
          status: 'AVAILABLE',
          skills: ['FIRST_AID', 'LOGISTICS'],
        }),
      });
    });

    await page.route('**/api/v1/volunteers/my-tasks', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.route('**/api/v1/volunteers/tasks/available', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.route('**/api/v1/recovery/damage-assessments*', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    await page.goto('/volunteer');
    await page.waitForLoadState('networkidle');

    // 1. Verify Tab buttons exist and switch to inspection
    const inspectionTab = page.locator('button:has-text("Field Damage Inspection")');
    await expect(inspectionTab).toBeVisible();
    await inspectionTab.click();

    // 2. Verify inspection form rendered
    await expect(page.locator('h3:has-text("Field Damage & Structural Inspection")')).toBeVisible();

    // 3. Fill form
    await page.fill('input[placeholder*="Incident UUID"]', 'inc-test-4411');
    await page.fill('input[placeholder*="Community Health Center"]', 'Community Clinic Sector 3');
    await page.fill('textarea[placeholder*="structural integrity"]', 'Perimeter wall collapsed, foundation intact');

    // 4. Click "Save Local Draft"
    const saveInspectionDraftBtn = page.locator('button:has-text("Save Local Draft")');
    await expect(saveInspectionDraftBtn).toBeVisible();
    await saveInspectionDraftBtn.click();

    // 5. Verify draft queue inspector
    await expect(page.locator('text=Local Field Inspection Drafts (IndexedDB)')).toBeVisible();
    await expect(page.locator('text=Community Clinic Sector 3')).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // 4. NGO Profile, Inventory Scoping & Relief Demands
  // --------------------------------------------------------------------------
  test('TC-WP3-E2E-04: NGO displays organization profile, toggles inventory scope and lists requests', async ({ page }) => {
    await setupMockAuth(page, 'NGO');

    // Mock resources requests
    await page.route('**/api/v1/resources/requests', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'req-01',
            incident_id: 'inc-01',
            incident_title: 'Central Flood Camp',
            category: 'WATER',
            quantity_requested: 500,
            quantity_fulfilled: 100,
            priority: 'HIGH',
            status: 'PENDING',
            created_at: '2026-11-18T00:00:00Z',
          },
        ]),
      });
    });

    await page.route('**/api/v1/resources', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'res-01',
            owner_id: 'usr-ngo-001',
            resource_name: '20L Drinking Water Cans',
            category: 'WATER',
            owner_type: 'NGO',
            supplier_info: 'Red Cross Relief Foundation',
            available_quantity: 400,
            total_quantity: 500,
            unit: 'cans',
          },
          {
            id: 'res-02',
            owner_id: 'usr-govt-001',
            resource_name: 'State Reserve Rations',
            category: 'FOOD',
            owner_type: 'GOVT',
            supplier_info: 'Government Central Depot',
            available_quantity: 1000,
            total_quantity: 1000,
            unit: 'kits',
          },
        ]),
      });
    });

    await page.goto('/ngo');
    await page.waitForLoadState('networkidle');

    // 1. Verify NGO Profile Card (disambiguate from header banner using main scope)
    await expect(page.locator('main').locator('text=NGO Coordinator')).toBeVisible();
    await expect(page.locator('text=REGISTERED PARTNER').or(page.locator('text=✓ VERIFIED NGO')).first()).toBeVisible();

    // 2. Verify Scope Toggle
    const myOrgBtn = page.locator('button:has-text("My Org Only")');
    const allHubsBtn = page.locator('button:has-text("All Hubs")');
    await expect(myOrgBtn).toBeVisible();
    await expect(allHubsBtn).toBeVisible();

    // Click My Org Only
    await myOrgBtn.click();
    await expect(page.locator('text=20L Drinking Water Cans')).toBeVisible();
    // Govt resource should be filtered out
    await expect(page.locator('text=State Reserve Rations')).not.toBeVisible();

    // Click All Hubs
    await allHubsBtn.click();
    await expect(page.locator('text=State Reserve Rations')).toBeVisible();

    // 3. Verify Field Relief Demands list
    await expect(page.locator('text=Field Relief Demands from Disaster Incidents')).toBeVisible();
    await expect(page.locator('text=Central Flood Camp')).toBeVisible();
    await expect(page.locator('text=500 units')).toBeVisible();

    // 4. Verify Institutional Governance Notice
    await expect(page.locator('text=Institutional Governance Policy')).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // 5. Government Command Center Field Inspection Verification
  // --------------------------------------------------------------------------
  test('TC-WP3-E2E-05: Government Command Center views Field Inspections Verification tab', async ({ page }) => {
    await setupMockAuth(page, 'GOVT');

    // Mock summary analytics & incidents
    await page.route('**/api/v1/analytics/summary', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          active_incidents: 4,
          available_shelters: 8,
          total_resources: 120,
          pending_verifications: 2,
        }),
      });
    });

    await page.route('**/api/v1/incidents*', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    // Mock damage assessments endpoint queried by CommandCenter
    await page.route('**/api/v1/recovery/assessments*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'asm-field-01',
            assessment_code: 'ASM-FLD-01',
            sector: 'HEALTH',
            facility_name: 'Ward 4 District Dispensary',
            damage_level: 'MODERATE',
            is_operational: false,
            estimated_reconstruction_cost: 450000.0,
            verification_status: 'PENDING_VERIFICATION',
            assessor_confidence: 92.0,
            structural_notes: 'Roof tiles collapsed, water inundation 0.6m',
            assessed_at: '2026-11-18T00:00:00Z',
          },
        ]),
      });
    });

    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    // 1. Verify 3rd tab "Field Inspections Verification"
    const verifyTab = page.locator('button:has-text("Field Inspections Verification")');
    await expect(verifyTab).toBeVisible();
    await verifyTab.click();

    // 2. Verify inspection list table and row
    await expect(page.locator('h3:has-text("Field Damage Inspection Verification Pipeline")')).toBeVisible();
    await expect(page.locator('text=Ward 4 District Dispensary')).toBeVisible();
    await expect(page.locator('text=PENDING_VERIFICATION')).toBeVisible();

    // 3. Open certification modal
    const certifyBtn = page.locator('button:has-text("Review & Certify")');
    await expect(certifyBtn).toBeVisible();
    await certifyBtn.click();

    // 4. Verify modal opened
    await expect(page.locator('text=Engineering Assessment Certification Gate')).toBeVisible();
    await expect(page.locator('button:has-text("Commit Decision")')).toBeVisible();
  });
});
