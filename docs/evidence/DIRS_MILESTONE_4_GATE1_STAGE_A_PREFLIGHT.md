# DIRS PHASE 6D-B — MILESTONE 4
# GATE 1 — STAGE A: CONTRACT VERIFICATION & IMPLEMENTATION PREFLIGHT REPORT
## Preflight Verification for Recovery Portfolio Optimization API Integration

- **Project:** Disaster Intelligence and Response System (DIRS)
- **Phase:** 6D-B (Mathematical Recovery Portfolio Optimization)
- **Milestone:** 4 (Frontend UI Integration & Decision Support)
- **Gate:** Gate 1 (API Client, Data Contracts & Preflight Verification)
- **Stage:** Stage A (Read-Only Contract Verification & Preflight Audit)
- **Date:** 2026-11-17
- **Status:** **STAGE A COMPLETE — STRICTLY READ-ONLY — PLANNING ONLY**
- **Authoritative Report File:** `DIRS_MILESTONE_4_GATE1_STAGE_A_PREFLIGHT.md`

---

## 1. Verified Backend Request Contract

### 1.1 Endpoint Overview
- **HTTP Method:** `POST`
- **Path:** `/api/v1/recovery/optimization/evaluate`
- **Router Location:** `backend/app/routers/recovery_optimization.py:30`
- **Service Handler:** `backend/app/recovery/services/recovery_optimization_service.py:69`
- **Execution Model:** Synchronous AnyIO worker thread (`starlette.concurrency.run_in_threadpool`, non-blocking to asyncio event loop)
- **Database Dependency:** Strictly **zero** database session injected; zero DML operations executed
- **HTTP Headers Required:**
  - `Content-Type: application/json`
  - `Authorization: Bearer <JWT>`
- **HTTP Headers Emitted:**
  - `X-Correlation-ID: <UUID v4>` (server-generated on every request)

### 1.2 Top-Level Request Schema (`RecoveryOptimizationScenarioRequest`)
*Source:* `backend/app/schemas/recovery_optimization.py:254-437`

| Field Name | Python Type | JSON Type | Mandatory? | Default Value | Constraints & Validation Invariants | Classification |
| :--- | :--- | :--- | :---: | :--- | :--- | :---: |
| `scenario_name` | `str` | `string` | **Yes** | *None* | `min_length=1`, `max_length=100` | **VERIFIED FACT** |
| `planning_horizon_periods` | `int` | `number` | **Yes** | *None* | Discrete periods $T \in [1, 120]$ | **VERIFIED FACT** |
| `period_length_days` | `float` | `number` | No | `30.0` | Finite float $> 0.0$ (recharts/calendar scaling) | **VERIFIED FACT** |
| `initial_cash` | `Decimal` | `string` / `number` | No | `Decimal("0.0")` | Finite decimal $\ge 0.0$ | **VERIFIED FACT** |
| `cash_currency` | `CurrencyUnit` | `string` | No | `"INR"` | Enum: `"INR"` or `"CCU"` | **VERIFIED FACT** |
| `periodic_budgets` | `Dict[int, Decimal]` | `object` (`string: string`) | No | `{}` | Key $t \in [1, T]$, value finite decimal $\ge 0.0$ | **VERIFIED FACT** |
| `budget_currency` | `CurrencyUnit` | `string` | No | `"INR"` | Enum: `"INR"` or `"CCU"` | **VERIFIED FACT** |
| `district_equity_targets` | `Dict[str, float]` | `object` (`string: number`) | No | `{}` | Quota $\theta_d \in [0.0, 1.0]$, sum $\le 1.000001$ | **VERIFIED FACT** |
| `blackout_districts` | `List[str]` | `array` (`string[]`) | No | `[]` | District codes with active budget blackouts | **VERIFIED FACT** |
| `candidates` | `List[Project...]` | `array` (`object[]`) | No | `[]` | Policy ceiling: $\le 500$ projects (HTTP 422 if $> 500$) | **VERIFIED FACT** |
| `dependencies` | `List[Dependency...]` | `array` (`object[]`) | No | `[]` | Directed precedence edges; DAG must be acyclic | **VERIFIED FACT** |
| `resource_capacities` | `Dict[str, Dict[int, int]]` | `object` | No | `{}` | `resource_type -> {period (1..T) -> capacity (>=0)}` | **VERIFIED FACT** |
| `funding_sources` | `List[Funding...]` | `array` (`object[]`) | No | `[]` | Model B indivisible funding specs | **VERIFIED FACT** |
| `fiscal_retention_rate` | `float` | `number` | No | `1.0` | Finite float $\in [0.0, 1.0]$ | **VERIFIED FACT** |
| `enable_early_start_bonus` | `bool` | `boolean` | No | `true` | Secondary non-compensatory acceleration incentive | **VERIFIED FACT** |
| `max_safety_start_period` | `Optional[int]` | `number` / `null` | **Conditional** | `null` | **Mandatory if any candidate has `is_tier1_mandatory=true`** ($1 \le T_{\text{safety}} \le T$) | **VERIFIED FACT** |
| `max_solve_time_seconds` | `float` | `number` | No | `60.0` | Finite float $> 0.0$; server cap $\le 120.0$ (HTTP 422 if $> 120.0$) | **VERIFIED FACT** |
| `deterministic_seed` | `int` | `number` | No | `42` | CP-SAT random seed $\ge 0$ | **VERIFIED FACT** |
| `num_workers` | `int` | `number` | No | `1` | CP-SAT search threads $\in [1, 16]$ | **VERIFIED FACT** |
| `allow_uniform_weight_fallback` | `bool` | `boolean` | No | `false` | Explicit opt-in for uniform disbursement generation | **VERIFIED FACT** |

