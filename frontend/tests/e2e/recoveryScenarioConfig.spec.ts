/**
 * DIRS Phase 6D-B Milestone 4 Gate 3 — Stage 3
 * Scenario Configuration & Candidate Projects Grid Test Suite
 *
 * Test Inventory Covered:
 * - TC-E2E-08: Scenario Template Loading (Minimal Valid vs Tier-1 Safety Templates)
 * - TC-E2E-09: Planning Horizon Boundary Validation (1 <= T <= 120, Ts safety bounds, error suppression)
 * - TC-E2E-10: Periodic Budget Cent Summation (Uniform apply, cent-exact math, invalid input detection)
 * - TC-E2E-11: Candidate Project Addition Modal (Form validation, ID uniqueness, reactive addition)
 * - TC-E2E-12: Candidate Project Inline Edit (Exact decimal preservation, duration update)
 * - TC-E2E-13: Candidate Project Deletion (Row removal, metric counter updates, empty state fallback)
 * - TC-E2E-14: Candidate Grid Pagination (Page size switching 10/25/50, clean multi-page navigation)
 * - TC-E2E-15: Candidate Grid Exact String Sorting (Numeric decimal cost sort, alphanumeric project ID sort)
 *
 * Traceability:
 * - Architectural Requirements: REQ-05, REQ-06, REQ-07, REQ-08
 * - Runtime Target: Chromium Exclusive
 */

import { test, expect } from '@playwright/test';
import { setupMockAuth } from './fixtures/recoveryMockFixtures';

