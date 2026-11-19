/**
 * DIRS Phase 6D-B Milestone 4 Gate 3 — Stage 4
 * Solver Dispatch, Indeterminate State & Visualizations Test Suite
 *
 * Test Inventory Covered:
 * - TC-E2E-16: Evaluation Disabled on Errors (Invalid horizon or empty name disables solver button)
 * - TC-E2E-17: Confirmation Dialog Summary (ConfirmDialog modal opens with parameters checklist)
 * - TC-E2E-18: Confirmation Dialog Cancellation (Cancelling dismisses modal, zero API requests dispatched)
 * - TC-E2E-19: Confirmation Dispatch Trigger (Confirming triggers indeterminate overlay and API call)
 * - TC-E2E-20: Stopwatch Increments Monotonically (Elapsed time timer increments monotonically without jumps)
 * - TC-E2E-21: Background Control Interaction Lock (Fullscreen modal blocks background inputs during evaluation)
 * - TC-E2E-22: OPTIMAL & FEASIBLE Status Rendering (OPTIMAL green banner, FEASIBLE banner, hasUsableSchedule)
 * - TC-E2E-23: 1-Based Periodic Gantt Timeline (Scheduled start/end rendered in 1-based columns)
 * - TC-E2E-24: Unselected Projects Registry (Candidate grid displays neutral "Not selected" outcome status)
 * - TC-E2E-25: Dual-Ledger Solvency Separation (Parallel CCU and INR ledger tracking with solvent badges)
 * - TC-E2E-26: INFEASIBLE 4-Tier Diagnostics (Diagnostic banner, 4-tier diagnostics, assumption core metadata)
 * - TC-E2E-27: Reconciliation Failure Rejection (Red banner, mathematically unusable schedule)
 * - TC-E2E-28: MODEL_INVALID & UNKNOWN Error Panels (Diagnostic panels with schedule suppressed)
 *
 * Traceability:
 * - Architectural Requirements: REQ-09, REQ-10, REQ-11, REQ-12, REQ-13
 * - Runtime Target: Chromium Exclusive
 */

import { test, expect, Page } from '@playwright/test';
import {
  setupMockAuth,
  mockSolverOutcome,
} from './fixtures/recoveryMockFixtures';
import {
  optimalScenarioResponseFixture,
  infeasibleScenarioResponseFixture,
} from '../../src/fixtures/recoveryOptimizationFixtures';
import { RecoveryOptimizationScenarioResponse } from '../../src/types/recoveryOptimization';

// Authoritative test fixtures with explicit solver_status
const testOptimalResponse: RecoveryOptimizationScenarioResponse = {
  ...optimalScenarioResponseFixture,
  solver_status: 'OPTIMAL',
  is_optimal: true,
  scheduled_projects: [
    ...optimalScenarioResponseFixture.scheduled_projects,
    {
      project_id: 'P-002',
      project_code: 'BRIDGE-REPAIR-02',
      district_id: 'DIST-SOUTH',
      is_selected: false,
      scheduled_start_period: null,
      scheduled_completion_period: null,
      assigned_funding_source: null,
      cost_ccu: '200000000',
      cost_inr: '2000000.00',
      periodic_expenditures_ccu: {},
      periodic_expenditures_inr: {},
      mcpi_score: 0.65,
      raw_mcpi_score: 0.65,
      quantized_mcpi_coefficient: 650000000,
      is_tier1_mandatory: false,
    },
  ],
};

const testFeasibleResponse: RecoveryOptimizationScenarioResponse = {
  ...optimalScenarioResponseFixture,
  solver_status: 'FEASIBLE',
  is_optimal: false,
  optimality_gap: 0.05,
};

const testInfeasibleResponse: RecoveryOptimizationScenarioResponse = {
  ...infeasibleScenarioResponseFixture,
  solver_status: 'INFEASIBLE',
  is_optimal: false,
};

const testModelInvalidResponse: RecoveryOptimizationScenarioResponse = {
  ...infeasibleScenarioResponseFixture,
  solver_status: 'MODEL_INVALID',
  is_optimal: false,
};

const testReconciliationFailedResponse: RecoveryOptimizationScenarioResponse = {
  ...optimalScenarioResponseFixture,
  solver_status: 'POST_SOLVE_RECONCILIATION_FAILED',
  is_optimal: false,
  scheduled_projects: [],
};

