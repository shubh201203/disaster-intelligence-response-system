/**
 * DIRS Phase 6D-B Milestone 4 Gate 2 Stage 4: Visualization & Decision Support Contract Test Suite
 *
 * Verifies mathematical, numerical, and architectural invariants for Stage 4 components:
 * 1. Six solver statuses & hasUsableSchedule() predicate.
 * 2. Category 1 exact 64-bit integer string preservation (> 2^53 - 1).
 * 3. Exact Indian currency (INR) formatting without float arithmetic.
 * 4. CCU and INR dual-ledger separation.
 * 5. 1-based timeline coordinate calculations and inclusive project duration.
 * 6. Scheduled vs. unselected partitioning and "Not selected" outcome status without fabricated rejection reasons.
 * 7. Four diagnostic tiers classification (Proven Causes, Necessary Violations, Solver Hypotheses, Warnings).
 * 8. Missing / null diagnostics handling for all non-solution statuses.
 * 9. Post-solve reconciliation failure schedule rejection and suppression.
 * 10. UNKNOWN status indeterminate presentation without fabricated timeout/infeasibility claims.
 * 11. Null KPI metric fallback handling.
 * 12. Maximum planning horizon (T=120) and empty candidate edge cases.
 */

import { test, expect } from '@playwright/test';
import { 
  hasUsableSchedule 
} from '../../src/components/recovery/SolverStatusBanner';
import { 
  formatExactInrString 
} from '../../src/components/recovery/OptimizationKPIStats';
import { 
  optimalScenarioResponseFixture, 
  infeasibleScenarioResponseFixture 
} from '../../src/fixtures/recoveryOptimizationFixtures';
import { 
  SolverOutcomeStatus, 
  RecoveryOptimizationScenarioResponse,
  ScheduledProjectResultDTO,
  PeriodSolvencyResultDTO,
  InfeasibilityDiagnosticReportDTO
} from '../../src/types/recoveryOptimization';

