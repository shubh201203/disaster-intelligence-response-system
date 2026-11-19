/**
 * DIRS Phase 6D-B Milestone 4 Gate 3 — Stage 2
 * Authentication, Route Guards & Least Privilege Test Suite
 *
 * Test Inventory Covered:
 * - TC-E2E-01: Unauthenticated Access Redirect (direct visit /admin/recovery-optimization -> /login)
 * - TC-E2E-02: Valid ADMIN Login & Routing (submit credentials -> /admin/recovery-optimization)
 * - TC-E2E-03: ADMIN Intercepted from /admin (redirects to /admin/recovery-optimization)
 * - TC-E2E-04: ADMIN Intercepted from /admin/simulation (redirects to /admin/recovery-optimization)
 * - TC-E2E-05: GOVT Super-Access to Admin Routes (/admin, /admin/simulation, /admin/recovery-optimization)
 * - TC-E2E-06: Sidebar Role Badge & Navigation (amber ADMIN badge, only Recovery Optimization link)
 * - TC-E2E-07: User Logout Session Cleared (localStorage dirs_token cleared -> /login)
 * - TC-E2E-38: Parameterized Non-Admin Route-Denial Matrix (3 roles x 3 routes = 9 combinations -> /citizen)
 *
 * Traceability:
 * - Architectural Requirements: REQ-01, REQ-02, REQ-03, REQ-04, REQ-14, REQ-15, REQ-16
 * - Runtime Target: Chromium Exclusive
 */

import { test, expect, Page } from '@playwright/test';
import {
  MOCK_USERS,
  MOCK_TOKENS,
  setupMockAuth,
  setupMockLogin,
} from './fixtures/recoveryMockFixtures';

/**
 * Configure auxiliary mock routes to prevent unhandled network requests
 * when administrative or citizen dashboards mount their data queries.
 */
async function setupAuxiliaryApiMocks(page: Page): Promise<void> {
  await page.route('**/api/v1/incidents**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/api/v1/alerts**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/api/v1/shelters**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/api/v1/analytics/summary**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        active_disasters: 0,
        critical_incidents: 0,
        people_affected: 0,
        operational_shelters: 0,
        active_responders: 0,
        relief_inventory_status: 'NOMINAL',
      }),
    });
  });

  await page.route('**/api/v1/simulation/scenarios**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/api/v1/gis/layers**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'FeatureCollection', features: [] }),
    });
  });
}