*Critical Contract Invariant (`model_config = ConfigDict(extra="forbid")`):*  
Pydantic v2 strictly rejects any JSON payload containing undeclared fields with an immediate HTTP 422 `extra_forbidden` error.

---

## 2. Verified Backend Response Contract

### 2.1 Top-Level Response Schema (`RecoveryOptimizationScenarioResponse`)
*Source:* `backend/app/schemas/recovery_optimization.py:624-787`

| Field Name | Python Type | JSON Wire Format | Nullable? | Invariant Across Solver Outcomes | Classification |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `scenario_name` | `str` | `string` | No | Matches request `scenario_name` | **VERIFIED FACT** |
| `solver_status` | `str` | `string` | No | One of: `"OPTIMAL"`, `"FEASIBLE"`, `"INFEASIBLE"`, `"UNKNOWN"`, `"MODEL_INVALID"`, `"POST_SOLVE_RECONCILIATION_FAILED"` | **VERIFIED FACT** |
| `is_optimal` | `bool` | `boolean` | No | `true` ONLY if `solver_status == "OPTIMAL"`, `false` otherwise | **VERIFIED FACT** |
| `exact_objective_value` | `Optional[int]` | `number` (64-bit int) | Yes | Non-null on `OPTIMAL` and `FEASIBLE`; `null` on `INFEASIBLE`, `UNKNOWN`, `MODEL_INVALID` | **VERIFIED FACT** |
| `exact_best_bound` | `Optional[int]` | `number` (64-bit int) | Yes | Equals `exact_objective_value` on `OPTIMAL`; `null` on non-solution | **VERIFIED FACT** |
| `conservative_best_bound`| `Optional[int]` | `number` (64-bit int) | Yes | Conservative integer upper bound; $\ge \text{exact\_objective}$ on `FEASIBLE` | **VERIFIED FACT** |
| `objective_value` | `Optional[float]` | `number` (float) | Yes | Float approximation; `null` on non-solution | **VERIFIED FACT** |
| `best_bound` | `Optional[float]` | `number` (float) | Yes | Float approximation; `null` on non-solution | **VERIFIED FACT** |
| `optimality_gap` | `Optional[float]` | `number` (float) | Yes | `0.0` on `OPTIMAL`, $\ge 0.0$ on `FEASIBLE`, `null` on non-solution | **VERIFIED FACT** |
| `solve_time_seconds` | `float` | `number` | No | Measured wall-clock solve time in seconds | **VERIFIED FACT** |
| `selected_project_count` | `int` | `number` | No | Integer count $\ge 0$; strictly `0` on non-solution | **VERIFIED FACT** |
| `total_cost_ccu` | `int` | `number` | No | Total integer cost in Currency Cost Units; `0` on non-solution | **VERIFIED FACT** |
| `total_cost_inr` | `Decimal` | `string` (exact) | No | Exact INR currency string; `"0"` on non-solution | **VERIFIED FACT** |
| `scheduled_projects` | `List[Scheduled...]` | `array` (`object[]`) | No | Project results; zero selected projects on non-solution | **VERIFIED FACT** |
| `periodic_solvency` | `List[Period...]` | `array` (`object[]`) | No | Periodic cash balances and solvency statuses | **VERIFIED FACT** |
| `district_equity_allocation_ccu` | `Dict[str, int]` | `object` (`string: number`) | No | District code -> integer CCU allocated | **VERIFIED FACT** |
| `district_equity_allocation_inr` | `Dict[str, Decimal]` | `object` (`string: string`) | No | District code -> exact INR string allocated | **VERIFIED FACT** |
| `input_fingerprint_sha256` | `str` | `string` | No | Canonical SHA-256 hash of incoming scenario payload | **VERIFIED FACT** |
| `ortools_version` | `str` | `string` | No | e.g. `"9.14.6206"` | **VERIFIED FACT** |
| `solver_parameters` | `Dict[str, Any]` | `object` | No | Key-value dictionary of solver telemetry parameters | **VERIFIED FACT** |
| `infeasibility_diagnostics` | `Optional[Report...]` | `object` / `null` | Yes | Populated on `INFEASIBLE`, `MODEL_INVALID`, `POST_SOLVE_RECONCILIATION_FAILED`; `null` on `OPTIMAL`/`FEASIBLE` | **VERIFIED FACT** |