test.describe('Gate 3 Stage 3: Scenario Configuration & Candidate Projects Grid', () => {

  test.beforeEach(async ({ page }) => {
    // Authenticate as ADMIN with access to /admin/recovery-optimization
    await setupMockAuth(page, 'ADMIN');
    await page.goto('/admin/recovery-optimization');
    await page.waitForURL('**/admin/recovery-optimization');
    await expect(page.getByRole('heading', { name: /Recovery Portfolio Optimization/i })).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-08: Scenario Template Loading
  // --------------------------------------------------------------------------
  test('TC-E2E-08: Scenario template loading populates horizon, duration, and candidate projects', async ({ page }) => {
    // 1. Verify default initial state displays Minimal Valid Recovery Scenario
    const templateBadge = page.locator('span:has-text("Minimal Valid Recovery Scenario")');
    await expect(templateBadge.first()).toBeVisible();

    // 2. Click "Tier-1 Safety Template" button in the catalog strip
    const tier1Button = page.getByRole('button', { name: 'Tier-1 Safety Template' });
    await expect(tier1Button).toBeVisible();
    await tier1Button.click();

    // Verify template indicator updates to Tier-1 Mandatory Safety Scenario
    const tier1Badge = page.locator('span:has-text("Tier-1 Mandatory Safety Scenario")');
    await expect(tier1Badge.first()).toBeVisible();

    // Verify horizon and safety window populated
    const horizonInput = page.locator('input[type="number"][max="120"]');
    await expect(horizonInput).toHaveValue('12');

    const safetyInput = page.locator('input[type="number"][placeholder*="1 .."]');
    await expect(safetyInput).toHaveValue('3');

    // Switch to Candidate Projects tab and verify Tier-1 candidates are loaded
    await page.getByRole('button', { name: /3\. Candidate Projects/i }).click();
    await expect(page.locator('tr:has-text("P-T1-01")')).toBeVisible();
    await expect(page.locator('tr:has-text("TIER-1 SAFETY")')).toBeVisible();

    // 3. Click "Minimal Valid Template" to switch back
    const minimalButton = page.getByRole('button', { name: 'Minimal Valid Template' });
    await minimalButton.click();

    // Verify template indicator updates back
    await expect(page.locator('span:has-text("Minimal Valid Recovery Scenario")').first()).toBeVisible();
    await expect(page.locator('tr:has-text("P-001")')).toBeVisible();
    await expect(page.locator('tr:has-text("P-T1-01")')).toHaveCount(0);
  });

  // --------------------------------------------------------------------------
  // TC-E2E-09: Planning Horizon Boundary Validation
  // --------------------------------------------------------------------------
  test('TC-E2E-09: Planning horizon boundary validation enforces 1 <= T <= 120 and safety constraints', async ({ page }) => {
    // Navigate to Parameters tab
    await page.getByRole('button', { name: /1\. Parameters & Horizon/i }).click();

    const horizonInput = page.locator('input[type="number"][max="120"]');
    await expect(horizonInput).toBeVisible();

    // Verify input constraint bounds
    await expect(horizonInput).toHaveAttribute('min', '1');
    await expect(horizonInput).toHaveAttribute('max', '120');

    // 1. Enter boundary value T=12 (Valid accepted value)
    await horizonInput.fill('12');
    await expect(page.locator('text=Discrete 1-based periods: [1, 12]')).toBeVisible();

    const executeBtn = page.getByRole('button', { name: /Run Optimization Evaluation/i });
    await expect(executeBtn).toBeEnabled();
    await expect(page.locator('text=Scenario Configuration Valid for Optimization')).toBeVisible();

    // 2. Load Tier-1 Template and test safety horizon violation (Ts > T)
    await page.getByRole('button', { name: 'Tier-1 Safety Template' }).click();
    await page.getByRole('button', { name: /1\. Parameters & Horizon/i }).click();

    // Set Horizon to 2 while Max Safety Period Ts is 3
    await horizonInput.fill('2');

    // Constraint invalidation warning must appear
    const issuesContainer = page.locator('div:has-text("Configuration Issues Detected")');
    await expect(issuesContainer.first()).toBeVisible();
    await expect(page.locator('text=exceeds planning horizon T=2')).toBeVisible();

    // Execution button must be disabled
    await expect(executeBtn).toBeDisabled();

    // 3. Clear scenario name to verify required field constraint
    const scenarioNameInput = page.locator('div:has(> label:has-text("Scenario Name")) input');
    await scenarioNameInput.fill('');
    await expect(page.locator('text=Scenario name cannot be empty.')).toBeVisible();
    await expect(executeBtn).toBeDisabled();

    // Restore valid values
    await scenarioNameInput.fill('Rehabilitated Portfolio Scenario');
    await horizonInput.fill('12');
    await expect(executeBtn).toBeEnabled();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-10: Periodic Budget Cent Summation
  // --------------------------------------------------------------------------
  test('TC-E2E-10: Periodic budget cent summation preserves exact monetary decimal arithmetic', async ({ page }) => {
    // Switch to Periodic Budgets tab
    await page.getByRole('button', { name: /2\. Periodic Budgets/i }).click();

    // 1. Test "Reset to Zero"
    const resetZeroBtn = page.getByRole('button', { name: 'Reset to Zero' });
    await resetZeroBtn.click();
    await expect(page.locator('span:has-text("INR 0.00")')).toBeVisible();

    // 2. Test "Apply to All Periods" uniform amount (e.g. 5000000.00 across T=12 -> 60000000.00)
    const uniformInput = page.locator('input.w-36');
    await uniformInput.fill('5000000.00');

    const applyUniformBtn = page.getByRole('button', { name: 'Apply to All Periods' });
    await applyUniformBtn.click();

    // Verify exact summation without floating-point distortion
    await expect(page.locator('span:has-text("INR 60000000.00")')).toBeVisible();

    // 3. Test individual period cent inputs with high-precision decimal addition
    // Period t = 1: add 10000000.50 (exact text-is to avoid matching Period t = 10, 11, 12)
    const period1Input = page.locator('div:has(> div > span:text-is("Period t = 1")) input');
    await period1Input.fill('10000000.50');

    // Period t = 2: add 5000000.25
    const period2Input = page.locator('div:has(> div > span:text-is("Period t = 2")) input');
    await period2Input.fill('5000000.25');

    // 10*5000000 + 10000000.50 + 5000000.25 = 65000000.75
    await expect(page.locator('span:has-text("INR 65000000.75")')).toBeVisible();

    // 4. Test non-conforming / invalid budget input
    await period1Input.fill('invalid_cents');
    await expect(page.locator('text=INVALID (1 period)')).toBeVisible();
    await expect(page.locator('text=Invalid or non-conforming budget values in period(s): t=1')).toBeVisible();

    // Restore valid cent input
    await period1Input.fill('5000000.00');
    await expect(page.locator('span:has-text("INR 60000000.25")')).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-11: Candidate Project Addition Modal
  // --------------------------------------------------------------------------
  test('TC-E2E-11: Candidate project addition modal validates input and reactively adds project', async ({ page }) => {
    // Switch to Candidate Projects tab
    await page.getByRole('button', { name: /3\. Candidate Projects/i }).click();

    // Click "Add Project" button
    const addProjectBtn = page.getByRole('button', { name: 'Add Project' });
    await expect(addProjectBtn).toBeVisible();
    await addProjectBtn.click();

    // Modal dialog must be visible
    await expect(page.getByRole('heading', { name: 'Add Candidate Project' })).toBeVisible();

    // Form inputs
    const projIdInput = page.locator('label:has-text("Project ID")').locator('..').locator('input[type="text"]');
    const projCodeInput = page.locator('label:has-text("Project Code")').locator('..').locator('input[type="text"]');
    const districtInput = page.locator('label:has-text("District ID")').locator('..').locator('input[type="text"]');
    const costInput = page.locator('label:has-text("Estimated Cost")').locator('..').locator('input[type="text"]');
    const durationInput = page.locator('label:has-text("Duration")').locator('..').locator('input[type="number"]');

    // Test validation: Empty fields rejected
    await projIdInput.fill('');
    await page.getByRole('button', { name: 'Save Project' }).click();
    await expect(page.locator('text=Project ID is required.')).toBeVisible();

    // Fill valid new project details
    await projIdInput.fill('P-NEW-99');
    await projCodeInput.fill('WATER-PIPE-RETROFIT');
    await districtInput.fill('DIST-SOUTH');
    await costInput.fill('7500000.00');
    await durationInput.fill('3');

    // Submit valid project form
    await page.getByRole('button', { name: 'Save Project' }).click();

    // Modal must close
    await expect(page.getByRole('heading', { name: 'Add Candidate Project' })).not.toBeVisible();

    // Candidate grid must reactively render the new project row
    const newRow = page.locator('tr:has-text("P-NEW-99")');
    await expect(newRow).toBeVisible();
    await expect(newRow).toContainText('DIST-SOUTH');
    await expect(newRow).toContainText('7500000.00');
    await expect(newRow).toContainText('3 periods');
  });

  // --------------------------------------------------------------------------
  // TC-E2E-12: Candidate Project Inline Edit
  // --------------------------------------------------------------------------
  test('TC-E2E-12: Candidate project inline edit updates cost and duration preserving decimal precision', async ({ page }) => {
    // Switch to Candidate Projects tab
    await page.getByRole('button', { name: /3\. Candidate Projects/i }).click();

    // Locate initial row P-001
    const p1Row = page.locator('tr:has-text("P-001")');
    await expect(p1Row).toBeVisible();

    // Click edit button for P-001
    const editBtn = p1Row.locator('button[title="Edit candidate"]');
    await editBtn.click();

    // Modal dialog must be visible for P-001
    await expect(page.getByRole('heading', { name: 'Edit Project: P-001' })).toBeVisible();

    // Project ID field must be disabled during edit
    const projIdInput = page.locator('label:has-text("Project ID")').locator('..').locator('input[type="text"]');
    await expect(projIdInput).toBeDisabled();

    // Modify Estimated Cost and Duration
    const costInput = page.locator('label:has-text("Estimated Cost")').locator('..').locator('input[type="text"]');
    await costInput.fill('9876543.21');

    const durationInput = page.locator('label:has-text("Duration")').locator('..').locator('input[type="number"]');
    await durationInput.fill('4');

    // Save modifications
    await page.getByRole('button', { name: 'Save Project' }).click();
    await expect(page.getByRole('heading', { name: 'Edit Project: P-001' })).not.toBeVisible();

    // Assert row reactively reflects updated exact decimal cost and duration
    await expect(p1Row).toContainText('9876543.21');
    await expect(p1Row).toContainText('4 periods');
  });

  // --------------------------------------------------------------------------
  // TC-E2E-13: Candidate Project Deletion
  // --------------------------------------------------------------------------
  test('TC-E2E-13: Candidate project deletion removes row and renders empty state fallback when zero', async ({ page }) => {
    // Switch to Candidate Projects tab
    await page.getByRole('button', { name: /3\. Candidate Projects/i }).click();

    // P-001 row is initially present
    const p1Row = page.locator('tr:has-text("P-001")');
    await expect(p1Row).toBeVisible();

    // Click Delete candidate button
    const deleteBtn = p1Row.locator('button[title="Delete candidate"]');
    await deleteBtn.click();

    // Row must be removed
    await expect(page.locator('tr:has-text("P-001")')).toHaveCount(0);

    // Empty state container must render
    await expect(page.locator('text=No Candidate Projects Configured')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create First Candidate' })).toBeVisible();

    // Optimization execution must be disabled when 0 candidates exist
    const executeBtn = page.getByRole('button', { name: /Run Optimization Evaluation/i });
    await expect(executeBtn).toBeDisabled();
    await expect(page.locator('text=Scenario must contain at least 1 candidate project.')).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-14: Candidate Grid Pagination
  // --------------------------------------------------------------------------
  test('TC-E2E-14: Candidate grid pagination supports page size selection and multi-page navigation', async ({ page }) => {
    // Switch to Candidate Projects tab
    await page.getByRole('button', { name: /3\. Candidate Projects/i }).click();

    // Add candidates to exceed page size 10 (total 11 candidates)
    for (let i = 2; i <= 11; i++) {
      const addBtn = page.getByRole('button', { name: 'Add Project' });
      await addBtn.click();
      const projIdInput = page.locator('label:has-text("Project ID")').locator('..').locator('input[type="text"]');
      await projIdInput.fill(`P-${String(i).padStart(3, '0')}`);
      await page.getByRole('button', { name: 'Save Project' }).click();
    }

    // Verify pagination toolbar displays Page 1 of 2
    await expect(page.locator('text=Showing 1 to 10 of 11 projects')).toBeVisible();
    await expect(page.locator('text=Page 1 of 2')).toBeVisible();

    // Click Next Page button
    const nextBtn = page.locator('button:has(svg.lucide-chevron-right)');
    await expect(nextBtn).toBeEnabled();
    await nextBtn.click();

    // Verify Page 2 displays the 11th project
    await expect(page.locator('text=Showing 11 to 11 of 11 projects')).toBeVisible();
    await expect(page.locator('text=Page 2 of 2')).toBeVisible();
    await expect(page.locator('tr:has-text("P-011")')).toBeVisible();

    // Click Previous Page button
    const prevBtn = page.locator('button:has(svg.lucide-chevron-left)');
    await expect(prevBtn).toBeEnabled();
    await prevBtn.click();
    await expect(page.locator('text=Showing 1 to 10 of 11 projects')).toBeVisible();

    // Switch Page Size dropdown to 25
    const pageSizeSelect = page.locator('div:has-text("Rows:")').locator('select');
    await pageSizeSelect.selectOption('25');

    // All 11 projects now fit on a single page
    await expect(page.locator('text=Showing 1 to 11 of 11 projects')).toBeVisible();
    await expect(page.locator('text=Page 1 of 1')).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-15: Candidate Grid Exact String Sorting
  // --------------------------------------------------------------------------
  test('TC-E2E-15: Candidate grid exact string sorting orders by cost and project ID without numeric distortion', async ({ page }) => {
    // Load Tier-1 template which has 2 distinct projects: P-T1-01 (12000000.00) and P-GEN-02 (4000000.00)
    await page.getByRole('button', { name: 'Tier-1 Safety Template' }).click();
    await page.getByRole('button', { name: /3\. Candidate Projects/i }).click();

    // Add a 3rd project with cost 15000000.00 to test three-way sort
    const addBtn = page.getByRole('button', { name: 'Add Project' });
    await addBtn.click();
    await page.locator('label:has-text("Project ID")').locator('..').locator('input[type="text"]').fill('P-EXTRA-03');
    await page.locator('label:has-text("Estimated Cost")').locator('..').locator('input[type="text"]').fill('15000000.00');
    await page.getByRole('button', { name: 'Save Project' }).click();

    // 1. Sort by Estimated Cost: Click "Est. Cost" column header
    const costHeader = page.locator('th:has-text("Est. Cost")');
    await costHeader.click();

    // In ascending sort: lowest cost (4000000.00) must appear in the first table row
    const firstRowCostAsc = page.locator('tbody tr').first().locator('td').nth(2);
    await expect(firstRowCostAsc).toHaveText('4000000.00');

    // Click cost header again for descending sort
    await costHeader.click();
    const firstRowCostDesc = page.locator('tbody tr').first().locator('td').nth(2);
    await expect(firstRowCostDesc).toHaveText('15000000.00');

    // 2. Sort by Project ID: Click "Project ID / Code" column header
    const idHeader = page.locator('th:has-text("Project ID / Code")');
    await idHeader.click();

    // Ascending: P-EXTRA-03 < P-GEN-02 < P-T1-01
    const firstRowIdAsc = page.locator('tbody tr').first().locator('td').first();
    await expect(firstRowIdAsc).toContainText('P-EXTRA-03');

    // Click again for descending: P-T1-01 is first
    await idHeader.click();
    const firstRowIdDesc = page.locator('tbody tr').first().locator('td').first();
    await expect(firstRowIdDesc).toContainText('P-T1-01');
  });

});