test.describe('Gate 3 Stage 2: Authentication, Route Guards & Least Privilege', () => {

  // --------------------------------------------------------------------------
  // TC-E2E-01: Unauthenticated Access Redirect
  // --------------------------------------------------------------------------
  test('TC-E2E-01: Unauthenticated direct visit to /admin/recovery-optimization redirects to /login', async ({ page }) => {
    // Ensure no prior session or token exists in localStorage
    await page.addInitScript(() => {
      window.localStorage.clear();
    });

    // Navigate directly to protected administrative recovery optimization route
    await page.goto('/admin/recovery-optimization');

    // ProtectedRoute must intercept unauthenticated session and redirect to /login
    await page.waitForURL('**/login');
    expect(page.url()).toContain('/login');

    // Verify login view is rendered and interactive
    const emailInput = page.getByPlaceholder('officer@dirs.gov');
    await expect(emailInput).toBeVisible();

    // Verify administrative recovery optimization content is NOT exposed or mounted
    const recoveryHeading = page.getByRole('heading', { name: /Recovery Portfolio Optimization/i });
    await expect(recoveryHeading).not.toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-02: Valid ADMIN Login & Routing
  // --------------------------------------------------------------------------
  test('TC-E2E-02: Valid ADMIN login via form navigates to /admin/recovery-optimization', async ({ page }) => {
    // Intercept login authentication endpoint
    await setupMockLogin(page);

    // Also configure /api/v1/auth/me to return ADMIN profile when token is bearer verified
    await page.route('**/api/v1/auth/me', async (route) => {
      const authHeader = route.request().headers()['authorization'];
      if (authHeader === `Bearer ${MOCK_TOKENS.ADMIN}`) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_USERS.ADMIN),
        });
      } else {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Unauthorized' }),
        });
      }
    });

    // Navigate to Login page
    await page.goto('/login');

    // Fill valid ADMIN credentials into the login form
    const emailInput = page.getByPlaceholder('officer@dirs.gov');
    const passwordInput = page.getByPlaceholder('••••••••••••');
    await expect(emailInput).toBeVisible();
    await emailInput.fill(MOCK_USERS.ADMIN.email);
    await passwordInput.fill('Admin123!');

    // Submit the authentication form
    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();

    // Verify redirection to /admin/recovery-optimization
    await page.waitForURL('**/admin/recovery-optimization');
    expect(page.url()).toContain('/admin/recovery-optimization');

    // Verify recovery optimization header is visible
    const recoveryHeading = page.getByRole('heading', { name: /Recovery Portfolio Optimization/i });
    await expect(recoveryHeading).toBeVisible();

    // Verify token was stored in localStorage
    const savedToken = await page.evaluate(() => window.localStorage.getItem('dirs_token'));
    expect(savedToken).toBe(MOCK_TOKENS.ADMIN);
  });

  // --------------------------------------------------------------------------
  // TC-E2E-03: ADMIN Intercepted from /admin
  // --------------------------------------------------------------------------
  test('TC-E2E-03: ADMIN direct visit to /admin is intercepted and redirected to /admin/recovery-optimization', async ({ page }) => {
    await setupMockAuth(page, 'ADMIN');

    // Direct navigation to Command Center (/admin)
    await page.goto('/admin');

    // ProtectedRoute must intercept ADMIN role and route to fallbackPath: /admin/recovery-optimization
    await page.waitForURL('**/admin/recovery-optimization');
    expect(page.url()).toContain('/admin/recovery-optimization');

    // Assert recovery optimization view is mounted
    const recoveryHeading = page.getByRole('heading', { name: /Recovery Portfolio Optimization/i });
    await expect(recoveryHeading).toBeVisible();

    // Assert Command Center content is NOT mounted
    const commandCenterHeading = page.getByRole('heading', { name: /GOVERNMENT EMERGENCY COMMAND CENTER/i });
    await expect(commandCenterHeading).not.toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-04: ADMIN Intercepted from /admin/simulation
  // --------------------------------------------------------------------------
  test('TC-E2E-04: ADMIN direct visit to /admin/simulation is intercepted and redirected to /admin/recovery-optimization', async ({ page }) => {
    await setupMockAuth(page, 'ADMIN');

    // Direct navigation to Simulation Lab (/admin/simulation)
    await page.goto('/admin/simulation');

    // ProtectedRoute must intercept ADMIN role and route to fallbackPath: /admin/recovery-optimization
    await page.waitForURL('**/admin/recovery-optimization');
    expect(page.url()).toContain('/admin/recovery-optimization');

    // Assert recovery optimization view is mounted
    const recoveryHeading = page.getByRole('heading', { name: /Recovery Portfolio Optimization/i });
    await expect(recoveryHeading).toBeVisible();

    // Assert Disaster Simulation content is NOT mounted
    const simulationHeading = page.getByRole('heading', { name: /DISASTER SIMULATION/i });
    await expect(simulationHeading).not.toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-05: GOVT Super-Access to Admin Routes
  // --------------------------------------------------------------------------
  test('TC-E2E-05: GOVT role has authorized super-access across all three administrative routes', async ({ page }) => {
    await setupMockAuth(page, 'GOVT');
    await setupAuxiliaryApiMocks(page);

    // 1. Visit Command Center (/admin)
    await page.goto('/admin');
    await page.waitForURL('**/admin');
    expect(page.url()).toMatch(/\/admin$/);
    const commandCenterHeading = page.getByRole('heading', { name: /GOVERNMENT EMERGENCY COMMAND CENTER/i });
    await expect(commandCenterHeading).toBeVisible();

    // 2. Visit Disaster Simulation Lab (/admin/simulation)
    await page.goto('/admin/simulation');
    await page.waitForURL('**/admin/simulation');
    expect(page.url()).toMatch(/\/admin\/simulation$/);
    const simulationHeading = page.getByRole('heading', { name: /DISASTER SIMULATION/i });
    await expect(simulationHeading).toBeVisible();

    // 3. Visit Recovery Optimization (/admin/recovery-optimization)
    await page.goto('/admin/recovery-optimization');
    await page.waitForURL('**/admin/recovery-optimization');
    expect(page.url()).toMatch(/\/admin\/recovery-optimization$/);
    const recoveryHeading = page.getByRole('heading', { name: /Recovery Portfolio Optimization/i });
    await expect(recoveryHeading).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-06: Sidebar Role Badge & Navigation
  // --------------------------------------------------------------------------
  test('TC-E2E-06: Sidebar navigation DOM renders amber ADMIN badge and only Recovery Optimization link for ADMIN', async ({ page }) => {
    await setupMockAuth(page, 'ADMIN');

    await page.goto('/admin/recovery-optimization');
    await page.waitForURL('**/admin/recovery-optimization');

    // 1. Assert amber "ADMIN" badge rendered in sidebar header
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();
    const adminBadge = sidebar.locator('span', { hasText: /^ADMIN$/ });
    await expect(adminBadge).toBeVisible();
    await expect(adminBadge).toHaveClass(/border-amber/);

    // 2. Assert navigation links for ADMIN: exactly one link to Recovery Optimization
    const navLinks = sidebar.locator('nav a');
    await expect(navLinks).toHaveCount(1);
    const recoveryLink = navLinks.first();
    await expect(recoveryLink).toHaveText(/Recovery Optimization/);
    await expect(recoveryLink).toHaveAttribute('href', '/admin/recovery-optimization');

    // 3. Assert absence of Command Center and Disaster Simulation links in sidebar
    await expect(sidebar.locator('nav a[href="/admin"]')).toHaveCount(0);
    await expect(sidebar.locator('nav a[href="/admin/simulation"]')).toHaveCount(0);
    await expect(sidebar.locator('nav a', { hasText: 'Command Center' })).toHaveCount(0);
    await expect(sidebar.locator('nav a', { hasText: 'GIS & Simulation Lab' })).toHaveCount(0);
  });

  // --------------------------------------------------------------------------
  // TC-E2E-07: User Logout Session Cleared
  // --------------------------------------------------------------------------
  test('TC-E2E-07: User logout removes dirs_token from localStorage and redirects to /login', async ({ page }) => {
    await setupMockAuth(page, 'ADMIN');

    await page.goto('/admin/recovery-optimization');
    await page.waitForURL('**/admin/recovery-optimization');

    // Verify session token is present prior to logout
    const preLogoutToken = await page.evaluate(() => window.localStorage.getItem('dirs_token'));
    expect(preLogoutToken).toBe(MOCK_TOKENS.ADMIN);

    // Locate and click the Logout button in the Navbar
    const logoutButton = page.getByRole('button', { name: /logout/i });
    await expect(logoutButton).toBeVisible();
    await logoutButton.click();

    // Verify redirection to /login
    await page.waitForURL('**/login');
    expect(page.url()).toContain('/login');

    // Verify dirs_token is removed from localStorage
    const postLogoutToken = await page.evaluate(() => window.localStorage.getItem('dirs_token'));
    expect(postLogoutToken).toBeNull();

    // Verify login form is rendered
    await expect(page.getByPlaceholder('officer@dirs.gov')).toBeVisible();
  });

  // --------------------------------------------------------------------------
  // TC-E2E-38: Parameterized Non-Admin Route-Denial Matrix (9 Combinations)
  // --------------------------------------------------------------------------
  test('TC-E2E-38: Parameterized Non-Admin Route-Denial Matrix (9 Combinations)', async ({ browser }) => {
    const NON_ADMIN_ROLES = ['CITIZEN', 'VOLUNTEER', 'NGO'] as const;
    const ADMIN_ROUTES = [
      { path: '/admin', name: 'Command Center' },
      { path: '/admin/simulation', name: 'Disaster Simulation' },
      { path: '/admin/recovery-optimization', name: 'Recovery Optimization' },
    ] as const;

    for (const role of NON_ADMIN_ROLES) {
      for (const route of ADMIN_ROUTES) {
        await test.step(`[TC-E2E-38] Matrix Combination: Role=${role} -> Route=${route.path} (${route.name})`, async () => {
          // Launch an isolated browser context for each matrix combination to guarantee pristine state
          const context = await browser.newContext();
          const page = await context.newPage();

          // Monitor for uncaught page exceptions or redirect loops
          const pageErrors: string[] = [];
          page.on('pageerror', (err) => pageErrors.push(err.message));

          try {
            // Setup authenticated non-admin session
            await setupMockAuth(page, role);
            await setupAuxiliaryApiMocks(page);

            // 1. Attempt direct navigation to target administrative route
            await page.goto(route.path);

            // 2. Assert Route Access Denial & Source-Backed Redirect Destination: /citizen
            await page.waitForURL('**/citizen');
            expect(page.url()).toMatch(/\/citizen$/);
            expect(page.url()).not.toContain(route.path);

            // 3. Verify Authenticated Synthetic Identity on the loaded domain
            const token = await page.evaluate(() => window.localStorage.getItem('dirs_token'));
            expect(token).toBe(MOCK_TOKENS[role]);

            // 4. Assert Content Isolation: Zero administrative DOM elements mounted or exposed
            await expect(page.getByRole('heading', { name: /Recovery Portfolio Optimization/i })).not.toBeVisible();
            await expect(page.getByRole('heading', { name: /GOVERNMENT EMERGENCY COMMAND CENTER/i })).not.toBeVisible();
            await expect(page.getByRole('heading', { name: /DISASTER SIMULATION/i })).not.toBeVisible();
            await expect(page.locator('button:has-text("Execute Optimization")')).not.toBeVisible();

            // 5. Assert Session Stability: Zero uncaught exceptions and no redirect loop
            expect(pageErrors).toHaveLength(0);
          } finally {
            await context.close();
          }
        });
      }
    }
  });

});
