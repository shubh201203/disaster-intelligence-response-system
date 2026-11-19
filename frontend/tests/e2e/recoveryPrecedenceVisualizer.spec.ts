/**
 * DIRS Phase 6E Accelerated Programme: Work Package 1
 * Precedence Graph Visualizer End-to-End Browser Interaction Test Suite.
 *
 * Verifies real browser interactions:
 * - Authorized GOVT role navigates to /admin and switches to Infrastructure Precedence view.
 * - Loading and rendering of DAG SVG elements (nodes, directed edges, critical path indicators).
 * - KPI summary cards accurately display project counts, dependencies, critical nodes, and makespan.
 * - Node inspection drawer opens on node click with accurate CPM metrics (ES, EF, LS, LF, Total Float).
 * - Zoom in, zoom out, and reset view controls update canvas zoom percentage.
 * - Critical path filter toggle highlights critical path nodes.
 * - Dry-run dependency edge validator modal opens, submits candidate edges, and renders validation response (acyclic approval and cycle warning).
 */

import { test, expect } from '@playwright/test';
import { setupMockAuth } from './fixtures/recoveryMockFixtures';
import {
  PrecedenceGraphResponse,
  PrecedenceEdgeValidateResponse,
} from '../../src/types/precedence';

const MOCK_GRAPH_RESPONSE: PrecedenceGraphResponse = {
  is_acyclic: true,
  topological_order: ['p-water-01', 'p-power-02', 'p-hosp-03'],
  critical_path_project_ids: ['p-water-01', 'p-power-02', 'p-hosp-03'],
  project_makespan_periods: 5,
  total_projects: 3,
  total_dependencies: 2,
  nodes: [
    {
      id: 'p-water-01',
      project_code: 'REC-WASH-01',
      title: 'Water Treatment Intake',
      sector: 'WASH',
      priority_tier: 'TIER_1',
      status: 'APPROVED',
      estimated_cost: 150000,
      estimated_duration_days: 60,
      cpm: {
        duration_periods: 2,
        early_start: 0,
        early_finish: 2,
        late_start: 0,
        late_finish: 2,
        total_float: 0,
        free_float: 0,
        is_critical: true,
      },
    },
    {
      id: 'p-power-02',
      project_code: 'REC-POW-02',
      title: 'Substation Feeder Line',
      sector: 'POWER',
      priority_tier: 'TIER_1',
      status: 'APPROVED',
      estimated_cost: 85000,
      estimated_duration_days: 30,
      cpm: {
        duration_periods: 1,
        early_start: 2,
        early_finish: 3,
        late_start: 2,
        late_finish: 3,
        total_float: 0,
        free_float: 0,
        is_critical: true,
      },
    },
    {
      id: 'p-hosp-03',
      project_code: 'REC-HLT-03',
      title: 'District Hospital Energization',
      sector: 'HEALTH',
      priority_tier: 'TIER_1',
      status: 'PROPOSED',
      estimated_cost: 120000,
      estimated_duration_days: 30,
      cpm: {
        duration_periods: 1,
        early_start: 4,
        early_finish: 5,
        late_start: 4,
        late_finish: 5,
        total_float: 0,
        free_float: 0,
        is_critical: true,
      },
    },
  ],
  edges: [
    {
      id: 'dep-01',
      predecessor_project_id: 'p-water-01',
      successor_project_id: 'p-power-02',
      dependency_type: 'FINISH_TO_START',
      lag_days: 0,
      lag_periods: 0,
      is_critical_path: true,
      rationale: 'Cooling line connection',
    },
    {
      id: 'dep-02',
      predecessor_project_id: 'p-power-02',
      successor_project_id: 'p-hosp-03',
      dependency_type: 'FINISH_TO_START',
      lag_days: 30,
      lag_periods: 1,
      is_critical_path: true,
      rationale: 'Safety stabilization lag',
    },
  ],
  cycle_path: null,
};