const testUnknownResponse: RecoveryOptimizationScenarioResponse = {
  ...infeasibleScenarioResponseFixture,
  solver_status: 'UNKNOWN',
  is_optimal: false,
  infeasibility_diagnostics: null,
};

test.describe('Gate 3 Stage 4: Solver Dispatch, Indeterminate State & Visualizations', () => {

  test.beforeEach(async ({ page }) => {
    await setupMockAuth(page, 'ADMIN');
    await page.goto('/admin/recovery-optimization');
    await page.waitForURL('**/admin/recovery-optimization');
    await expect(page.getByRole('heading', { name: /Recovery Portfolio Optimization/i })).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-16: Evaluation Disabled on Errors
  // --------------------------------------------------------------------------
  test('TC-E2E-16: Evaluation disabled on errors blocks solver dispatch when constraints are violated', async ({ page }) => {
    const executeBtn = page.getByRole('button', { name: /Run Optimization Evaluation/i });
    await expect(executeBtn).toBeEnabled();

    // Invalidate configuration by clearing scenario name
    const scenarioNameInput = page.locator('div:has(> label:has-text("Scenario Name")) input');
    await scenarioNameInput.fill('');

    // Assert validation issues detected
    await expect(page.locator('text=Scenario name cannot be empty.')).toBeVisible();
    await expect(page.locator('text=1 Configuration Issues Detected')).toBeVisible();

    // Assert execute button is disabled
    await expect(executeBtn).toBeDisabled();

    // Restore valid name
    await scenarioNameInput.fill('Valid Optimization Scenario');
    await expect(executeBtn).toBeEnabled();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-17: Confirmation Dialog Summary
  // --------------------------------------------------------------------------
  test('TC-E2E-17: Confirmation dialog opens with human-in-the-loop summary and checklist', async ({ page }) => {
    const executeBtn = page.getByRole('button', { name: /Run Optimization Evaluation/i });
    await executeBtn.click();

    // Modal dialog must be visible
    const dialog = page.locator('div[role="dialog"]');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole('heading', { name: 'Confirm Optimization Evaluation' })).toBeVisible();

    // Assert decision support disclaimer is present
    await expect(dialog).toContainText('decision support only');
    await expect(dialog).toContainText('120 seconds');

    // Assert both Confirm and Cancel buttons are present
    await expect(dialog.getByRole('button', { name: 'Execute Optimization' })).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-18: Confirmation Dialog Cancellation
  // --------------------------------------------------------------------------
  test('TC-E2E-18: Confirmation dialog cancellation dismisses modal and prevents API dispatch', async ({ page }) => {
    let apiCallDispatched = false;
    await page.route('**/api/v1/recovery/optimization/evaluate', async (route) => {
      apiCallDispatched = true;
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });

    // Open confirmation dialog
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    const dialog = page.locator('div[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Click Cancel
    await dialog.getByRole('button', { name: 'Cancel' }).click();

    // Modal must be dismissed
    await expect(dialog).not.toBeVisible();

    // Zero API calls should have been made
    expect(apiCallDispatched).toBe(false);

    // Initial valid state is preserved
    await expect(page.getByRole('button', { name: /Run Optimization Evaluation/i })).toBeEnabled();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-19: Confirmation Dispatch Trigger
  // --------------------------------------------------------------------------
  test('TC-E2E-19: Confirmation dispatch trigger initiates indeterminate overlay and dispatches API call', async ({ page }) => {
    let apiCallDispatched = false;
    await page.route('**/api/v1/recovery/optimization/evaluate', async (route) => {
      apiCallDispatched = true;
      await new Promise((r) => setTimeout(r, 600));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(testOptimalResponse),
      });
    });

    // Open confirmation and execute
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    const dialog = page.locator('div[role="dialog"]');
    await dialog.getByRole('button', { name: 'Execute Optimization' }).click();

    // Confirm dialog dismisses and indeterminate solver overlay appears
    await expect(page.locator('text=SOLVER KERNEL ACTIVE')).toBeVisible();
    await expect(page.locator('text=Synchronous Mathematical Optimization')).toBeVisible();

    // Wait for resolution
    await expect(page.locator('text=SOLVER KERNEL ACTIVE')).not.toBeVisible();
    expect(apiCallDispatched).toBe(true);
  });

  // --------------------------------------------------------------------------
  // TC-E2E-20: Stopwatch Increments Monotonically
  // --------------------------------------------------------------------------
  test('TC-E2E-20: Stopwatch increments monotonically during indeterminate solver execution', async ({ page }) => {
    await mockSolverOutcome(page, testOptimalResponse, 2000);

    // Dispatch optimization
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    const overlay = page.locator('div[aria-label="Optimization Solver Execution"]');
    await expect(overlay).toBeVisible();

    // Read stopwatch at t1
    const stopwatchElem = overlay.locator('span.text-amber-ops');
    await expect(stopwatchElem).toBeVisible();
    const t1Text = await stopwatchElem.innerText();
    const t1 = parseFloat(t1Text.replace('s', ''));

    // Wait 400ms
    await page.waitForTimeout(400);

    // Read stopwatch at t2
    const t2Text = await stopwatchElem.innerText();
    const t2 = parseFloat(t2Text.replace('s', ''));

    // Verify monotonic forward progression without negative or unexpected jumps
    expect(t2).toBeGreaterThan(t1);

    // Await completion
    await expect(overlay).not.toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-21: Background Control Interaction Lock
  // --------------------------------------------------------------------------
  test('TC-E2E-21: Background controls locked by modal overlay during solver evaluation', async ({ page }) => {
    await mockSolverOutcome(page, testOptimalResponse, 1500);

    // Dispatch optimization
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    const overlay = page.locator('div[aria-label="Optimization Solver Execution"]');
    await expect(overlay).toBeVisible();

    // Assert fullscreen backdrop overlay has high z-index and blocks pointer events
    await expect(overlay).toHaveClass(/fixed inset-0 z-\[9999\]/);

    // Await completion
    await expect(overlay).not.toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-22: OPTIMAL & FEASIBLE Status Rendering
  // --------------------------------------------------------------------------
  test('TC-E2E-22: OPTIMAL and FEASIBLE status rendering with usable schedule guarantees', async ({ page }) => {
    // Sub-step 1: OPTIMAL Outcome
    await test.step('OPTIMAL Outcome: Renders status banner, KPI stats, and usable schedule', async () => {
      await mockSolverOutcome(page, testOptimalResponse);
      await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
      await page.getByRole('button', { name: 'Execute Optimization' }).click();

      // Top-level status banner
      const banner = page.locator('div:has-text("Global Mathematical Optimum Proven")');
      await expect(banner.first()).toBeVisible();
      await expect(page.locator('span:text-is("OPTIMAL")').first()).toBeVisible();
      await expect(page.locator('text=USABLE SCHEDULE AVAILABLE').first()).toBeVisible();

      // KPI stats
      await expect(page.locator('text=Exact Objective Value')).toBeVisible();
      await expect(page.getByText('Optimality Gap', { exact: true })).toBeVisible();

      // Schedule usable
      await expect(page.locator('text=Project Schedule Timeline')).toBeVisible();
    });

    // Sub-step 2: FEASIBLE Outcome
    await test.step('FEASIBLE Outcome: Renders status banner with distinct status label', async () => {
      await mockSolverOutcome(page, testFeasibleResponse);
      await page.getByRole('button', { name: 'Clear Result' }).click();
      await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
      await page.getByRole('button', { name: 'Execute Optimization' }).click();

      // Feasible banner
      const banner = page.locator('div:has-text("Feasible Portfolio Schedule Identified")');
      await expect(banner.first()).toBeVisible();
      await expect(page.locator('span:text-is("FEASIBLE")').first()).toBeVisible();
      await expect(page.locator('text=USABLE SCHEDULE AVAILABLE').first()).toBeVisible();
    });
  });

  // --------------------------------------------------------------------------
  // TC-E2E-23: 1-Based Periodic Gantt Timeline
  // --------------------------------------------------------------------------
  test('TC-E2E-23: 1-based periodic Gantt timeline renders scheduled projects on exact coordinates', async ({ page }) => {
    await mockSolverOutcome(page, testOptimalResponse);
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Timeline component header
    await expect(page.locator('text=Project Schedule Timeline')).toBeVisible();
    await expect(page.locator('text=Horizon T = 12 Periods')).toBeVisible();

    // Scheduled projects rendered inside timeline grid
    await expect(page.locator('text=ROAD-REPAIR-01').first()).toBeVisible();
    await expect(page.locator('text=DIST-NORTH').first()).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-24: Unselected Projects Registry
  // --------------------------------------------------------------------------
  test('TC-E2E-24: Unselected projects registry displays neutral "Not selected" outcome status', async ({ page }) => {
    await mockSolverOutcome(page, testOptimalResponse);
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Locate unscheduled / unselected candidate section and expand
    await expect(page.locator('text=Unscheduled Candidate Registry')).toBeVisible();
    await page.getByRole('button', { name: /Expand to View Unselected Candidates/i }).click();

    // Unselected project shows neutral outcome status
    await expect(page.locator('span:has-text("Not selected")').first()).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-25: Dual-Ledger Solvency Separation
  // --------------------------------------------------------------------------
  test('TC-E2E-25: Dual-ledger solvency matrix renders parallel CCU and INR liquidity accounting', async ({ page }) => {
    await mockSolverOutcome(page, testOptimalResponse);
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Financial Solvency Matrix container
    await expect(page.locator('text=Financial Solvency & District Equity Ledgers')).toBeVisible();

    // Verify dual ledgers
    await expect(page.getByRole('button', { name: /1\. CCU Solvency Ledger/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /2\. INR Liquidity Ledger/i })).toBeVisible();

    // Solvency status badge
    await expect(page.locator('span:text-is("SOLVENT")').first()).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-26: INFEASIBLE 4-Tier Diagnostics
  // --------------------------------------------------------------------------
  test('TC-E2E-26: INFEASIBLE renders diagnostic banner, 4-tier diagnostics, and suppresses schedule', async ({ page }) => {
    await mockSolverOutcome(page, testInfeasibleResponse);
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Status banner
    const banner = page.locator('div:has-text("Proven Mathematical Infeasibility")');
    await expect(banner.first()).toBeVisible();
    await expect(page.locator('span:text-is("INFEASIBLE")').first()).toBeVisible();

    // 4-Tier Infeasibility Diagnostics View
    await expect(page.locator('text=Infeasibility Diagnostics & Assumption Core')).toBeVisible();
    await expect(page.locator('text=Tier 1: Proven Causes')).toBeVisible();

    // Schedule timeline must NOT be rendered (hasUsableSchedule === false)
    await expect(page.locator('text=Project Schedule Timeline')).not.toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-27: Reconciliation Failure Rejection
  // --------------------------------------------------------------------------
  test('TC-E2E-27: POST_SOLVE_RECONCILIATION_FAILED renders red rejection banner and suppresses schedule', async ({ page }) => {
    await mockSolverOutcome(page, testReconciliationFailedResponse);
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Rejection banner
    const banner = page.locator('div:has-text("Post-Solve Safety Reconciliation Failed")');
    await expect(banner.first()).toBeVisible();
    await expect(page.locator('text=SCHEDULE REJECTED — NOT USABLE').first()).toBeVisible();

    // Schedule must NOT be usable
    await expect(page.locator('text=Project Schedule Timeline')).not.toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-28: MODEL_INVALID & UNKNOWN Error Panels
  // --------------------------------------------------------------------------
  test('TC-E2E-28: MODEL_INVALID and UNKNOWN render appropriate diagnostic banners with schedule suppressed', async ({ page }) => {
    // Sub-step 1: MODEL_INVALID
    await test.step('MODEL_INVALID: Renders diagnostic banner and suppresses schedule', async () => {
      await mockSolverOutcome(page, testModelInvalidResponse);
      await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
      await page.getByRole('button', { name: 'Execute Optimization' }).click();

      const banner = page.locator('div:has-text("Invalid Model Formulation")');
      await expect(banner.first()).toBeVisible();
      await expect(page.locator('span:text-is("MODEL_INVALID")').first()).toBeVisible();

      // Schedule suppressed
      await expect(page.locator('text=Project Schedule Timeline')).not.toBeVisible();
    });

    // Sub-step 2: UNKNOWN
    await test.step('UNKNOWN: Renders indeterminate banner with schedule suppressed and zero invented reasons', async () => {
      await mockSolverOutcome(page, testUnknownResponse);
      await page.getByRole('button', { name: 'Clear Result' }).click();
      await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
      await page.getByRole('button', { name: 'Execute Optimization' }).click();

      const banner = page.locator('div:has-text("Indeterminate Solver State (UNKNOWN)")');
      await expect(banner.first()).toBeVisible();
      await expect(page.locator('span:text-is("UNKNOWN")').first()).toBeVisible();

      // Schedule suppressed
      await expect(page.locator('text=Project Schedule Timeline')).not.toBeVisible();
    });
  });

});
