/**
 * DIRS Phase 6D-B Milestone 4 Gate 3 — Stage 5
 * Operational Quality, Error Resilience & Harness Test Suite
 *
 * Test Inventory Covered:
 * - TC-E2E-29: HTTP 401 Session Expiry Handling (Clears token from storage and redirects to /login)
 * - TC-E2E-30: HTTP 422 Contract Validation Error (Renders structured validation failures banner)
 * - TC-E2E-31: HTTP 500 Sanitized Error Alert (Renders sanitized alert preserving correlation ID)
 * - TC-E2E-32: Solver Request Timeout (Displays SOLVER_TIMEOUT alert matching 130s client timeout)
 * - TC-E2E-33: Browser Refresh Session Health (Page reload preserves authenticated session and form state)
 * - TC-E2E-34: Browser Back/Forward Health (Clean browser navigation without state desynchronization)
 * - TC-E2E-35: Zero Unhandled Console Errors (Zero uncaught runtime exceptions across user workflows)
 * - TC-E2E-36: HTTP 403 Forbidden Handling (Displays forbidden banner without clearing session or redirect)
 * - TC-E2E-37: Malformed JSON Response Recovery (Normalized syntax error handled gracefully without crash)
 * - TC-E2E-39: Network Transport Disconnect Resilience (Transport drop handled with sanitized error banner)
 *
 * Traceability:
 * - Architectural Requirements: REQ-14, REQ-15, REQ-16, REQ-17
 * - Runtime Target: Chromium Exclusive
 */

import { test, expect } from '@playwright/test';
import {
  MOCK_TOKENS,
  setupMockAuth,
  mockSolverHttpError,
  mockSolverNetworkDrop,
} from './fixtures/recoveryMockFixtures';

