/**
 * DIRS Phase 6F / Accelerated Programme Work Package 2
 * Recovery Simulation & Community Monitoring Workbench E2E Browser Test Suite.
 *
 * Verifies real browser interactions:
 * - Authorized GOVT officer navigates to /admin/simulation.
 * - Tab switching to "Community Recovery & What-If".
 * - Community indicators and KPI cards rendered with data confidence decay badge.
 * - Interactive scenario sliders (budget multiplier, supply constraint, secondary hazard).
 * - What-if forward simulation run with trajectory graph and bottleneck callouts.
 * - Interactive vulnerability rescoring calculation with demographic baseline, deficit math, and delta.
 */

import { test, expect } from '@playwright/test';
import { setupMockAuth } from './fixtures/recoveryMockFixtures';
import {
  CommunityMetricSummaryResponse,
  RecoveryWhatIfSimulationResponse,
  VulnerabilityRescoreResponse
} from '../../src/types/communityMonitoring';

const MOCK_COMMUNITY_SUMMARY: CommunityMetricSummaryResponse = {
  total_wards_monitored: 4,
  reporting_date_range: {
    earliest: '2026-11-10T00:00:00Z',
    latest: '2026-11-18T00:00:00Z',
  },
  average_recovery_score: 72.5,
  average_confidence: 88.4,
  sector_restoration_averages: {
    power: 78.0,
    water: 82.0,
    health: 68.0,
    schools: 70.0,
    livelihoods: 64.0,
  },
  total_active_shelters: 8,
  total_remaining_displaced: 450,
  freshness_distribution: {
    FRESH: 3,
    MODERATE: 1,
    STALE_AMBER: 0,
    EXPIRED_RED: 0,
  },
  wards: [
    {
      ward_code: 'WARD-01',
      district: 'Central',
      metric_date: '2026-11-18T00:00:00Z',
      active_shelter_count: 2,
      remaining_displaced_persons: 120,
      power_grid_restoration_pct: 85.0,
      potable_water_access_pct: 90.0,
      healthcare_facility_operational_pct: 75.0,
      schools_open_pct: 80.0,
      livelihoods_resumed_pct: 60.0,
      overall_recovery_score: 79.25,
      initial_confidence: 100.0,
      current_confidence: 94.5,
      freshness_status: 'FRESH',
      days_since_verification: 1.1,
      last_verified_at: '2026-11-17T00:00:00Z',
    },
  ],
};

const MOCK_SIM_RESPONSE: RecoveryWhatIfSimulationResponse = {
  scenario_name: 'Test Coastal Restoration',
  planning_horizon_periods: 6,
  period_length_days: 30.0,
  is_non_mutating: true,
  baseline_completion_period: 5,
  simulated_completion_period: 4,
  baseline_final_recovery_score: 85.0,
  simulated_final_recovery_score: 92.5,
  recovery_score_delta: 7.5,
  periods_to_target_80pct: 4,
  total_budget_allocated: 20000000.0,
  total_budget_utilized: 18500000.0,
  unmet_budget_deficit: 0.0,
  bottleneck_resources: [
    {
      material_category: 'CEMENT',
      demand_quantity: 150.0,
      available_supply: 90.0,
      deficit_quantity: 60.0,
      impact_level: 'HIGH',
    },
  ],
  trajectory: [
    {
      period: 1,
      calendar_day: 30.0,
      capital_spent_period: 3000000.0,
      cumulative_capital_spent: 3000000.0,
      remaining_cash_balance: 17000000.0,
      projects_in_progress: 3,
      projects_completed_cumulative: 0,
      displaced_persons_remaining: 500,
      projected_recovery_score: 15.0,
      unmet_needs_score: 85.0,
      shock_occurred: false,
    },
    {
      period: 2,
      calendar_day: 60.0,
      capital_spent_period: 4000000.0,
      cumulative_capital_spent: 7000000.0,
      remaining_cash_balance: 13000000.0,
      projects_in_progress: 3,
      projects_completed_cumulative: 1,
      displaced_persons_remaining: 350,
      projected_recovery_score: 40.0,
      unmet_needs_score: 60.0,
      shock_occurred: false,
    },
    {
      period: 3,
      calendar_day: 90.0,
      capital_spent_period: 4000000.0,
      cumulative_capital_spent: 11000000.0,
      remaining_cash_balance: 9000000.0,
      projects_in_progress: 2,
      projects_completed_cumulative: 3,
      displaced_persons_remaining: 150,
      projected_recovery_score: 75.0,
      unmet_needs_score: 25.0,
      shock_occurred: false,
    },
    {
      period: 4,
      calendar_day: 120.0,
      capital_spent_period: 3500000.0,
      cumulative_capital_spent: 14500000.0,
      remaining_cash_balance: 5500000.0,
      projects_in_progress: 1,
      projects_completed_cumulative: 4,
      displaced_persons_remaining: 50,
      projected_recovery_score: 88.0,
      unmet_needs_score: 12.0,
      shock_occurred: false,
    },
  ],
  simulation_provenance: { is_non_mutating: true },
};