---

## 3. Exact Nested DTO Structures

### 3.1 `ProjectOptimizationCandidateDTO`
*Source:* `backend/app/schemas/recovery_optimization.py:54-160`

```typescript
interface ProjectOptimizationCandidateDTO {
  project_id: string;                         // 1..100 characters (Unique key)
  project_code: string;                       // 1..100 characters
  district_id: string;                        // 1..100 characters
  estimated_cost: string | number;            // Sent as string or number; validated as Decimal >= 0
  duration_periods: number;                   // Integer >= 1
  cost_currency?: "INR" | "CCU";              // Default: "INR"
  release_period?: number;                    // Default: 1, range: [1, T]
  deadline_period?: number | null;            // Optional, range: [release + duration - 1, T]
  is_tier1_mandatory?: boolean;               // Default: false
  raw_mcpi_score?: number;                    // Float in [0.0, 1.0], default: 0.0
  expenditure_weights?: number[] | null;      // Optional, length == duration_periods, sum > 0
  resource_demands?: Record<string, number>;  // Resource ID -> integer demand per period (>= 0)
  eligible_funds?: string[];                  // Optional list of fund IDs
}
```

### 3.2 `DependencyEdgeDTO`
*Source:* `backend/app/schemas/recovery_optimization.py:217-248`

```typescript
interface DependencyEdgeDTO {
  predecessor_id: string;                     // Candidate project ID
  successor_id: string;                       // Candidate project ID (cannot equal predecessor_id)
  lag_periods?: number;                       // Default: 0, integer >= 0
}
```

### 3.3 `FundingSourceSpecDTO`
*Source:* `backend/app/schemas/recovery_optimization.py:161-216`

```typescript
interface FundingSourceSpecDTO {
  fund_id: string;                            // Unique funding source identifier
  capacity: string | number;                  // Capital capacity; validated as Decimal >= 0
  currency?: "INR" | "CCU";                   // Default: "INR"
  period_tranches?: Record<number, string | number> | null; // Optional period (1..T) -> tranche limit
}
```

### 3.4 `ScheduledProjectResultDTO`
*Source:* `backend/app/schemas/recovery_optimization.py:500-544`

```typescript
interface ScheduledProjectResultDTO {
  project_id: string;
  project_code: string;
  district_id: string;
  is_selected: boolean;
  scheduled_start_period: number | null;      // Integer in [1, T] if selected; null if not selected
  scheduled_completion_period: number | null; // start + duration - 1 if selected; null if not selected
  assigned_funding_source: string | null;     // Fund ID if selected; null if not selected
  cost_ccu: number;                           // Normalized cost in CCU
  cost_inr: string;                           // Wire format: exact Decimal string (e.g. "5000000.00")
  periodic_expenditures_ccu: Record<string, number>; // Period string -> CCU integer
  periodic_expenditures_inr: Record<string, string>; // Period string -> exact Decimal string
  mcpi_score: number;                         // Normalized MCPI score
  raw_mcpi_score: number;                     // Input raw MCPI score
  quantized_mcpi_coefficient: number;         // Integer objective coefficient
  is_tier1_mandatory: boolean;
}
```

