# DIRS Phase 6D-A — Data Model Extensions & REST API Proposal

**Document ID:** `DIRS-PHASE6D-DOC-10`  
**Classification:** ARCHITECTURAL SPECIFICATION & API DESIGN  
**Author:** Principal Software Architect & Database Forensic Engineer  
**Date:** November 16, 2026  
**Status:** COMPLETE (PHASE 6D-A DESIGN BASELINE)  

---

## 1. Executive Summary

This document evaluates the relational data model requirements for Phase 6D recovery prioritization and project scheduling. It compares the existing frozen Phase 6B schema against the optimization requirements, proposes two implementation pathways (Zero-Migration vs Dedicated Extension Tables), and defines the complete REST API specification under `/api/v1/recovery/optimization/*`.

---

## 2. Comparison with Frozen Phase 6B Schema

The live `dirs_db` schema possesses four core recovery tables created in Phase 6B:
1. `recovery_projects`: Tracks capital reconstruction projects.
2. `project_dependencies`: Encodes directed finish-to-start precedence edges with lags.
3. `recovery_resources`: Tracks bills of materials and workforce requirements.
4. `recovery_override_logs`: Records immutable human governance overrides.

### 2.1 Gap Analysis Matrix

| Optimization Requirement | Phase 6B Existing Support | Identified Architectural Gap | Proposed Remediation Strategy |
| :--- | :--- | :--- | :--- |
| **Project Precedence DAG** | `project_dependencies` table with `lag_days`, `is_critical_path` | None | Fully supported natively in Phase 6B schema. |
| **Project Priority Score** | `recovery_projects.priority_score`, `priority_tier` | None | Fully supported natively; populated via MCPI. |
| **Project Duration & Timing** | `estimated_duration_days`, `earliest_start_date`, `planned_completion_date` | Continuous timestamps rather than discrete period integers | Map period index $t$ to dates: $\text{Date}(t) = \text{AnchorDate} + t \cdot \Delta t$. |
| **Cash-Flow Profile** | `recovery_projects.time_indexed_cost_profile` (`JSON`) | None | Fully supported natively as JSON list of periodic costs. |
| **Resource Demands** | `recovery_resources` table (`material_category`, `quantity_required`) | None | Fully supported natively in Phase 6B schema. |
| **Periodic Budget Envelopes** | No dedicated relational table for $B_t$ | Missing table for dynamic period envelopes | **Path A**: Pass in API request body.<br>**Path B**: Create `recovery_budget_envelopes` table. |
| **Optimization Run Audit** | `optimization_runs` (Phase 5 emergency table) | Emergency schema tied to incidents/shelters, not projects | **Path A**: Reuse with JSON metadata.<br>**Path B**: Create `recovery_optimization_runs`. |

---

## 3. Evaluation of Implementation Pathways

### Pathway A: Zero-Migration Architectural Design (Recommended Baseline)
- **Principle**: Operates 100% within the frozen Phase 6B database schema.
- **Mechanics**:
  1. Multi-period budget envelopes ($B_t$), funding source limits ($B_{f, t}$), and district equity floors ($\underline{\theta}_d$) are submitted dynamically in the optimization request payload (`RecoveryOptimizationRequest`).
  2. Scheduled start periods and finish periods are mapped to calendar dates and stored in `RecoveryProject.earliest_start_date` and `planned_completion_date`.
  3. Precedence critical path flags are updated in `ProjectDependency.is_critical_path`.
  4. Optimization run metadata, objective values, and explainability manifests are stored in `OptimizationRun` with `prediction_type = "RECOVERY_SCHEDULE"` and detailed JSON in `summary_metrics`.
- **Advantage**: **Zero database migrations required**. Eliminates risks of migration deadlocks or rollback failures.

### Pathway B: Dedicated Relational Schema Extensions
- **Principle**: Introduces new Alembic migration (`phase6d_recovery_optimization.py`) adding 3 tables:
  1. `recovery_optimization_runs`: Run ID, algorithm (`CP_SAT`), objective score, solve time, status.
  2. `recovery_project_schedules`: Links run ID to project ID, scheduled start period, scheduled finish period, allocated funding stream.
  3. `recovery_budget_envelopes`: Period index $t$, statutory envelope $B_t$, remaining unspent slack.