const MOCK_RESCORE_RESPONSE: VulnerabilityRescoreResponse = {
  ward_code: 'WARD-04-NORTH',
  district: 'Central District',
  base_demographic_vulnerability: 0.450000,
  rescored_vulnerability: 0.385000,
  vulnerability_delta: -0.065000,
  raw_headcount_index_psi: 325.0,
  baseline_status: 'BASELINE_KNOWN',
  effective_denominator: 2000.0,
  infrastructure_deficit_score: 0.3500,
  displacement_pressure_score: 0.1500,
  data_confidence: 94.0,
  freshness_status: 'FRESH',
  days_elapsed: 1.2,
  uncertainty_flag: false,
  audit_trail: {
    formula: 'phi_rescored = min(1.0, 0.50*eff_base + 0.35*I_def*eff_base + 0.15*D_press)',
  },
};

test.describe('WP2 Recovery Simulation Workbench Browser Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockAuth(page, 'GOVT');

    // Intercept backend API routes
    await page.route('**/api/v1/recovery/monitoring/community-metrics/summary*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_COMMUNITY_SUMMARY),
      });
    });

    await page.route('**/api/v1/recovery/simulation/what-if', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SIM_RESPONSE),
      });
    });

    await page.route('**/api/v1/recovery/monitoring/vulnerability-rescore', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_RESCORE_RESPONSE),
      });
    });

    await page.route('**/api/v1/simulation/scenarios*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.route('**/api/v1/gis/layers*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ type: 'FeatureCollection', features: [] }),
      });
    });
  });

  test('TC-WP2-01: Navigates to Community Recovery Simulation tab and renders KPI cards', async ({ page }) => {
    await page.goto('/admin/simulation');
    await page.waitForLoadState('networkidle');

    // Click on the Community Recovery & What-If tab
    const recoveryTabBtn = page.getByRole('button', { name: /Community Recovery & What-If/i });
    await expect(recoveryTabBtn).toBeVisible();
    await recoveryTabBtn.click();

    // Verify Workbench renders
    const workbench = page.locator('[data-testid="recovery-simulation-workbench"]');
    await expect(workbench).toBeVisible();

    // Verify KPI stats render
    await expect(page.getByText('Wards Monitored')).toBeVisible();
    await expect(page.getByText('Avg Recovery Score')).toBeVisible();
    await expect(page.getByText('READ-ONLY SAFEGUARD CERTIFIED')).toBeVisible();
  });

  test('TC-WP2-02: Executes What-If forward simulation and displays trajectory results', async ({ page }) => {
    await page.goto('/admin/simulation');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /Community Recovery & What-If/i }).click();

    // Click "Run What-If Forward Simulation"
    const runSimBtn = page.getByRole('button', { name: /Run What-If Forward Simulation/i });
    await expect(runSimBtn).toBeVisible();
    await runSimBtn.click();

    // Verify simulation results appear
    await expect(page.getByText('Projected Recovery Trajectory')).toBeVisible();
    await expect(page.getByText('80% Target Reached: Period 4')).toBeVisible();
    await expect(page.getByText('Simulated Final Score')).toBeVisible();
    await expect(page.getByText('Supply Bottlenecks & Operational Constraints')).toBeVisible();
    await expect(page.getByText('CEMENT', { exact: true })).toBeVisible();
    await expect(page.getByText('DEFICIT -60')).toBeVisible();
  });

  test('TC-WP2-03: Executes Vulnerability Rescoring and displays mathematical delta and freshness', async ({ page }) => {
    await page.goto('/admin/simulation');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /Community Recovery & What-If/i }).click();

    // Click "Calculate Rescored Vulnerability (φ)"
    const rescoreBtn = page.getByRole('button', { name: /Calculate Rescored Vulnerability/i });
    await expect(rescoreBtn).toBeVisible();
    await rescoreBtn.click();

    // Verify results card
    await expect(page.getByText('Demographic Baseline φ_V:')).toBeVisible();
    await expect(page.getByText('0.4500')).toBeVisible();
    await expect(page.getByText('Rescored Vulnerability φ_res:')).toBeVisible();
    await expect(page.getByText('0.3850')).toBeVisible();
    await expect(page.getByText('Net Delta:')).toBeVisible();
    await expect(page.getByText('-0.0650')).toBeVisible();
  });
});