### 3.5 `PeriodSolvencyResultDTO`
*Source:* `backend/app/schemas/recovery_optimization.py:546-568`

```typescript
interface PeriodSolvencyResultDTO {
  period: number;                             // Integer in [1, T]
  revenue_receipt_ccu: number;
  expenditure_ccu: number;
  cash_balance_ccu: number;
  cash_balance_inr: string;                   // Wire format: exact Decimal string
  is_solvent: boolean;
}
```

### 3.6 Infeasibility Diagnostic Structures
*Source:* `backend/app/schemas/recovery_optimization.py:570-618`

```typescript
interface InfeasibilityFindingDTO {
  category: string;                           // e.g. "FINANCIAL_SOLVENCY", "PRECEDENCE_CYCLE"
  classification: string;                     // "PROVEN_CAUSE", "NECESSARY_VIOLATION", "HYPOTHESIS"
  message: string;
  mathematical_condition: string;             // Exact LaTeX / equation condition
  affected_projects: string[];
  conflicting_periods: number[];
  details: Record<string, any>;
}

interface InfeasibilityDiagnosticReportDTO {
  has_proven_infeasibility: boolean;
  proven_causes: InfeasibilityFindingDTO[];
  necessary_condition_violations: InfeasibilityFindingDTO[];
  solver_hypotheses: InfeasibilityFindingDTO[];
  warnings: InfeasibilityFindingDTO[];
  is_assumption_core_minimal: boolean;        // false (not claimed minimal)
  is_assumption_core_sufficient: boolean;     // true
}
```

### 3.7 `OptimizationErrorDetailDTO` (HTTP 500 & Unhandled Failures)
*Source:* `backend/app/schemas/recovery_optimization.py:793-811`

```typescript
interface OptimizationErrorDetailDTO {
  error_type: "INVALID_REQUEST" | "PROVEN_INFEASIBILITY" | "SOLVER_TIMEOUT" | "FEASIBLE_SUBOPTIMAL" | "INTERNAL_EXECUTION_FAILURE";
  message: string;
  diagnostic_code: string | null;             // Matches X-Correlation-ID
  validation_failures: string[];
  input_fingerprint_sha256: string | null;
  infeasibility_diagnostics: InfeasibilityDiagnosticReportDTO | null;
}
```

---

## 4. RSK-M2-07 Evidence & Resolution of Indexing Discrepancy

### 4.1 Exhaustive Source Verification
Direct inspection of the executable codebase was conducted across all relevant files:

1. **M2B Engine Pre-Solve Validation (`backend/app/recovery/optimization/recovery_optimization_orchestrator.py:185-195`):**
   ```python
   has_mandatory = any(c.is_tier1_mandatory for c in request.candidates)
   if has_mandatory:
       if request.max_safety_start_period is None:
           errors.append("Request contains mandatory life-safety projects but max_safety_start_period (T_safety_max) is None...")
       elif request.max_safety_start_period < 1 or request.max_safety_start_period > request.planning_horizon_periods:
           errors.append(f"max_safety_start_period ({request.max_safety_start_period}) must be between 1 and planning_horizon_periods ({request.planning_horizon_periods}).")
   ```
   *Verified Fact:* The engine strictly rejects any value $< 1$ or $> T$. Discrete planning periods are **strictly 1-based** ($[1, T]$).

2. **Gate 1 Pydantic DTO Validation (`backend/app/schemas/recovery_optimization.py:293` & `363-390`):**
   ```python
   max_safety_start_period: Optional[int] = Field(default=None, ge=1, description="...")
   ```
   *Verified Fact:* Field-level constraint `ge=1` unconditionally rejects `0` or negative values. Model validator rejects values $> T$.

3. **CP-SAT Solver Hard Constraint (`backend/app/recovery/optimization/recovery_cpsat_solver.py:465-475`):**
   Variables $x_{j, s}$ are indexed for periods $s \in [1, T]$. Period 1 represents the first discrete time slice.

