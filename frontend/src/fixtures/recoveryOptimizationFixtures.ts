/**
 * DIRS Phase 6D-B Milestone 4 Gate 1: Frontend Test Fixtures
 * Synthetic recovery portfolio optimization scenario requests and responses.
 *
 * Provides typed test data for:
 * 1. minimalValidScenarioRequestFixture: Valid minimal 1-candidate request.
 * 2. tier1MandatoryScenarioRequestFixture: Valid request with mandatory safety window.
 * 3. optimalScenarioResponseFixture: Fully populated OPTIMAL response with exact integer strings.
 * 4. infeasibleScenarioResponseFixture: INFEASIBLE response with diagnostic findings.
 */

import {
  RecoveryOptimizationScenarioRequest,
  RecoveryOptimizationScenarioResponse,
} from '../types/recoveryOptimization';

/**
 * 1. Minimal valid scenario request.
 * Single candidate project, 12 planning periods, INR currency.
 */
export const minimalValidScenarioRequestFixture: RecoveryOptimizationScenarioRequest = {
  scenario_name: 'Minimal Valid Recovery Scenario',
  planning_horizon_periods: 12,
  period_length_days: 30.0,
  initial_cash: '10000000.00',
  cash_currency: 'INR',
  periodic_budgets: {
    1: '10000000.00',
    2: '5000000.00',
    3: '5000000.00',
  },
  budget_currency: 'INR',
  candidates: [
    {
      project_id: 'P-001',
      project_code: 'ROAD-REPAIR-01',
      district_id: 'DIST-NORTH',
      estimated_cost: '5000000.00',
      duration_periods: 3,
      cost_currency: 'INR',
      release_period: 1,
      deadline_period: 6,
      is_tier1_mandatory: false,
      raw_mcpi_score: 0.85,
    },
  ],
  deterministic_seed: 42,
  num_workers: 1,
  max_solve_time_seconds: 30.0,
};

/**
 * 2. Tier-1 mandatory scenario request.
 * Includes a mandatory safety critical project and explicit max_safety_start_period.
 */
export const tier1MandatoryScenarioRequestFixture: RecoveryOptimizationScenarioRequest = {
  scenario_name: 'Tier-1 Mandatory Safety Scenario',
  planning_horizon_periods: 12,
  period_length_days: 30.0,
  initial_cash: '25000000.00',
  cash_currency: 'INR',
  max_safety_start_period: 3,
  candidates: [
    {
      project_id: 'P-T1-01',
      project_code: 'HOSPITAL-SEISMIC-RETROFIT',
      district_id: 'DIST-CENTRAL',
      estimated_cost: '12000000.00',
      duration_periods: 2,
      cost_currency: 'INR',
      release_period: 1,
      deadline_period: 4,
      is_tier1_mandatory: true,
      raw_mcpi_score: 0.98,
    },
    {
      project_id: 'P-GEN-02',
      project_code: 'COMMUNITY-CENTER-ROOF',
      district_id: 'DIST-EAST',
      estimated_cost: '4000000.00',
      duration_periods: 2,
      cost_currency: 'INR',
      release_period: 2,
      deadline_period: 8,
      is_tier1_mandatory: false,
      raw_mcpi_score: 0.65,
    },
  ],
  deterministic_seed: 42,
  num_workers: 1,
  max_solve_time_seconds: 30.0,
};

/**
 * 3. Optimal scenario response fixture.
 * Models an OPTIMAL solve outcome. All Category 1 64-bit integer fields and
 * Category 3 Decimal fields are preserved as exact strings.
 */