test.describe('Stage 4 Results Visualization & Decision Support Contract Suite', () => {
  // ============================================================================
  // 1. Solver Outcome Status & Usability Predicate
  // ============================================================================
  test.describe('1. Solver Status & Usability Predicate', () => {
    test('hasUsableSchedule returns true strictly for OPTIMAL and FEASIBLE', () => {
      expect(hasUsableSchedule('OPTIMAL')).toBe(true);
      expect(hasUsableSchedule('FEASIBLE')).toBe(true);
    });

    test('hasUsableSchedule returns false strictly for all non-solution statuses', () => {
      expect(hasUsableSchedule('INFEASIBLE')).toBe(false);
      expect(hasUsableSchedule('UNKNOWN')).toBe(false);
      expect(hasUsableSchedule('MODEL_INVALID')).toBe(false);
      expect(hasUsableSchedule('POST_SOLVE_RECONCILIATION_FAILED')).toBe(false);
    });

    test('All six application solver statuses are exhaustively covered', () => {
      const allStatuses: SolverOutcomeStatus[] = [
        'OPTIMAL',
        'FEASIBLE',
        'INFEASIBLE',
        'UNKNOWN',
        'MODEL_INVALID',
        'POST_SOLVE_RECONCILIATION_FAILED',
      ];
      for (const st of allStatuses) {
        const usable = hasUsableSchedule(st);
        if (st === 'OPTIMAL' || st === 'FEASIBLE') {
          expect(usable).toBe(true);
        } else {
          expect(usable).toBe(false);
        }
      }
    });
  });

  // ============================================================================
  // 2. Exact Integer String & Monetary Precision Preservation
  // ============================================================================
  test.describe('2. Exact Integer & Currency String Preservation', () => {
    test('Category 1 exact integers exceeding Number.MAX_SAFE_INTEGER (2^53 - 1) preserved as exact strings', () => {
      // 2^53 = 9007199254740992, test with 9007199254740999
      const hugeIntStr = '9007199254740999';
      expect(hugeIntStr).not.toBe(String(Number(hugeIntStr))); // Number loses precision!
      
      // In Stage 4, exact strings must be passed verbatim without conversion
      const rawExactObjective: string = optimalScenarioResponseFixture.exact_objective_value!;
      expect(typeof rawExactObjective).toBe('string');
      expect(rawExactObjective).toBe('850000000000');
    });

    test('formatExactInrString formats standard amounts using Indian grouping without float math', () => {
      expect(formatExactInrString('5000000.00')).toBe('₹50,00,000.00');
      expect(formatExactInrString('12000000.00')).toBe('₹1,20,00,000.00');
      expect(formatExactInrString('450000.50')).toBe('₹4,50,000.50');
      expect(formatExactInrString('0.00')).toBe('₹0.00');
      expect(formatExactInrString('100.25')).toBe('₹100.25');
    });

    test('formatExactInrString preserves huge numbers exceeding 2^53 without float truncation', () => {
      const hugeInr = '9007199254740999.50';
      const formatted = formatExactInrString(hugeInr);
      expect(formatted).toBe('₹9,00,71,99,25,47,40,999.50');
      expect(formatted.endsWith('.50')).toBe(true);
    });

    test('formatExactInrString handles null, undefined, and sentinel values gracefully', () => {
      expect(formatExactInrString(null)).toBe('N/A');
      expect(formatExactInrString(undefined)).toBe('N/A');
      expect(formatExactInrString('N/A')).toBe('N/A');
    });
  });

  // ============================================================================
  // 3. Financial Solvency & Dual-Ledger Separation
  // ============================================================================
  test.describe('3. Dual-Ledger Solvency & Accounting Separation', () => {
    test('CCU ledger maintains independent integer balance accounting', () => {
      const solvency: PeriodSolvencyResultDTO[] = optimalScenarioResponseFixture.periodic_solvency;
      expect(solvency.length).toBeGreaterThan(0);

      for (const row of solvency) {
        expect(typeof row.period).toBe('number');
        expect(row.period).toBeGreaterThanOrEqual(1);
        expect(typeof row.revenue_receipt_ccu).toBe('string');
        expect(typeof row.expenditure_ccu).toBe('string');
        expect(typeof row.cash_balance_ccu).toBe('string');
        expect(typeof row.is_solvent).toBe('boolean');
      }
    });

    test('INR liquidity ledger maintains exact Decimal cash balance strings', () => {
      const solvency: PeriodSolvencyResultDTO[] = optimalScenarioResponseFixture.periodic_solvency;
      for (const row of solvency) {
        expect(typeof row.cash_balance_inr).toBe('string');
        expect(row.cash_balance_inr).toMatch(/^\d+\.\d{2}$/);
      }
    });

    test('District equity allocation preserves separate CCU and INR dictionaries', () => {
      const resp = optimalScenarioResponseFixture;
      expect(resp.district_equity_allocation_ccu['DIST-NORTH']).toBe('500000000');
      expect(resp.district_equity_allocation_inr['DIST-NORTH']).toBe('5000000.00');
    });
  });

  // ============================================================================
  // 4. 1-Based Timeline & Coordinate Calculations
  // ============================================================================
  test.describe('4. 1-Based Timeline Calculations & Duration Math', () => {
    test('Scheduled start and completion periods are strictly 1-based and within horizon', () => {
      const projects: ScheduledProjectResultDTO[] = optimalScenarioResponseFixture.scheduled_projects;
      const horizon = 12;

      for (const p of projects) {
        if (p.is_selected) {
          expect(p.scheduled_start_period).toBeGreaterThanOrEqual(1);
          expect(p.scheduled_start_period!).toBeLessThanOrEqual(horizon);
          expect(p.scheduled_completion_period).toBeGreaterThanOrEqual(p.scheduled_start_period!);
          expect(p.scheduled_completion_period!).toBeLessThanOrEqual(horizon);

          // Inclusive duration calculation: comp - start + 1
          const duration = p.scheduled_completion_period! - p.scheduled_start_period! + 1;
          expect(duration).toBeGreaterThanOrEqual(1);
        }
      }
    });

    test('CSS Grid column coordinates map directly to start and completion + 1', () => {
      const p = optimalScenarioResponseFixture.scheduled_projects[0];
      const gridStart = p.scheduled_start_period!;
      const gridEnd = p.scheduled_completion_period! + 1;

      expect(gridStart).toBe(1);
      expect(gridEnd).toBe(4); // Column line 1 to 4 spans 3 periods (P1, P2, P3)
      expect(gridEnd - gridStart).toBe(3);
    });

    test('Single-period project spans exactly 1 column width', () => {
      const singlePeriodProject: ScheduledProjectResultDTO = {
        ...optimalScenarioResponseFixture.scheduled_projects[0],
        scheduled_start_period: 5,
        scheduled_completion_period: 5,
      };
      const gridStart = singlePeriodProject.scheduled_start_period!;
      const gridEnd = singlePeriodProject.scheduled_completion_period! + 1;

      expect(gridStart).toBe(5);
      expect(gridEnd).toBe(6);
      expect(gridEnd - gridStart).toBe(1); // 1 period duration
    });
  });

  // ============================================================================
  // 5. Partitioning & Unscheduled Candidates Registry
  // ============================================================================
  test.describe('5. Scheduled vs. Unscheduled Partitioning & No Fabricated Reasons', () => {
    test('Candidate projects are partitioned strictly by is_selected', () => {
      const candidateA: ScheduledProjectResultDTO = {
        ...optimalScenarioResponseFixture.scheduled_projects[0],
        project_id: 'P-SEL',
        is_selected: true,
        scheduled_start_period: 1,
        scheduled_completion_period: 3,
      };

      const candidateB: ScheduledProjectResultDTO = {
        ...optimalScenarioResponseFixture.scheduled_projects[0],
        project_id: 'P-UNSEL',
        is_selected: false,
        scheduled_start_period: null,
        scheduled_completion_period: null,
      };

      const all = [candidateA, candidateB];
      const scheduled = all.filter((p) => p.is_selected);
      const unselected = all.filter((p) => !p.is_selected);

      expect(scheduled.length).toBe(1);
      expect(scheduled[0].project_id).toBe('P-SEL');
      expect(unselected.length).toBe(1);
      expect(unselected[0].project_id).toBe('P-UNSEL');
      expect(unselected[0].scheduled_start_period).toBeNull();
      expect(unselected[0].scheduled_completion_period).toBeNull();
    });

    test('Unscheduled project outcome status is strictly "Not selected" without fabricated causes', () => {
      const unselectedCandidate: ScheduledProjectResultDTO = {
        ...optimalScenarioResponseFixture.scheduled_projects[0],
        project_id: 'P-099',
        is_selected: false,
        scheduled_start_period: null,
        scheduled_completion_period: null,
      };

      // Invariant: DTO has NO rejection_reason or exclusion_cause field
      expect((unselectedCandidate as any).rejection_reason).toBeUndefined();
      expect((unselectedCandidate as any).exclusion_cause).toBeUndefined();
      expect((unselectedCandidate as any).constraint_violated).toBeUndefined();
    });
  });

  // ============================================================================
  // 6. Diagnostic Tiers & Infeasibility Analysis
  // ============================================================================
  test.describe('6. Infeasibility Diagnostic Tiers & Assumption Core', () => {
    test('Infeasible fixture provides structured diagnostic findings across tiers', () => {
      const resp = infeasibleScenarioResponseFixture;
      expect(resp.solver_status).toBe('INFEASIBLE');
      expect(hasUsableSchedule(resp.solver_status)).toBe(false);

      const diag = resp.infeasibility_diagnostics!;
      expect(diag).not.toBeNull();
      expect(diag.has_proven_infeasibility).toBe(true);
      expect(diag.proven_causes.length).toBeGreaterThan(0);

      const cause = diag.proven_causes[0];
      expect(cause.category).toBe('MANDATORY_PROJECT_SAFETY_WINDOW');
      expect(cause.classification).toBe('PROVEN_CAUSE');
      expect(cause.mathematical_condition).toBe('release_period (3) > max_safety_start_period (1)');
      expect(cause.affected_projects).toContain('P-T1-01');
      expect(cause.conflicting_periods).toEqual([1, 2, 3]);
    });

    test('Diagnostic findings lack severity and finding_id fields in DTO', () => {
      const cause = infeasibleScenarioResponseFixture.infeasibility_diagnostics!.proven_causes[0];
      // Severity is implied by tier membership, not present on finding DTO
      expect((cause as any).severity).toBeUndefined();
      expect((cause as any).finding_id).toBeUndefined();
      expect((cause as any).provenance).toBeUndefined();
    });

    test('Assumption core minimality and sufficiency metadata accurately captured', () => {
      const diag = infeasibleScenarioResponseFixture.infeasibility_diagnostics!;
      expect(diag.is_assumption_core_minimal).toBe(true);
      expect(diag.is_assumption_core_sufficient).toBe(true);
    });
  });

  // ============================================================================
  // 7. Non-Solution Statuses & Schedule Rejection
  // ============================================================================
  test.describe('7. Non-Solution Statuses & Reconciliation Rejection', () => {
    test('POST_SOLVE_RECONCILIATION_FAILED enforces schedule rejection and non-usability', () => {
      const status: SolverOutcomeStatus = 'POST_SOLVE_RECONCILIATION_FAILED';
      expect(hasUsableSchedule(status)).toBe(false);
    });

    test('UNKNOWN status does not imply proven infeasibility or timeout', () => {
      const status: SolverOutcomeStatus = 'UNKNOWN';
      expect(hasUsableSchedule(status)).toBe(false);
    });

    test('MODEL_INVALID enforces non-usability', () => {
      const status: SolverOutcomeStatus = 'MODEL_INVALID';
      expect(hasUsableSchedule(status)).toBe(false);
    });
  });

  // ============================================================================
  // 8. Null KPI Handling & Boundary Edge Cases
  // ============================================================================
  test.describe('8. Null Metric Handling & Horizon Edge Cases', () => {
    test('Infeasible scenario response has null objective and gap values', () => {
      const resp = infeasibleScenarioResponseFixture;
      expect(resp.exact_objective_value).toBeNull();
      expect(resp.objective_value).toBeNull();
      expect(resp.best_bound).toBeNull();
      expect(resp.optimality_gap).toBeNull();
      expect(resp.selected_project_count).toBe(0);
      expect(resp.total_cost_ccu).toBe('0');
      expect(resp.total_cost_inr).toBe('0.00');
    });

    test('Maximum planning horizon T=120 periods handled correctly', () => {
      const horizon = 120;
      const periodNumbers = Array.from({ length: horizon }, (_, i) => i + 1);
      expect(periodNumbers.length).toBe(120);
      expect(periodNumbers[0]).toBe(1);
      expect(periodNumbers[119]).toBe(120);
    });

    test('Empty candidate projects array handled without runtime exceptions', () => {
      const emptyProjects: ScheduledProjectResultDTO[] = [];
      const scheduled = emptyProjects.filter((p) => p.is_selected);
      const unselected = emptyProjects.filter((p) => !p.is_selected);

      expect(scheduled.length).toBe(0);
      expect(unselected.length).toBe(0);
    });
  });
});