4. **Boundary Test Verification (`tests/backend/test_phase6d_api_schemas.py:540` & `tests/backend/test_phase6d_api_route.py:340`):**
   - Value `0` raises `Input should be greater than or equal to 1`.
   - Value $T + 1$ raises `max_safety_start_period exceeds planning_horizon_periods`.

5. **Period-Indexed Fields Consistency Comparison:**
   | Period Field | Domain in Running Code | Minimum Value | Maximum Value |
   | :--- | :---: | :---: | :---: |
   | `planning_horizon_periods` ($T$) | Positive integer | $1$ | $120$ |
   | `release_period` | Discrete period | $1$ | $T$ |
   | `deadline_period` | Discrete period | $1$ | $T$ |
   | `scheduled_start_period` | Discrete period | $1$ | $T$ |
   | `scheduled_completion_period`| Discrete period | $1$ | $T$ |
   | `periodic_budgets` keys | Discrete period | $1$ | $T$ |
   | `resource_capacities` keys | Discrete period | $1$ | $T$ |
   | `max_safety_start_period` | Discrete period | $1$ | $T$ |

### 4.2 Resolution of Earlier Audit Narrative Conflict
- **Finding:** Every single period-indexed field across the entire executable codebase (engine, solver, schemas, DTOs, tests) uses **1-based indexing** ($[1, T]$).
- **The Discrepancy:** The earlier Gate 1 audit narrative statement claiming periods are 0-based ($[0, H-1]$) was a **typographical documentation error** in that report. There is zero 0-based period indexing anywhere in the executable Python code.
- **RECOMMENDATION:** Formally log in Milestone 4 documentation that the system is 100% unified on **1-based planning periods ($[1, T]$)** matching the executable engine, and update the audit records accordingly without altering running code.

---

## 5. Numerical Serialization Findings & Lossless Transport Strategy

### 5.1 Verification of Backend JSON Serialization Behavior
Inspection of `tests/backend/test_phase6d_api_route.py` (`test_12` and `test_13`) establishes the wire-level JSON representation:

1. **Monetary Decimal Fields:**
   - Fields: `total_cost_inr`, `cost_inr`, `periodic_expenditures_inr`, `district_equity_allocation_inr`, `cash_balance_inr`.
   - Wire representation: **Emitted as exact JSON strings** (e.g. `"9876543210.123456789012345678"`).
   - *Status:* **Inherently lossless.** Standard JavaScript `JSON.parse` preserves these as strings without precision loss.

2. **64-Bit Integer Objective & Bound Fields:**
   - Fields: `exact_objective_value`, `exact_best_bound`, `conservative_best_bound`.
   - Wire representation: **Emitted as bare JSON numbers** (e.g. `18014398509491983` in `test_12`).
   - *The JavaScript Constraint:* Standard JavaScript represents all JSON numbers as IEEE-754 double-precision floats. The maximum safe integer is:
     $$\text{Number.MAX\_SAFE\_INTEGER} = 2^{53} - 1 = 9,007,199,254,740,991$$
   - Any bare integer $> 2^{53}-1$ tokenized by standard `JSON.parse` is rounded by the JavaScript engine *before* any reviver function can inspect it.
   - Converting an already-rounded number to `BigInt(val)` simply preserves the corrupted value.

### 5.2 Realistic Magnitude Analysis
In `RecoveryCPSATSolver`, the objective function is:
$$\text{Term}_j = (M_{\text{accel}} \cdot \bar{\Pi}_j) \cdot w_j$$
Where:
- $\bar{\Pi}_j = \lfloor \text{raw\_mcpi} \times 10^7 \rfloor \le 10^7$
- $M_{\text{accel}} = N \cdot (T - 1) + 1$
- For policy maximums ($N = 500$ projects, $T = 120$ periods):
  $$M_{\text{accel}} = 500 \times 119 + 1 = 59,501$$
  $$\text{Max Term}_j = 59,501 \times 10^7 \approx 5.95 \times 10^{11}$$
  $$\text{Max Objective} \approx 500 \times 5.95 \times 10^{11} \approx 2.975 \times 10^{14}$$
Notice that $2.975 \times 10^{14} < 9.007 \times 10^{15}$ ($\approx 3.3\%$ of `MAX_SAFE_INTEGER`). Under standard realistic disaster recovery scenarios, objective values remain safely within JavaScript's safe integer range.

