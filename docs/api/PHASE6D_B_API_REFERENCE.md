# DIRS Phase 6D-B: REST API Reference Manual

**Subsystem:** Disaster Intelligence and Response System (DIRS)  
**Phase:** 6D-B — Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine  
**Milestone:** Milestone 6 — Final Architecture Treatise & Permanent Freeze  
**Status:** Certified & Frozen  
**Date:** November 2026  

---

## 1. Overview & Protocol Specification

The Phase 6D-B API exposes high-performance combinatorial recovery portfolio evaluation capabilities via JSON-over-HTTPS.

- **Base URL:** `/api/v1`
- **Primary Endpoint:** `POST /api/v1/recovery/optimization/evaluate`
- **Protocol:** HTTP/1.1 and HTTP/2
- **Authentication:** Bearer JWT in `Authorization: Bearer <token>`
- **Tracking Header:** `X-Correlation-ID: <uuid>` (client or server generated)
- **Content Type:** `application/json; charset=utf-8`

---

## 2. API Endpoint Specification

### `POST /recovery/optimization/evaluate`

Evaluates a multi-period recovery portfolio against budget cash flows, district equity quotas, predecessor project dependencies, and renewable resource constraints using Google OR-Tools CP-SAT.

#### Request Headers
| Header | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `Authorization` | String | Yes | Bearer JWT containing authenticated user credentials (`ADMIN` or `GOVT`). |
| `Content-Type` | String | Yes | Must be `application/json`. |
| `X-Correlation-ID` | String (UUIDv4) | Optional | Distributed trace ID for end-to-end auditability. |

#### Request Payload Structure (`RecoveryOptimizationScenarioRequest`)

```json
{
  "scenario_name": "Post-Monsoon Infrastructure Recovery Plan 2026",
  "planning_horizon_periods": 24,
  "period_length_days": 30.0,
  "initial_cash": "50000000.00",
  "cash_currency": "INR",
  "periodic_budgets": {
    "1": "25000000.00",
    "2": "25000000.00",
    "3": "20000000.00"
  },
  "budget_currency": "INR",
  "district_equity_targets": {
    "DIST_WAYANAD": 0.35,
    "DIST_IDUKKI": 0.25
  },
  "blackout_districts": [
    "DIST_KOZHIKODE"
  ],
  "candidates": [
    {
      "project_id": "PRJ_WAY_001",
      "project_code": "WAY-ROAD-01",
      "district_id": "DIST_WAYANAD",
      "estimated_cost": "12000000.00",
      "duration_periods": 3,
      "cost_currency": "INR",
      "release_period": 1,
      "deadline_period": 12,
      "is_tier1_mandatory": true,
      "raw_mcpi_score": 0.925,
      "resource_demands": {
        "EXCAVATOR": 4,
        "STRUCTURAL_ENGINEER": 2
      },
      "expenditure_weights": {
        "1": 0.5,
        "2": 0.3,
        "3": 0.2
      }
    }
  ],
  "dependencies": [
    {
      "predecessor_id": "PRJ_WAY_001",
      "successor_id": "PRJ_WAY_002",
      "lag_periods": 1
    }
  ],
  "resource_capacities": {
    "EXCAVATOR": { "1": 10, "2": 10, "3": 10 },
    "STRUCTURAL_ENGINEER": { "1": 6, "2": 6, "3": 6 }
  },
  "funding_sources": [],
  "fiscal_retention_rate": 0.95,
  "enable_early_start_bonus": true,
  "max_safety_start_period": 4,
  "max_solve_time_seconds": 60.0,
  "deterministic_seed": 42,
  "num_workers": 4,
  "allow_uniform_weight_fallback": true
}
```

#### Request Validation Invariants
1. **Candidate Ceiling Cap:** Maximum candidates $N \le 500$. Submitting $N \ge 501$ produces an immediate `HTTP 422 Unprocessable Entity` without invoking solver threads.
2. **Planning Horizon Bounds:** $T \in [1, 120]$. Values $T = 0$ or $T > 120$ are strictly rejected.
3. **RSK-M2-07 Caller-Mandatory Deadline:** If any candidate has `is_tier1_mandatory=True`, `max_safety_start_period` must be provided and must satisfy $1 \le \text{max\_safety\_start\_period} \le T$.
4. **IEEE-754 Non-Finite Rejection:** Submissions containing `NaN`, `+Infinity`, or `-Infinity` are intercepted by Pydantic validators and rejected with HTTP 422.
5. **No Extra Fields:** Payload strictly enforces `extra="forbid"`. Unrecognized keys trigger HTTP 422.
6. **DAG Verification:** Directed dependencies must form an acyclic graph (DAG). Cyclic dependencies return HTTP 422 with a structured cycle detection error before solver dispatch.

---

## 3. Response Structure (`RecoveryOptimizationScenarioResponse`)