export const optimalScenarioResponseFixture: RecoveryOptimizationScenarioResponse = {
  scenario_name: 'Minimal Valid Recovery Scenario',
  solver_status: 'OPTIMAL',
  is_optimal: true,
  exact_objective_value: '850000000000',
  exact_best_bound: '850000000000',
  conservative_best_bound: '850000000000',
  objective_value: 850000.0,
  best_bound: 850000.0,
  optimality_gap: 0.0,
  solve_time_seconds: 0.124,
  selected_project_count: 1,
  total_cost_ccu: '500000000',
  total_cost_inr: '5000000.00',
  scheduled_projects: [
    {
      project_id: 'P-001',
      project_code: 'ROAD-REPAIR-01',
      district_id: 'DIST-NORTH',
      is_selected: true,
      scheduled_start_period: 1,
      scheduled_completion_period: 3,
      assigned_funding_source: null,
      cost_ccu: '500000000',
      cost_inr: '5000000.00',
      periodic_expenditures_ccu: {
        '1': '166666666',
        '2': '166666667',
        '3': '166666667',
      },
      periodic_expenditures_inr: {
        '1': '1666666.66',
        '2': '1666666.67',
        '3': '1666666.67',
      },
      mcpi_score: 0.85,
      raw_mcpi_score: 0.85,
      quantized_mcpi_coefficient: 850000000,
      is_tier1_mandatory: false,
    },
  ],
  periodic_solvency: [
    {
      period: 1,
      revenue_receipt_ccu: '1000000000',
      expenditure_ccu: '166666666',
      cash_balance_ccu: '833333334',
      cash_balance_inr: '8333333.34',
      is_solvent: true,
    },
    {
      period: 2,
      revenue_receipt_ccu: '0',
      expenditure_ccu: '166666667',
      cash_balance_ccu: '666666667',
      cash_balance_inr: '6666666.67',
      is_solvent: true,
    },
    {
      period: 3,
      revenue_receipt_ccu: '0',
      expenditure_ccu: '166666667',
      cash_balance_ccu: '500000000',
      cash_balance_inr: '5000000.00',
      is_solvent: true,
    },
  ],
  district_equity_allocation_ccu: {
    'DIST-NORTH': '500000000',
  },
  district_equity_allocation_inr: {
    'DIST-NORTH': '5000000.00',
  },
  input_fingerprint_sha256: 'a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90',
  ortools_version: '9.8.3296',
  solver_parameters: {
    seed: 42,
    num_workers: 1,
    max_time_in_seconds: 30.0,
  },
  infeasibility_diagnostics: null,
};

/**
 * 4. Infeasible scenario response fixture.
 * Models an INFEASIBLE solve outcome with structured diagnostic conflict report.
 */
export const infeasibleScenarioResponseFixture: RecoveryOptimizationScenarioResponse = {
  scenario_name: 'Infeasible Safety Window Scenario',
  solver_status: 'INFEASIBLE',
  is_optimal: false,
  exact_objective_value: null,
  exact_best_bound: null,
  conservative_best_bound: null,
  objective_value: null,
  best_bound: null,
  optimality_gap: null,
  solve_time_seconds: 0.045,
  selected_project_count: 0,
  total_cost_ccu: '0',
  total_cost_inr: '0.00',
  scheduled_projects: [],
  periodic_solvency: [],
  district_equity_allocation_ccu: {},
  district_equity_allocation_inr: {},
  input_fingerprint_sha256: 'b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1',
  ortools_version: '9.8.3296',
  solver_parameters: {
    seed: 42,
    num_workers: 1,
    max_time_in_seconds: 30.0,
  },
  infeasibility_diagnostics: {
    has_proven_infeasibility: true,
    proven_causes: [
      {
        category: 'MANDATORY_PROJECT_SAFETY_WINDOW',
        classification: 'PROVEN_CAUSE',
        message: 'Tier-1 mandatory project P-T1-01 cannot start before max_safety_start_period 1 due to release period 3.',
        mathematical_condition: 'release_period (3) > max_safety_start_period (1)',
        affected_projects: ['P-T1-01'],
        conflicting_periods: [1, 2, 3],
        details: { release_period: 3, max_safety_start_period: 1 },
      },
    ],
    necessary_condition_violations: [],
    solver_hypotheses: [],
    warnings: [],
    is_assumption_core_minimal: true,
    is_assumption_core_sufficient: true,
  },
};