However, artificial unit tests (`test_12` uses $2^{54} + 9999$) or large budget coefficients can exceed $2^{53}-1$.

### 5.3 Recommended Frontend Lossless Strategy
To guarantee 100% numerical safety without adding new npm packages or modifying the backend:

**Axios Custom Response Transformer (Regex Pre-Quoting):**
Configure `transformResponse` on the recovery optimization API call to quote bare integer objective values in the raw HTTP response string *before* passing to `JSON.parse`:
```typescript
const losslessResponseTransformer = (rawText: string): any => {
  if (typeof rawText !== 'string') return rawText;
  // Safely quote exact integer objective and bound fields before JSON.parse tokenization
  const quoted = rawText.replace(
    /"(exact_objective_value|exact_best_bound|conservative_best_bound)":\s*(-?\d+)/g,
    '"$1": "$2"'
  );
  return JSON.parse(quoted);
};
```
- **How It Works:** Transforms `"exact_objective_value": 18014398509491983` into `"exact_objective_value": "18014398509491983"`.
- **Result:** `JSON.parse` treats it as a string token, completely bypassing IEEE-754 float conversion.
- **Frontend Type:** Typed in TypeScript as `string | null` (or parsed losslessly via `BigInt(val)`).
- **Classification:** **RECOMMENDATION.** Completely self-contained, zero new dependencies, 100% lossless.

---

## 6. Authentication and Role Findings

### 6.1 Existing Frontend Security Architecture
- **JWT Storage:** `localStorage.getItem('dirs_token')` (`frontend/src/context/AuthContext.tsx:25`).
- **Axios Interceptor:** Injects `Authorization: Bearer <token>` automatically on all requests (`frontend/src/api/client.ts:12-17`).
- **Token Refresh:** **Does not exist.** The backend issues tokens with standard expiry (1440 minutes / 24 hours); no refresh token endpoint exists.
- **Session Expiry Handling:** If `/auth/me` returns 401, `AuthContext` calls `logout()`, removing the token and clearing state.
- **API Error Handling:** If the evaluate endpoint returns 401 or 403, Axios throws an error containing `err.response.status`.

### 6.2 The `ADMIN` Role Access Discrepancy
Direct inspection reveals a front-to-back role type mismatch:

1. **Backend Route (`backend/app/routers/recovery_optimization.py:51`):**
   ```python
   current_user: User = Depends(require_any_role(["GOVT", "ADMIN"]))
   ```
   Both `GOVT` and `ADMIN` users are authorized to evaluate recovery portfolios.

2. **Frontend User Profile (`frontend/src/context/AuthContext.tsx:8`):**
   ```typescript
   export interface UserProfile {
     role: 'CITIZEN' | 'VOLUNTEER' | 'NGO' | 'GOVT'; // 'ADMIN' is missing!
   }
   ```

3. **Frontend Route Protection (`frontend/src/App.tsx:22`):**
   ```typescript
   if (allowedRoles && !allowedRoles.includes(user.role) && user.role !== 'GOVT') {
     return <Navigate to="/citizen" replace />;
   }
   ```
   Because `ADMIN` is not in `allowedRoles` and `user.role !== 'GOVT'` is true, an Admin user is redirected to `/citizen`.

4. **Frontend Sidebar (`frontend/src/components/layout/Sidebar.tsx:46`):**
   `roleNavItems` has no entry for `'ADMIN'`, defaulting an Admin to the Citizen menu items.

- **RECOMMENDATION (Stage B):** Add `'ADMIN'` to `UserProfile.role` in `AuthContext.tsx`, configure the new recovery route with `allowedRoles={['GOVT', 'ADMIN']}`, and ensure Admin users see the Command Center / Recovery sidebar options.

---

## 7. Recommended TypeScript Types

The following types should be created in `frontend/src/types/recoveryOptimization.ts` during Stage B:

```typescript
// ==============================================================================
// Enums & Core Types
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
// Nested Request Types
// ==============================================================================

export interface ProjectOptimizationCandidateDTO {
  project_id: string;
  project_code: string;
  district_id: string;
  estimated_cost: string | number;
  duration_periods: number;
  cost_currency?: CurrencyUnit;
  release_period?: number;
  deadline_period?: number | null;
  is_tier1_mandatory?: boolean;
  raw_mcpi_score?: number;
  expenditure_weights?: number[] | null;
  resource_demands?: Record<string, number>;
  eligible_funds?: string[];
}

export interface DependencyEdgeDTO {
  predecessor_id: string;
  successor_id: string;
  lag_periods?: number;
}

export interface FundingSourceSpecDTO {
  fund_id: string;
  capacity: string | number;
  currency?: CurrencyUnit;
  period_tranches?: Record<number, string | number> | null;
}

// ==============================================================================
// Top-Level Request Contract
// ==============================================================================

export interface RecoveryOptimizationScenarioRequest {
  scenario_name: string;
  planning_horizon_periods: number;
  period_length_days?: number;
  initial_cash?: string | number;
  cash_currency?: CurrencyUnit;
  periodic_budgets?: Record<number, string | number>;
  budget_currency?: CurrencyUnit;
  district_equity_targets?: Record<string, number>;
  blackout_districts?: string[];
  candidates: ProjectOptimizationCandidateDTO[];
  dependencies?: DependencyEdgeDTO[];
  resource_capacities?: Record<string, Record<number, number>>;
  funding_sources?: FundingSourceSpecDTO[];
  fiscal_retention_rate?: number;
  enable_early_start_bonus?: boolean;
  max_safety_start_period?: number | null;
  max_solve_time_seconds?: number;
  deterministic_seed?: number;
  num_workers?: number;
  allow_uniform_weight_fallback?: boolean;
}

// ==============================================================================
// Nested Response Types
// ==============================================================================

export interface ScheduledProjectResultDTO {
  project_id: string;
  project_code: string;
  district_id: string;
  is_selected: boolean;
  scheduled_start_period: number | null;
  scheduled_completion_period: number | null;
  assigned_funding_source: string | null;
  cost_ccu: number;
  cost_inr: string; // Exact Decimal string
  periodic_expenditures_ccu: Record<string, number>;
  periodic_expenditures_inr: Record<string, string>; // Exact Decimal string
  mcpi_score: number;
  raw_mcpi_score: number;
  quantized_mcpi_coefficient: number;
  is_tier1_mandatory: boolean;
}

export interface PeriodSolvencyResultDTO {
  period: number;
  revenue_receipt_ccu: number;
  expenditure_ccu: number;
  cash_balance_ccu: number;
  cash_balance_inr: string; // Exact Decimal string
  is_solvent: boolean;
}

export interface InfeasibilityFindingDTO {
  category: string;
  classification: string;
  message: string;
  mathematical_condition: string;
  affected_projects: string[];
  conflicting_periods: number[];
  details: Record<string, any>;
}

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
// Top-Level Response Contract
// ==============================================================================

export interface RecoveryOptimizationScenarioResponse {
  scenario_name: string;
  solver_status: SolverOutcomeStatus;
  is_optimal: boolean;
  exact_objective_value: string | number | null; // String if regex-prequoted
  exact_best_bound: string | number | null;
  conservative_best_bound: string | number | null;
  objective_value: number | null;
  best_bound: number | null;
  optimality_gap: number | null;
  solve_time_seconds: number;
  selected_project_count: number;
  total_cost_ccu: number;
  total_cost_inr: string; // Exact Decimal string
  scheduled_projects: ScheduledProjectResultDTO[];
  periodic_solvency: PeriodSolvencyResultDTO[];
  district_equity_allocation_ccu: Record<string, number>;
  district_equity_allocation_inr: Record<string, string>; // Exact Decimal string
  input_fingerprint_sha256: string;
  ortools_version: string;
  solver_parameters: Record<string, any>;
  infeasibility_diagnostics: InfeasibilityDiagnosticReportDTO | null;
}

export interface OptimizationErrorDetailDTO {
  error_type: OptimizationErrorType;
  message: string;
  diagnostic_code: string | null;
  validation_failures: string[];
  input_fingerprint_sha256: string | null;
  infeasibility_diagnostics: InfeasibilityDiagnosticReportDTO | null;
}

export interface EvaluatedScenarioResult {
  data: RecoveryOptimizationScenarioResponse;
  correlationId: string;
}
```

---

## 8. Exact Proposed Implementation File List for Gate 1

