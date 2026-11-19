/**
 * DIRS Phase 6D-B Milestone 4 Gate 1: Frontend Data Contracts
 * Recovery Portfolio Optimization TypeScript Types & DTO Definitions.
 *
 * Faithfully mirrors the accepted backend Pydantic v2 DTOs from:
 * backend/app/schemas/recovery_optimization.py
 *
 * Numerical Field Classification Policy:
 * 1. Category 1 (Exact 64-bit integer fields that may exceed Number.MAX_SAFE_INTEGER = 2^53 - 1):
 *    - exact_objective_value, exact_best_bound, conservative_best_bound
 *    - total_cost_ccu, cost_ccu
 *    - district_equity_allocation_ccu values, periodic_expenditures_ccu values
 *    - revenue_receipt_ccu, expenditure_ccu, cash_balance_ccu
 *    Represented as `string` (or `string | null`) to prevent IEEE-754 float truncation.
 *
 * 2. Category 2 (Integer fields proven mathematically bounded within safe range):
 *    - selected_project_count in [0, 500]
 *    - quantized_mcpi_coefficient <= 6 * 10^11 << 2^53 - 1
 *    - duration_periods, release_period, deadline_period, scheduled_start_period,
 *      scheduled_completion_period, period in [1, 120]
 *    - deterministic_seed, num_workers in [1, 16]
 *    Represented as `number` (or `number | null`).
 *
 * 3. Category 3 (Exact monetary Decimals already serialized as strings by backend):
 *    - total_cost_inr, cost_inr, cash_balance_inr
 *    - district_equity_allocation_inr, periodic_expenditures_inr
 *    Represented as `string`.
 *
 * 4. Category 4 (Floating-point fields that are intentionally approximate):
 *    - objective_value, best_bound, optimality_gap, solve_time_seconds
 *    - mcpi_score, raw_mcpi_score, fiscal_retention_rate, period_length_days
 *    Represented as `number` (or `number | null`).
 *
 * Period Indexing: Strictly 1-based discrete indexing [1, T].
 */

// ==============================================================================
// 1. Enums & Unions
// ==============================================================================

export type CurrencyUnit = 'INR' | 'CCU';

export type SolverOutcomeStatus =
  | 'OPTIMAL'
  | 'FEASIBLE'
  | 'INFEASIBLE'
  | 'UNKNOWN'
  | 'MODEL_INVALID'
  | 'POST_SOLVE_RECONCILIATION_FAILED';

export type OptimizationErrorType =
  | 'INVALID_REQUEST'
  | 'PROVEN_INFEASIBILITY'
  | 'SOLVER_TIMEOUT'
  | 'FEASIBLE_SUBOPTIMAL'
  | 'INTERNAL_EXECUTION_FAILURE';

// ==============================================================================
// 2. Nested Request DTOs
// ==============================================================================

/**
 * Candidate recovery project input specification.
 * Mirrors ProjectOptimizationCandidateDTO.
 */
export interface ProjectOptimizationCandidateDTO {
  project_id: string; // 1..100 characters
  project_code: string; // 1..100 characters
  district_id: string; // 1..100 characters
  estimated_cost: string | number; // Decimal >= 0
  duration_periods: number; // Integer >= 1
  cost_currency?: CurrencyUnit; // Default: 'INR'
  release_period?: number; // Integer >= 1, default: 1
  deadline_period?: number | null; // Optional, >= release + duration - 1
  is_tier1_mandatory?: boolean; // Default: false
  raw_mcpi_score?: number; // Float in [0.0, 1.0], default: 0.0
  expenditure_weights?: number[] | null; // Optional disbursement weights summing to > 0
  resource_demands?: Record<string, number>; // Resource ID -> integer demand per active period
  eligible_funds?: string[]; // Optional list of funding source IDs
}

/**
 * Directed precedence dependency between two candidate projects.
 * Mirrors DependencyEdgeDTO.
 */
export interface DependencyEdgeDTO {
  predecessor_id: string;
  successor_id: string;
  lag_periods?: number; // Default: 0, integer >= 0
}

/**
 * Funding source specification under Model B indivisible assignment.
 * Mirrors FundingSourceSpecDTO.
 */
export interface FundingSourceSpecDTO {
  fund_id: string;
  capacity: string | number; // Decimal >= 0
  currency?: CurrencyUnit; // Default: 'INR'
  period_tranches?: Record<number, string | number> | null; // Period (1..T) -> capacity limit
}

// ==============================================================================
// 3. Top-Level Request Contract
// ==============================================================================

/**
 * Complete recovery portfolio optimization scenario request.
 * Mirrors RecoveryOptimizationScenarioRequest.
 */
export interface RecoveryOptimizationScenarioRequest {
  scenario_name: string; // 1..100 characters
  planning_horizon_periods: number; // Integer in [1, 120]
  period_length_days?: number; // Default: 30.0, finite float > 0
  initial_cash?: string | number; // Decimal >= 0, default: '0.0'
  cash_currency?: CurrencyUnit; // Default: 'INR'
  periodic_budgets?: Record<number, string | number>; // Period (1..T) -> amount
  budget_currency?: CurrencyUnit; // Default: 'INR'
  district_equity_targets?: Record<string, number>; // District ID -> quota in [0.0, 1.0]
  blackout_districts?: string[]; // Districts with zero allocation permitted
  candidates: ProjectOptimizationCandidateDTO[]; // Policy ceiling: <= 500 projects
  dependencies?: DependencyEdgeDTO[]; // Precedence edges
  resource_capacities?: Record<string, Record<number, number>>; // Resource -> period -> capacity
  funding_sources?: FundingSourceSpecDTO[]; // Funding sources
  fiscal_retention_rate?: number; // Float in [0.0, 1.0], default: 1.0
  enable_early_start_bonus?: boolean; // Default: true
  max_safety_start_period?: number | null; // Mandatory if any is_tier1_mandatory=true [1, T]
  max_solve_time_seconds?: number; // Default: 60.0, server cap <= 120.0
  deterministic_seed?: number; // Default: 42
  num_workers?: number; // Integer in [1, 16], default: 1
  allow_uniform_weight_fallback?: boolean; // Default: false
}