```json
{
  "scenario_name": "Post-Monsoon Infrastructure Recovery Plan 2026",
  "solver_status": "OPTIMAL",
  "is_optimal": true,
  "exact_objective_value": 48291048120042,
  "exact_best_bound": 48291048120042,
  "conservative_best_bound": 48291048120042,
  "objective_value": 48291048120042.0,
  "best_bound": 48291048120042.0,
  "optimality_gap": 0.0,
  "solve_time_seconds": 2.418,
  "selected_project_count": 18,
  "total_cost_ccu": 3840000000,
  "total_cost_inr": "38400000.00",
  "scheduled_projects": [
    {
      "project_id": "PRJ_WAY_001",
      "project_code": "WAY-ROAD-01",
      "district_id": "DIST_WAYANAD",
      "is_selected": true,
      "scheduled_start_period": 1,
      "scheduled_completion_period": 3,
      "cost_ccu": 1200000000,
      "cost_inr": "12000000.00",
      "assigned_funding_source_id": null
    }
  ],
  "periodic_solvency": [
    {
      "period": 1,
      "inflow_ccu": 7500000000,
      "expenditure_ccu": 1200000000,
      "net_balance_ccu": 6300000000,
      "carried_forward_ccu": 5985000000,
      "inflow_inr": "75000000.00",
      "expenditure_inr": "12000000.00",
      "net_balance_inr": "63000000.00",
      "carried_forward_inr": "59850000.00"
    }
  ],
  "district_equity_allocation_ccu": {
    "DIST_WAYANAD": 2400000000,
    "DIST_IDUKKI": 1440000000
  },
  "district_equity_allocation_inr": {
    "DIST_WAYANAD": "24000000.00",
    "DIST_IDUKKI": "14400000.00"
  },
  "input_fingerprint_sha256": "4b630f9a2e1d78c0e2941ba92847a9e102f893cb7f7b5502b1888cbd6caf14d4",
  "ortools_version": "9.8.3296",
  "solver_parameters": {
    "num_search_workers": 4,
    "random_seed": 42,
    "max_time_in_seconds": 60.0
  },
  "infeasibility_diagnostics": null
}
```

---

## 4. Infeasibility Diagnostics Structure

When `solver_status` is `"INFEASIBLE"`, the `scheduled_projects` array is empty, and `infeasibility_diagnostics` is populated with a 4-tier structured diagnosis:

```json
{
  "has_proven_infeasibility": true,
  "proven_causes": [
    {
      "category": "PRECEDENCE_DEADLINE_CONFLICT",
      "classification": "PROVEN_ROOT_CAUSE",
      "message": "Mandatory life-safety project PRJ_WAY_001 earliest feasible start (5) exceeds hard safety deadline 4.",
      "mathematical_condition": "EarliestStart(p) > max_safety_start_period",
      "affected_projects": ["PRJ_WAY_001"],
      "conflicting_periods": [4, 5],
      "details": {
        "earliest_feasible_start": 5,
        "max_safety_start_period": 4
      }
    }
  ],
  "necessary_condition_violations": [],
  "solver_hypotheses": [
    {
      "category": "PERIODIC_SOLVENCY_VIOLATION",
      "classification": "SOLVER_ASSISTED_HYPOTHESIS",
      "message": "Periodic cash-flow solvency constraint assumption conflicted. [Literal: solv_4]",
      "mathematical_condition": "SufficientAssumptionsForInfeasibility()",
      "affected_projects": [],
      "conflicting_periods": [4],
      "details": { "assumption_literal": "solv_4" }
    }
  ],
  "warnings": [],
  "is_assumption_core_minimal": false,
  "is_assumption_core_sufficient": true
}
```

---

## 5. HTTP Status Codes & Error Format

| Status Code | Reason | Cause |
| :--- | :--- | :--- |
| `200 OK` | Evaluation Successful | Solver completed. Returns `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `MODEL_INVALID`, or `UNKNOWN`. |
| `401 Unauthorized` | Missing / Invalid Token | Missing, invalid, or expired Bearer JWT token in Authorization header. |
| `403 Forbidden` | Access Denied | Authenticated user role is not `ADMIN` or `GOVT`. |
| `422 Unprocessable Entity` | Validation Failure | Constraint ceiling exceeded ($N > 500$, $T > 120$), cyclic dependency detected, or schema violation. |
| `500 Internal Server Error` | Unexpected Server Error | Unhandled backend exception. Sanitized error returned with correlation ID. |

#### Structured Validation Error Payload (HTTP 422)

```json
{
  "detail": {
    "error_code": "CANDIDATE_CEILING_EXCEEDED",
    "message": "Candidate projects count (501) exceeds maximum allowable ceiling of 500.",
    "correlation_id": "c1f7b889-105c-4861-b4bb-a9829f0e1329",
    "timestamp_iso": "2026-11-17T23:38:00.000Z"
  }
}
```
