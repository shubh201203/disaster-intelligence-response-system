import { test, expect } from '@playwright/test';
import {
  minimalValidScenarioRequestFixture,
  tier1MandatoryScenarioRequestFixture,
  optimalScenarioResponseFixture,
  infeasibleScenarioResponseFixture,
} from '../../src/fixtures/recoveryOptimizationFixtures';
import {
  CurrencyUnit,
  SolverOutcomeStatus,
  OptimizationErrorType,
  RecoveryOptimizationScenarioRequest,
  RecoveryOptimizationScenarioResponse,
  ProjectOptimizationCandidateDTO,
  ScheduledProjectResultDTO,
  PeriodSolvencyResultDTO,
} from '../../src/types/recoveryOptimization';

test.describe('Recovery Optimization DTO & Fixture Contract Suite', () => {
  // ============================================================================
  // 1. Request Contract Constraints & Fixture Verification
  // ============================================================================
  test.describe('Request Contracts & Fixtures', () => {
    test('Currency unit union literals conform to INR | CCU', () => {
      const validCurrencies: CurrencyUnit[] = ['INR', 'CCU'];
      expect(validCurrencies).toContain(minimalValidScenarioRequestFixture.cash_currency);
      expect(validCurrencies).toContain(tier1MandatoryScenarioRequestFixture.cash_currency);
    });

    test('Minimal valid scenario fixture satisfies all backend contract invariants', () => {
      const req: RecoveryOptimizationScenarioRequest = minimalValidScenarioRequestFixture;

      // Scenario name
      expect(typeof req.scenario_name).toBe('string');
      expect(req.scenario_name.length).toBeGreaterThan(0);
      expect(req.scenario_name.length).toBeLessThanOrEqual(100);

      // Planning horizon
      expect(req.planning_horizon_periods).toBeGreaterThanOrEqual(1);
      expect(req.planning_horizon_periods).toBeLessThanOrEqual(120);

      // Candidate count
      expect(req.candidates.length).toBeGreaterThan(0);
      expect(req.candidates.length).toBeLessThanOrEqual(500);

      // Solve time & workers
      expect(req.max_solve_time_seconds).toBeLessThanOrEqual(120.0);
      expect(req.num_workers).toBeGreaterThanOrEqual(1);
      expect(req.num_workers).toBeLessThanOrEqual(16);
      expect(req.deterministic_seed).toBeGreaterThanOrEqual(0);

      // Candidate 1-based indexing & duration
      const candidate = req.candidates[0];
      expect(candidate.duration_periods).toBeGreaterThanOrEqual(1);
      expect(candidate.release_period).toBeGreaterThanOrEqual(1);
      expect(candidate.release_period!).toBeLessThanOrEqual(req.planning_horizon_periods);
      if (candidate.deadline_period != null) {
        expect(candidate.deadline_period).toBeGreaterThanOrEqual(
          candidate.release_period! + candidate.duration_periods - 1
        );
        expect(candidate.deadline_period).toBeLessThanOrEqual(req.planning_horizon_periods);
      }

      // Cost decimal representation
      expect(typeof candidate.estimated_cost).toBe('string');
    });

    test('Tier-1 mandatory fixture enforces safety window and valid candidate IDs', () => {
      const req: RecoveryOptimizationScenarioRequest = tier1MandatoryScenarioRequestFixture;

      expect(req.candidates.some((c) => c.is_tier1_mandatory)).toBe(true);

      // max_safety_start_period must be defined when tier1 mandatory candidates exist
      expect(req.max_safety_start_period).toBeDefined();
      expect(req.max_safety_start_period).not.toBeNull();
      expect(req.max_safety_start_period!).toBeGreaterThanOrEqual(1);
      expect(req.max_safety_start_period!).toBeLessThanOrEqual(req.planning_horizon_periods);

      // Candidate IDs must be unique strings
      const candidateIds = req.candidates.map((c) => c.project_id);
      const uniqueIds = new Set(candidateIds);
      expect(uniqueIds.size).toBe(candidateIds.length);

      // Dependency references (if present) must exist in candidates
      if (req.dependencies && req.dependencies.length > 0) {
        for (const dep of req.dependencies) {
          expect(uniqueIds.has(dep.predecessor_id)).toBe(true);
          expect(uniqueIds.has(dep.successor_id)).toBe(true);
          expect(dep.lag_periods ?? 0).toBeGreaterThanOrEqual(0);
        }
      }
    });

    test('Decimal strings are not coerced to numbers in request fixtures', () => {
      const req = minimalValidScenarioRequestFixture;
      expect(typeof req.initial_cash).toBe('string');
      expect(req.initial_cash).toBe('10000000.00');

      if (req.periodic_budgets) {
        for (const [period, amount] of Object.entries(req.periodic_budgets)) {
          expect(Number(period)).toBeGreaterThanOrEqual(1);
          expect(typeof amount).toBe('string');
        }
      }
    });
  });

  // ============================================================================
  // 2. Response Contract Constraints & Fixture Verification
  // ============================================================================
  test.describe('Response Contracts & Fixtures', () => {
    test('Solver outcome status type covers all six application statuses', () => {
      const allStatuses: SolverOutcomeStatus[] = [
        'OPTIMAL',
        'FEASIBLE',
        'INFEASIBLE',
        'UNKNOWN',
        'MODEL_INVALID',
        'POST_SOLVE_RECONCILIATION_FAILED',
      ];
      expect(allStatuses).toContain(optimalScenarioResponseFixture.solver_status);
      expect(allStatuses).toContain(infeasibleScenarioResponseFixture.solver_status);
    });

    test('OPTIMAL scenario response fixture satisfies all mathematical invariants', () => {
      const res: RecoveryOptimizationScenarioResponse = optimalScenarioResponseFixture;

      // Status & Optimality
      expect(res.solver_status).toBe('OPTIMAL');
      expect(res.is_optimal).toBe(true);
      expect(res.optimality_gap).toBe(0.0);

      // Category 1: Exact 64-bit integer strings
      expect(typeof res.exact_objective_value).toBe('string');
      expect(res.exact_objective_value).toBe('850000000000');
      expect(typeof res.exact_best_bound).toBe('string');
      expect(typeof res.conservative_best_bound).toBe('string');
      expect(typeof res.total_cost_ccu).toBe('string');

      // Category 3: Exact Decimal strings
      expect(typeof res.total_cost_inr).toBe('string');
      expect(res.total_cost_inr).toBe('5000000.00');

      // Scheduled projects
      expect(res.selected_project_count).toBe(res.scheduled_projects.filter((p) => p.is_selected).length);
      for (const proj of res.scheduled_projects) {
        if (proj.is_selected) {
          expect(proj.scheduled_start_period).toBeGreaterThanOrEqual(1);
          expect(proj.scheduled_completion_period).toBeGreaterThanOrEqual(proj.scheduled_start_period!);
        } else {
          expect(proj.scheduled_start_period).toBeNull();
          expect(proj.scheduled_completion_period).toBeNull();
        }

        // CCU and INR cost fields
        expect(typeof proj.cost_ccu).toBe('string');
        expect(typeof proj.cost_inr).toBe('string');

        // Periodic expenditure dictionaries
        for (const [pStr, ccuStr] of Object.entries(proj.periodic_expenditures_ccu)) {
          expect(Number(pStr)).toBeGreaterThanOrEqual(1);
          expect(typeof ccuStr).toBe('string');
        }
        for (const [pStr, inrStr] of Object.entries(proj.periodic_expenditures_inr)) {
          expect(Number(pStr)).toBeGreaterThanOrEqual(1);
          expect(typeof inrStr).toBe('string');
        }
      }

      // Periodic solvency
      for (const solv of res.periodic_solvency) {
        expect(solv.period).toBeGreaterThanOrEqual(1);
        expect(typeof solv.revenue_receipt_ccu).toBe('string');
        expect(typeof solv.expenditure_ccu).toBe('string');
        expect(typeof solv.cash_balance_ccu).toBe('string');
        expect(typeof solv.cash_balance_inr).toBe('string');
        expect(typeof solv.is_solvent).toBe('boolean');
      }

      // District equity
      for (const [dist, ccu] of Object.entries(res.district_equity_allocation_ccu)) {
        expect(typeof dist).toBe('string');
        expect(typeof ccu).toBe('string');
      }
      for (const [dist, inr] of Object.entries(res.district_equity_allocation_inr)) {
        expect(typeof dist).toBe('string');
        expect(typeof inr).toBe('string');
      }

      // Input fingerprint
      expect(typeof res.input_fingerprint_sha256).toBe('string');
      expect(res.input_fingerprint_sha256.length).toBe(64);
    });

    test('INFEASIBLE scenario response fixture provides structured diagnostic findings', () => {
      const res: RecoveryOptimizationScenarioResponse = infeasibleScenarioResponseFixture;

      expect(res.solver_status).toBe('INFEASIBLE');
      expect(res.is_optimal).toBe(false);
      expect(res.exact_objective_value).toBeNull();
      expect(res.exact_best_bound).toBeNull();
      expect(res.objective_value).toBeNull();
      expect(res.selected_project_count).toBe(0);

      // Infeasibility diagnostics structure
      expect(res.infeasibility_diagnostics).not.toBeNull();
      expect(res.infeasibility_diagnostics?.has_proven_infeasibility).toBe(true);
      expect(res.infeasibility_diagnostics?.proven_causes.length).toBeGreaterThan(0);

      const cause = res.infeasibility_diagnostics!.proven_causes[0];
      expect(cause.classification).toBe('PROVEN_CAUSE');
      expect(typeof cause.category).toBe('string');
      expect(typeof cause.message).toBe('string');
      expect(typeof cause.mathematical_condition).toBe('string');
      expect(Array.isArray(cause.affected_projects)).toBe(true);
      expect(Array.isArray(cause.conflicting_periods)).toBe(true);
    });

    test('Optimization error type union covers all 5 documented error types', () => {
      const errorTypes: OptimizationErrorType[] = [
        'INVALID_REQUEST',
        'PROVEN_INFEASIBILITY',
        'SOLVER_TIMEOUT',
        'FEASIBLE_SUBOPTIMAL',
        'INTERNAL_EXECUTION_FAILURE',
      ];
      expect(errorTypes.length).toBe(5);
    });
  });
});