// ==============================================================================
// 4. Nested Response DTOs
// ==============================================================================

/**
 * Scheduled output specification for a single candidate project.
 * Mirrors ScheduledProjectResultDTO.
 */
export interface ScheduledProjectResultDTO {
  project_id: string;
  project_code: string;
  district_id: string;
  is_selected: boolean;
  scheduled_start_period: number | null; // Integer in [1, T] if selected; null if not selected
  scheduled_completion_period: number | null; // start + duration - 1 if selected; null if not selected
  assigned_funding_source: string | null; // Fund ID if selected; null if not selected
  cost_ccu: string; // Category 1: exact 64-bit integer preserved as string
  cost_inr: string; // Category 3: exact Decimal string (e.g. "5000000.00")
  periodic_expenditures_ccu: Record<string, string>; // Category 1: period string -> exact CCU string
  periodic_expenditures_inr: Record<string, string>; // Category 3: period string -> exact Decimal string
  mcpi_score: number; // Float score
  raw_mcpi_score: number; // Input float score in [0.0, 1.0]
  quantized_mcpi_coefficient: number; // Category 2: integer objective coefficient <= 6*10^11
  is_tier1_mandatory: boolean;
}

/**
 * Period solvency balance outcome.
 * Mirrors PeriodSolvencyResultDTO.
 */
export interface PeriodSolvencyResultDTO {
  period: number; // Discrete period index in [1, T]
  revenue_receipt_ccu: string; // Category 1: exact 64-bit integer preserved as string
  expenditure_ccu: string; // Category 1: exact 64-bit integer preserved as string
  cash_balance_ccu: string; // Category 1: exact 64-bit integer preserved as string
  cash_balance_inr: string; // Category 3: exact Decimal string
  is_solvent: boolean;
}

/**
 * Infeasibility conflict finding.
 * Mirrors InfeasibilityFindingDTO.
 */
export interface InfeasibilityFindingDTO {
  category: string;
  classification: string; // PROVEN_CAUSE, NECESSARY_VIOLATION, HYPOTHESIS, WARNING
  message: string;
  mathematical_condition: string;
  affected_projects: string[];
  conflicting_periods: number[];
  details: Record<string, any>;
}

/**
 * Comprehensive diagnostic report for infeasible or conflicting portfolios.
 * Mirrors InfeasibilityDiagnosticReportDTO.
 */
export interface InfeasibilityDiagnosticReportDTO {
  has_proven_infeasibility: boolean;
  proven_causes: InfeasibilityFindingDTO[];
  necessary_condition_violations: InfeasibilityFindingDTO[];
  solver_hypotheses: InfeasibilityFindingDTO[];
  warnings: InfeasibilityFindingDTO[];
  is_assumption_core_minimal: boolean;
  is_assumption_core_sufficient: boolean;
}

// ==============================================================================
// 5. Top-Level Response Contract
// ==============================================================================

/**
 * Structured API response contract for recovery portfolio optimization.
 * Mirrors RecoveryOptimizationScenarioResponse.
 */
export interface RecoveryOptimizationScenarioResponse {
  scenario_name: string;
  solver_status: SolverOutcomeStatus;
  is_optimal: boolean;
  exact_objective_value: string | null; // Category 1: exact 64-bit integer preserved as string
  exact_best_bound: string | null; // Category 1: exact 64-bit integer preserved as string
  conservative_best_bound: string | null; // Category 1: exact 64-bit integer preserved as string
  objective_value: number | null; // Category 4: approximate float
  best_bound: number | null; // Category 4: approximate float
  optimality_gap: number | null; // Category 4: approximate float (0.0 for OPTIMAL)
  solve_time_seconds: number;
  selected_project_count: number; // Category 2: integer in [0, 500]
  total_cost_ccu: string; // Category 1: exact 64-bit integer preserved as string
  total_cost_inr: string; // Category 3: exact Decimal string
  scheduled_projects: ScheduledProjectResultDTO[];
  periodic_solvency: PeriodSolvencyResultDTO[];
  district_equity_allocation_ccu: Record<string, string>; // Category 1: district -> exact CCU string
  district_equity_allocation_inr: Record<string, string>; // Category 3: district -> exact Decimal string
  input_fingerprint_sha256: string;
  ortools_version: string;
  solver_parameters: Record<string, any>;
  infeasibility_diagnostics: InfeasibilityDiagnosticReportDTO | null;
}

// ==============================================================================
// 6. Structured Error Contract
// ==============================================================================

/**
 * Structured API error response for validation and execution failures.
 * Mirrors OptimizationErrorDetailDTO.
 */
export interface OptimizationErrorDetailDTO {
  error_type: OptimizationErrorType;
  message: string;
  diagnostic_code: string | null; // Populated with X-Correlation-ID
  validation_failures: string[];
  input_fingerprint_sha256: string | null;
  infeasibility_diagnostics: InfeasibilityDiagnosticReportDTO | null;
}

/**
 * Normalization envelope returned by the API client layer.
 */
export interface EvaluatedScenarioResult {
  data: RecoveryOptimizationScenarioResponse;
  correlationId: string | null;
}

export interface OptimizationApiError {
  isOptimizationError: true;
  status: number;
  correlationId: string | null;
  detail: OptimizationErrorDetailDTO;
}