Stage B of Gate 1 will create or modify **strictly the minimal set of frontend contract files**:

| Action | File Path | Purpose & Responsibilities |
| :--- | :--- | :--- |
| **CREATE** | `frontend/src/types/recoveryOptimization.ts` | Complete TypeScript type definitions for all request, response, error, and nested DTOs. |
| **CREATE** | `frontend/src/api/recoveryOptimization.ts` | Typed Axios caller `evaluateRecoveryOptimizationScenario`, correlation ID extraction, error normalizer, and lossless integer regex pre-quoter. |
| **CREATE** | `frontend/src/fixtures/recoveryOptimizationFixtures.ts` | Static contract test fixtures: (1) Minimal valid scenario, (2) Mandatory safety deadline scenario, (3) Mock OPTIMAL response, (4) Mock INFEASIBLE diagnostic response. |
| **MODIFY** | `frontend/src/context/AuthContext.tsx` | Add `'ADMIN'` to `UserProfile.role` union so Admin users match backend authorization. |

**Prohibitions Maintained:**
- Zero UI components (no forms, buttons, cards, Gantt views).
- Zero new package dependencies installed.
- Zero changes to backend files, database models, or migrations.

---

## 9. Risk Register & Owner Decisions Required

| Risk ID | Severity | Description | Mitigation Strategy | Owner Decision Required? |
| :--- | :---: | :--- | :--- | :---: |
| **RSK-G1-01** | **HIGH** | `ADMIN` role blocked by frontend `ProtectedRoute`. | Add `'ADMIN'` to `UserProfile.role` and `allowedRoles`. | **No** (Direct alignment with backend). |
| **RSK-G1-02** | **MEDIUM** | Large integer objective truncation ($> 2^{53}-1$) in JS. | Regex pre-quoting in Axios `transformResponse` to parse as string. | **No** (Frontend-only lossless strategy). |
| **RSK-G1-03** | **LOW** | Off-by-one error on RSK-M2-07 safety deadline. | Enforce $1 \le T_{\text{safety}} \le T$ validation in TypeScript. | **No** (Direct alignment with engine). |
| **RSK-G1-04** | **POLICY** | Pre-packaged scenario templates vs live database ingestion. | Provide curated scenario templates in Stage B fixtures. | **YES: OWNER DECISION** (Confirm template presets). |

---

## 10. File Integrity and Read-Only Confirmation

During this Stage A preflight verification:
- **Source files modified:** **ZERO (0)**
- **Source files created:** **ZERO (0)** (Excluding this preflight report file)
- **Files deleted or renamed:** **ZERO (0)**
- **Dependencies installed:** **ZERO (0)**
- **Database migrations executed:** **ZERO (0)**
- **Database writes executed:** **ZERO (0)**

All baseline backend hashes remain intact:
- `backend/app/recovery/services/recovery_optimization_service.py`: `5507fe4ca226479bc11b0508d3be64cc53c772af5ec8e9206c2ff8b0cd82311f` (**MATCH**)
- `backend/app/routers/recovery_optimization.py`: `b41e38e440e12bdfa2293a6f15c9aeb653bc0687aaf56eacff48ccaee1d06950` (**MATCH**)
- `backend/app/main.py`: `43757d9eab03cdf38db73b60e64d831681e245376b0c562be1618c5ac2484fd8` (**MATCH**)
- `backend/app/schemas/recovery_optimization.py`: `c6983353ca041d3b1b2049d50c4bc51d14061a875685d9555fc9c8da4e4aa9cd` (**MATCH**)
- `tests/backend/test_phase6d_api_schemas.py`: `10679420a6cea81fb6b4e4102b2220410c7cd731f401f0a32c3e526d438c2c46` (**MATCH**)
- `tests/backend/test_phase6d_api_route.py`: `def21b0cc4c1d1ff084937db4a23e5c1e75084a33ce034704f6f2cb4add23a8e` (**MATCH**)

---

## 11. Final Governance Stop Condition

Milestone 4 Gate 1 Stage A (Preflight Verification) is complete.

**GOVERNANCE STOP:**
- No frontend source files have been created or modified.
- Stage B implementation has **strictly NOT been started**.
- Standing by for Project Owner review and explicit authorization to proceed with Gate 1 Stage B implementation. **STOP.**