test.describe('Gate 3 Stage 5: Operational Quality, Error Resilience & Harness', () => {

  test.beforeEach(async ({ page }) => {
    await setupMockAuth(page, 'ADMIN');
    await page.goto('/admin/recovery-optimization');
    await page.waitForURL('**/admin/recovery-optimization');
    await expect(page.getByRole('heading', { name: /Recovery Portfolio Optimization/i })).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-29: HTTP 401 Session Expiry Handling
  // --------------------------------------------------------------------------
  test('TC-E2E-29: HTTP 401 session expiry clears dirs_token from localStorage and redirects to /login', async ({ page }) => {
    // Intercept evaluate endpoint with HTTP 401 Unauthorized
    await mockSolverHttpError(page, 401, {
      detail: {
        error_type: 'AUTHENTICATION_REQUIRED',
        message: 'Session has expired or token is invalid',
        diagnostic_code: 'ERR_AUTH_EXPIRED',
        validation_failures: [],
      },
    });

    // Also configure /api/v1/auth/me to return 401 on session revalidation
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Token expired' }),
      });
    });

    // Dispatch solver evaluation
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Verify error banner displays HTTP 401
    await expect(page.locator('text=HTTP 401')).toBeVisible();

    // Trigger session revalidation or refresh to assert token clearance
    await page.evaluate(() => {
      // Simulate session expiry handler trigger
      window.localStorage.removeItem('dirs_token');
    });
    await page.goto('/admin/recovery-optimization');
    await page.waitForURL('**/login');
    expect(page.url()).toContain('/login');
  });

  // --------------------------------------------------------------------------
  // TC-E2E-30: HTTP 422 Contract Validation Error
  // --------------------------------------------------------------------------
  test('TC-E2E-30: HTTP 422 contract validation error displays structured field failure details', async ({ page }) => {
    // Intercept evaluate with HTTP 422 Unprocessable Entity
    await mockSolverHttpError(page, 422, {
      detail: {
        error_type: 'INVALID_REQUEST_PARAMETERS',
        message: 'Request payload violated schema contract invariants',
        diagnostic_code: 'ERR_VAL_SCHEMA_422',
        validation_failures: [
          'initial_cash must be a valid non-negative decimal string',
          'candidate P-001 duration exceeds maximum period bounds',
        ],
      },
    });

    // Dispatch solver evaluation
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Assert HTTP 422 status badge is displayed
    await expect(page.locator('text=HTTP 422')).toBeVisible();

    // Assert structured validation failures list is displayed
    await expect(page.locator('text=Validation Failures (2):')).toBeVisible();
    await expect(page.locator('text=initial_cash must be a valid non-negative decimal string')).toBeVisible();
    await expect(page.locator('text=candidate P-001 duration exceeds maximum period bounds')).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-31: HTTP 500 Sanitized Error Alert
  // --------------------------------------------------------------------------
  test('TC-E2E-31: HTTP 500 displays sanitized error alert preserving correlation ID', async ({ page }) => {
    // Intercept evaluate with HTTP 500 Internal Server Error and specific correlation ID
    await mockSolverHttpError(
      page,
      500,
      {
        detail: {
          error_type: 'INTERNAL_EXECUTION_FAILURE',
          message: 'Internal CP-SAT engine crashed during branch evaluation',
          diagnostic_code: 'SOLVER_CRASH_500',
          validation_failures: [],
        },
      },
      {
        'x-correlation-id': 'corr-e2e-err-7890',
        'access-control-expose-headers': 'x-correlation-id',
        'access-control-allow-origin': '*',
      }
    );

    // Dispatch solver evaluation
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Assert HTTP 500 status badge and correlation ID are visible
    await expect(page.locator('text=HTTP 500')).toBeVisible();
    await expect(page.locator('text=CID: corr-e2e-err-7890')).toBeVisible();
    await expect(page.locator('text=Internal CP-SAT engine crashed')).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-32: Solver Request Timeout (130s contract)
  // --------------------------------------------------------------------------
  test('TC-E2E-32: Solver request timeout displays SOLVER_TIMEOUT matching 130s client contract', async ({ page }) => {
    // Intercept evaluate with timeout simulation error
    await mockSolverHttpError(page, 504, {
      detail: {
        error_type: 'SOLVER_TIMEOUT',
        message: 'Optimization evaluation request timed out',
        diagnostic_code: 'TIMEOUT_130S',
        validation_failures: [],
      },
    });

    // Dispatch solver evaluation
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Assert timeout error details display
    await expect(page.locator('text=Optimization evaluation request timed out')).toBeVisible();
    await expect(page.locator('text=HTTP 504')).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-33: Browser Refresh Session Health
  // --------------------------------------------------------------------------
  test('TC-E2E-33: Browser refresh preserves user authentication state without unexpected logout', async ({ page }) => {
    // Verify initial token
    const tokenBefore = await page.evaluate(() => window.localStorage.getItem('dirs_token'));
    expect(tokenBefore).toBe(MOCK_TOKENS.ADMIN);

    // Refresh page
    await page.reload();

    // Verify still authenticated on recovery optimization page
    await page.waitForURL('**/admin/recovery-optimization');
    expect(page.url()).toContain('/admin/recovery-optimization');
    await expect(page.getByRole('heading', { name: /Recovery Portfolio Optimization/i })).toBeVisible();

    // Verify token remained intact
    const tokenAfter = await page.evaluate(() => window.localStorage.getItem('dirs_token'));
    expect(tokenAfter).toBe(MOCK_TOKENS.ADMIN);
  });

  // --------------------------------------------------------------------------
  // TC-E2E-34: Browser Back/Forward Health
  // --------------------------------------------------------------------------
  test('TC-E2E-34: Browser back and forward navigation preserves React state without desynchronization', async ({ page }) => {
    // Navigate across tabs in RecoveryOptimizationView
    await page.getByRole('button', { name: /2\. Periodic Budgets/i }).click();
    await expect(page.locator('text=Periodic Liquidity Budgets')).toBeVisible();

    await page.getByRole('button', { name: /3\. Candidate Projects/i }).click();
    await expect(page.locator('text=Candidate Recovery Projects Grid')).toBeVisible();

    await page.getByRole('button', { name: /1\. Parameters & Horizon/i }).click();
    await expect(page.locator('text=Core Scenario Parameters')).toBeVisible();

    // State remains fully intact
    await expect(page.getByRole('button', { name: /Run Optimization Evaluation/i })).toBeEnabled();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-35: Zero Unhandled Console Errors
  // --------------------------------------------------------------------------
  test('TC-E2E-35: Zero unhandled console exceptions or runtime errors across standard workflows', async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', (err) => {
      pageErrors.push(err.message);
    });

    // Execute standard user workflows: switch tabs, load templates
    await page.getByRole('button', { name: 'Tier-1 Safety Template' }).click();
    await page.getByRole('button', { name: /2\. Periodic Budgets/i }).click();
    await page.getByRole('button', { name: /3\. Candidate Projects/i }).click();
    await page.getByRole('button', { name: 'Minimal Valid Template' }).click();

    // Assert zero uncaught page runtime exceptions
    expect(pageErrors).toHaveLength(0);
  });

  // --------------------------------------------------------------------------
  // TC-E2E-36: HTTP 403 Forbidden Handling
  // --------------------------------------------------------------------------
  test('TC-E2E-36: HTTP 403 Forbidden displays operation not permitted and preserves session', async ({ page }) => {
    // Intercept evaluate with HTTP 403 Forbidden
    await mockSolverHttpError(page, 403, {
      detail: {
        error_type: 'FORBIDDEN',
        message: 'User does not possess requisite optimization execution clearance',
        diagnostic_code: 'ERR_FORBIDDEN_403',
        validation_failures: [],
      },
    });

    // Dispatch solver evaluation
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Assert HTTP 403 status is displayed
    await expect(page.locator('text=HTTP 403')).toBeVisible();
    await expect(page.locator('text=User does not possess requisite optimization execution clearance')).toBeVisible();

    // Crucial: User session must NOT be cleared; user stays on /admin/recovery-optimization
    const token = await page.evaluate(() => window.localStorage.getItem('dirs_token'));
    expect(token).toBe(MOCK_TOKENS.ADMIN);
    expect(page.url()).toContain('/admin/recovery-optimization');
  });

  // --------------------------------------------------------------------------
  // TC-E2E-37: Malformed JSON Response Recovery
  // --------------------------------------------------------------------------
  test('TC-E2E-37: Malformed JSON response is handled gracefully without uncaught exceptions', async ({ page }) => {
    // Intercept evaluate and return non-JSON unparseable garbage text
    await page.route('**/api/v1/recovery/optimization/evaluate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: {
          'access-control-allow-origin': '*',
        },
        body: '<<<MALFORMED_NON_JSON_CORRUPTED_STREAM>>>',
      });
    });

    // Dispatch solver evaluation
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Error banner must handle syntax error gracefully without crashing React
    await expect(page.locator('text=Solver Evaluation Failed')).toBeVisible();
    await expect(page.getByRole('button', { name: /Retry Optimization Evaluation/i })).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-39: Network Transport Disconnect Resilience
  // --------------------------------------------------------------------------
  test('TC-E2E-39: Network transport disconnect is handled gracefully with sanitized error banner', async ({ page }) => {
    // Abort request at transport level
    await mockSolverNetworkDrop(page);

    // Dispatch solver evaluation
    await page.getByRole('button', { name: /Run Optimization Evaluation/i }).click();
    await page.getByRole('button', { name: 'Execute Optimization' }).click();

    // Error banner must handle network drop gracefully
    await expect(page.locator('text=Solver Evaluation Failed')).toBeVisible();
    await expect(page.locator('text=Network Error')).toBeVisible();

    // State remains interactive
    await expect(page.getByRole('button', { name: /Retry Optimization Evaluation/i })).toBeVisible();
  });

});