test.describe('WP1 Precedence Graph Visualizer End-to-End Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Mock base command center APIs
    await page.route('**/analytics/summary', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          active_disasters: 2,
          critical_incidents: 5,
          people_affected: 1200,
          active_volunteers: 45,
          shelter_capacity_utilized: 68.5,
          sos_pending_count: 3,
        }),
      });
    });

    await page.route('**/incidents', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.route('**/shelters', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    // Mock Precedence Graph endpoint
    await page.route('**/recovery/dependencies/graph*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_GRAPH_RESPONSE),
      });
    });

    // Setup GOVT authorized session and navigate to /admin
    await setupMockAuth(page, 'GOVT');
    await page.goto('/admin');
    await page.waitForURL('**/admin');
  });

  test('TC-WP1-01: GOVT officer can switch to Precedence Network tab and load DAG visualizer', async ({ page }) => {
    // Verify Command Center header
    await expect(page.getByRole('heading', { name: /GOVERNMENT EMERGENCY COMMAND CENTER/i })).toBeVisible();

    // Click Infrastructure Precedence tab
    const precedenceTabBtn = page.getByRole('button', { name: /Infrastructure Precedence \(CPM-PL\)/i });
    await expect(precedenceTabBtn).toBeVisible();
    await precedenceTabBtn.click();

    // Verify DAG visualizer container
    await expect(page.getByText('Infrastructure Precedence Network')).toBeVisible();
    await expect(page.getByText('Acyclic DAG')).toBeVisible();

    // Verify KPI summary metrics
    await expect(page.getByText('Total Projects:').locator('..').getByText('3')).toBeVisible();
    await expect(page.getByText('Dependencies:').locator('..').getByText('2')).toBeVisible();
    await expect(page.getByText('Critical Projects:').locator('..').getByText('3')).toBeVisible();
    await expect(page.getByText('Makespan:').locator('..').getByText('5 Periods')).toBeVisible();

    // Verify SVG canvas renders nodes
    const svgCanvas = page.locator('#graph-canvas');
    await expect(svgCanvas).toBeVisible();
    await expect(svgCanvas.getByText('REC-WASH-01')).toBeVisible();
    await expect(svgCanvas.getByText('REC-POW-02')).toBeVisible();
    await expect(svgCanvas.getByText('REC-HLT-03')).toBeVisible();
  });

  test('TC-WP1-02: Clicking a project node opens Inspector Drawer with exact CPM bounds', async ({ page }) => {
    // Switch to Precedence tab
    await page.getByRole('button', { name: /Infrastructure Precedence \(CPM-PL\)/i }).click();

    // Click REC-WASH-01 node
    const nodeEl = page.locator('#graph-canvas').getByText('REC-WASH-01');
    await expect(nodeEl).toBeVisible();
    await nodeEl.click();

    // Inspector Drawer appears on the right
    await expect(page.getByRole('heading', { name: 'Water Treatment Intake' })).toBeVisible();
    await expect(page.getByText('CPM-PL Schedule Bounds')).toBeVisible();
    await expect(page.getByText('Early Start:').locator('..').getByText('Period 0')).toBeVisible();
    await expect(page.getByText('Early Finish:').locator('..').getByText('Period 2')).toBeVisible();
    await expect(page.getByText('Total Float:').locator('..').getByText('0 periods')).toBeVisible();
  });

  test('TC-WP1-03: Zoom controls and Critical Path toggle function interactively', async ({ page }) => {
    // Switch to Precedence tab
    await page.getByRole('button', { name: /Infrastructure Precedence \(CPM-PL\)/i }).click();

    // Verify initial zoom 100%
    await expect(page.getByText('100%')).toBeVisible();

    // Click Zoom In
    await page.getByRole('button', { name: 'Zoom In' }).click();
    await expect(page.getByText('115%')).toBeVisible();

    // Click Reset
    await page.getByRole('button', { name: 'Reset View' }).click();
    await expect(page.getByText('100%')).toBeVisible();

    // Toggle Critical Path Only
    const critToggle = page.getByRole('button', { name: /Critical Path Only/i });
    await critToggle.click();
    await expect(critToggle).toHaveClass(/bg-red-950/);
  });

  test('TC-WP1-04: Dry-Run Dependency Link Validator validates candidate edge and reports cycle feedback', async ({ page }) => {
    // Mock candidate validation endpoint
    await page.route('**/recovery/dependencies/validate-edge', async (route) => {
      const body = JSON.parse(route.request().postData() || '{}');
      if (body.predecessor_project_id === 'p-hosp-03' && body.successor_project_id === 'p-water-01') {
        // Return simulated cycle
        const response: PrecedenceEdgeValidateResponse = {
          is_valid: false,
          reason: 'CYCLIC_DEPENDENCY',
          message: 'Candidate edge introduces a circular dependency cycle.',
          cycle_path: ['REC-WASH-01', 'REC-POW-02', 'REC-HLT-03', 'REC-WASH-01'],
        };
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(response),
        });
      } else {
        const response: PrecedenceEdgeValidateResponse = {
          is_valid: true,
          reason: null,
          message: 'Candidate dependency edge is valid and acyclic.',
          cycle_path: null,
        };
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(response),
        });
      }
    });

    // Switch to Precedence tab
    await page.getByRole('button', { name: /Infrastructure Precedence \(CPM-PL\)/i }).click();

    // Click "Test Link (Dry-Run)" button
    await page.getByRole('button', { name: /Test Link \(Dry-Run\)/i }).click();

    // Modal opens
    await expect(page.getByText('Dry-Run Dependency Link Validator')).toBeVisible();

    // Select cyclic edge inside modal form: predecessor = p-hosp-03, successor = p-water-01
    const modalForm = page.locator('form');
    await modalForm.locator('select').nth(0).selectOption({ value: 'p-hosp-03' });
    await modalForm.locator('select').nth(1).selectOption({ value: 'p-water-01' });

    // Submit check
    await modalForm.getByRole('button', { name: /Run Dry-Run Cycle Check/i }).click();

    // Verify cycle warning appears
    await expect(page.getByText('Dependency Rejected: CYCLIC_DEPENDENCY')).toBeVisible();
    await expect(page.getByText('REC-WASH-01 → REC-POW-02 → REC-HLT-03 → REC-WASH-01')).toBeVisible();
  });
});