- **Advantage**: Pure relational normalization for enterprise SQL reporting.
- **Disadvantage**: Requires Alembic migration and alters frozen database state.

---

## 4. Proposed REST API Specification

All Phase 6D optimization endpoints are exposed under `/api/v1/recovery/optimization/*`:

### 4.1 Endpoints Overview

| Method | Endpoint | Description | Request Model | Response Model | Authorized Roles |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/recovery/optimization/mcpi/calculate` | Computes MCPI priority scores across candidate projects | `MCPICalculateRequest` | `MCPICalculateResponse` | `GOVT`, `ADMIN` |
| `POST` | `/api/v1/recovery/optimization/dag/validate` | Validates dependency DAG, detects cycles, extracts CPM | `DAGValidateRequest` | `DAGValidateResponse` | `GOVT`, `ADMIN` |
| `POST` | `/api/v1/recovery/optimization/schedule/solve` | Solves MP-RPSP optimization using OR-Tools CP-SAT | `RecoveryOptimizationRequest` | `RecoveryOptimizationResponse` | `GOVT`, `ADMIN` |
| `GET` | `/api/v1/recovery/optimization/runs/{run_id}` | Retrieves optimization run details and schedule manifest | None | `RecoveryOptimizationResponse` | `GOVT`, `NGO`, `ADMIN` |
| `POST` | `/api/v1/recovery/optimization/runs/{run_id}/approve` | Government approval gate sanctioning proposed portfolio | `ScheduleApproveRequest` | `RecoveryOptimizationResponse` | `GOVT` |

---

## 5. Pydantic Contract Schemas

### 5.1 Optimization Request (`RecoveryOptimizationRequest`)
```python
class RecoveryOptimizationRequest(BaseModel):
  planning_horizon_periods: int = Field(
      8, ge=1, le=52, description="Total discrete periods T"
  )
  period_duration_days: int = Field(
      30, ge=7, le=90, description="Length of discrete period"
  )
  budget_envelopes: List[float] = Field(
      ..., description="Periodic budget envelopes B_t"
  )
  funding_source_limits: Optional[Dict[str, List[float]]] = None
  district_equity_floors: Optional[Dict[str, float]] = None
  candidate_project_ids: Optional[List[str]] = None
  allow_budget_carry_forward: bool = True
  carry_forward_retention_rate: float = Field(1.0, ge=0.0, le=1.0)
  enable_lexicographic_safety_gate: bool = True
  scenario_profile: str = Field(
      "BASELINE", description="OPTIMISTIC, BASELINE, ADVERSE"
  )
  deterministic_seed: int = 42
```

### 5.2 Optimization Response (`RecoveryOptimizationResponse`)
```python
class ScheduledProjectItem(BaseModel):
  project_id: str
  project_code: str
  title: str
  sector: str
  mcpi_score: float
  is_selected: bool
  scheduled_start_period: Optional[int]
  scheduled_finish_period: Optional[int]
  is_on_critical_path: bool
  period_cash_flows: List[float]
  funding_stream_allocated: str
  binding_constraints: List[str]


class RecoveryOptimizationResponse(BaseModel):
  run_id: str
  solver_status: str  # OPTIMAL, FEASIBLE, INFEASIBLE
  objective_value: float
  solve_duration_ms: float
  planning_horizon_periods: int
  total_candidate_projects: int
  selected_projects_count: int
  total_capital_expended: float
  total_budget_envelope: float
  budget_utilization_pct: float
  scheduled_projects: List[ScheduledProjectItem]
  infeasibility_diagnostics: Optional[Dict[str, Any]] = None
  governance_approval_status: (
      str  # PROPOSED_PORTFOLIO, SANCTIONED_BY_GOVERNMENT
  )
  generated_at: datetime
```
