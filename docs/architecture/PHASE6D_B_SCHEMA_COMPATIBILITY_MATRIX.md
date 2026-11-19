# DIRS Phase 6D-B — Milestone 0: Schema Compatibility Matrix
## Zero-Migration Audit, Field-by-Field Relational Mapping, and Transient State Architecture

**Document ID:** `DIRS-PHASE6D-B-M0-02`  
**Phase:** Phase 6D-B (Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine)  
**Milestone:** Milestone 0 (Forensic Preflight & Schema Compatibility)  
**Lead Authors:** Principal Database Architect, Senior Systems Engineer, Database Integrity Auditor  
**Date of Audit:** November 16, 2026  
**Status:** COMPLETE & SEALED  
**Policy Directive:** ABSOLUTE ZERO MIGRATIONS — 100% EXISTING PHASE 6B SCHEMA ONLY  

---

## 1. Executive Summary

This document establishes the exhaustive schema compatibility matrix for Phase 6D-B. In strict adherence to Section 3 of the Master Execution Prompt:
- **No new migrations may be created.**
- **No existing migrations may be edited.**
- **No database tables, columns, constraints, or types may be added, renamed, or modified.**
- **Alembic head must remain strictly at `phase6b_recovery_foundation`.**

Every Phase 6D-B functional and mathematical requirement was cross-referenced against the actual live PostgreSQL database columns and SQLAlchemy models in `backend/app/models/recovery.py`. This audit proves that **100% of required persistent data attributes are natively supported by the existing Phase 6B schema**, and that all dynamic scenario parameters, solver telemetry, and intermediate schedules are safely handled through validated Pydantic API contracts and transient runtime computations.

---

## 2. Exhaustive Schema Compatibility Matrix

| Requirement ID | Optimization Requirement | Existing Entity / Database Column | Live SQL Data Type & Nullability | Proposed Phase 6D-B Implementation | Schema Change Needed? | Feasibility Status |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: |
| **REQ-01** | Multi-Criteria Priority Score ($\Pi_j \in [0, 100]$) | `recovery_projects.priority_score` | `DOUBLE PRECISION`, Nullable: `True` | Computed by MCPI service; persisted to existing column upon project ranking. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-02** | Priority Tier Classification (`TIER_1` to `TIER_4`) | `recovery_projects.priority_tier` | `VARCHAR(20)`, Nullable: `False`, Default: `"TIER_3"` | Assigned based on MCPI percentiles and Stage 1 Life-Safety Filter; stored in existing column. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-03** | Project Duration in Periods/Days ($d_j$) | `recovery_projects.estimated_duration_days` | `INTEGER`, Nullable: `False` | Native integer stores task duration; mapped to discrete planning periods in optimization model. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-04** | Execution Age Cost Profile Vector ($\boldsymbol{\gamma}_j$) | `recovery_projects.time_indexed_cost_profile` | `JSON`, Nullable: `True`, Default: `list` | Serialized as validated JSON array of periodic costs: `[gamma_1, gamma_2, ..., gamma_d]`. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-05** | Scheduled Start Period / Date ($S_j$) | `recovery_projects.earliest_start_date` | `TIMESTAMP`, Nullable: `True` | Start period $t$ mapped to calendar timestamp: $\text{Date}(t) = \text{AnchorDate} + (t-1) \Delta t$. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-06** | Scheduled Planned Completion Date ($C_j$) | `recovery_projects.planned_completion_date` | `TIMESTAMP`, Nullable: `True` | Completion period $t_{\text{finish}} = S_j + d_j - 1$ mapped to calendar timestamp. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-07** | Dependency Precedence Directed Edges ($(i, j)$) | `project_dependencies.predecessor_project_id`, `successor_project_id` | `VARCHAR(36)` Foreign Keys to `recovery_projects.id` | Natively represents directed acyclic precedence edges between recovery projects. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-08** | Precedence Completion-to-Start Lag ($L_{ij}$) | `project_dependencies.lag_days` | `INTEGER`, Nullable: `False`, Default: `0` | Encodes discrete non-negative lag periods $L_{ij} \ge 0$. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-09** | Critical Path Precedence Edge Flag | `project_dependencies.is_critical_path` | `BOOLEAN`, Nullable: `False`, Default: `False` | Updated by CPM service when dependency edge $(i, j)$ satisfies zero total float ($TF = 0$). | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-10** | Project-Level Critical Path Membership | Dynamic Runtime Property in Pydantic Response Schema | `BOOLEAN` in API response (`ScheduledProjectItem.is_on_critical_path`) | Computed dynamically in memory from CPM analysis ($TF_j = LS_j - ES_j = 0$); transiently exposed. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-11** | Dynamic Planning Horizon ($T$) | Request Payload: `RecoveryOptimizationRequest.planning_horizon_periods` | Pydantic integer (`ge=1, le=52`) | Passed dynamically in API request; not a static database column. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-12** | Multi-Period Budget Envelopes ($B_t$) | Request Payload: `RecoveryOptimizationRequest.budget_envelopes` | Pydantic `List[float]` | Passed dynamically per optimization run; allows multi-scenario evaluation without DB lock-in. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-13** | District Policy Equity Targets ($\underline{\theta}_d$) | Request Payload: `RecoveryOptimizationRequest.district_equity_floors` | Pydantic `Dict[str, float]` | Configurable administrative targets passed in request body; validated to sum $\le 1.0$. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-14** | Carry-Forward Retention Factor ($\eta$) | Request Payload: `RecoveryOptimizationRequest.carry_forward_retention_rate` | Pydantic float (`ge=0.0, le=1.0`) | Configured dynamically per run (default: `1.00`). | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-15** | Life-Safety Policy Threshold ($\tau_L$) | Request Payload: `RecoveryOptimizationRequest.safety_hazard_threshold` | Pydantic float (`default=0.85`) | Configured dynamically; allows policy sensitivity testing without database mutation. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-16** | Vulnerability Policy Multipliers ($\mathbf{v}$) | Request Payload: `RecoveryOptimizationRequest.vulnerability_multipliers` | Pydantic dict (default: `[1.0, 2.5, 3.0, 4.5]`) | Configured dynamically; enables policy equity sweeps. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-17** | Cash-Flow Closing Balances ($\Phi_t$) | Response Payload: `RecoveryOptimizationResponse.closing_cash_balances` | Pydantic `List[float]` | Computed transiently by CP-SAT solver and returned in API response. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-18** | Solver Run Telemetry & Status | Response Payload: `RecoveryOptimizationResponse` | Pydantic schema (`status`, `objective_value`, `solve_time_ms`) | Returned directly in API response; stored transiently or logged to audit trail. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-19** | Human Administrative Overrides | `recovery_override_logs` | `VARCHAR(36)`, `VARCHAR(50)`, `JSON`, `TEXT`, `TIMESTAMP` | Natively captures user ID, action (`SCHEDULE_OVERRIDE`, `BUDGET_OVERRIDE`), original & new values, and justification. | **NO** | **VERIFIED COMPATIBLE** |
| **REQ-20** | Material & Workforce Resource Demands | `recovery_resources` | `VARCHAR(50)`, `DOUBLE PRECISION`, `VARCHAR(30)` | Natively tracks bills of materials and quantities required per project. | **NO** | **VERIFIED COMPATIBLE** |

---

## 3. Deep-Dive on Specific Field Audits

### 3.1 Time-Indexed Cost Profile (`recovery_projects.time_indexed_cost_profile`)
- **SQL Type:** `JSON`, Nullable: `True`.
- **Validation:** Pydantic model `TimeIndexedCostProfileSchema` enforces:
  - Total array length matches `estimated_duration_days` ($|\boldsymbol{\gamma}_j| = d_j$).
  - Every element is non-negative: $\gamma_{j, \tau} \ge 0$.
  - Array sum reconciles exactly with `estimated_cost`: $\sum_{\tau=1}^{d_j} \gamma_{j, \tau} = c_j$.
- **Conclusion:** JSON provides native, completely safe, and flexible persistence without introducing a 1-to-many child table.

### 3.2 Critical Path Representation
- **Edge-Level Critical Path:** `project_dependencies.is_critical_path` (`BOOLEAN`, default `False`) persistently marks whether directed link $(i, j)$ has zero float.
- **Project-Level Critical Path:** Storing a static boolean on `recovery_projects` would be a database anti-pattern because project float is a dynamic function of global horizon $T$ and predecessor durations.
- **Conclusion:** Exposing `is_on_critical_path` dynamically in `ScheduledProjectItem` without adding a column to `recovery_projects` is 100% compliant with zero migrations and mathematically sound.

### 3.3 Dynamic Optimization Parameters ($B_t, T, \underline{\theta}_d, \tau_L$)
- **Audit Decision:** These parameters are dynamic scenario inputs, not static project properties. Persisting them into relational tables would require creating new tables (`recovery_optimization_runs`, `recovery_budget_envelopes`), which is strictly prohibited under zero migrations.
- **Conclusion:** Passing dynamic parameters via `RecoveryOptimizationRequest` and returning solved schedules in `RecoveryOptimizationResponse` complies 100% with zero migrations.

---

## 4. Final Zero-Migration Certification

```
================================================================================
           DIRS PHASE 6D-B SCHEMA COMPATIBILITY CERTIFICATION                  
================================================================================

  - Total Database Requirements Audited:                20 / 20
  - Existing Database Entities Reused:                  recovery_projects
                                                        project_dependencies
                                                        recovery_resources
                                                        recovery_override_logs
                                                        recovery_needs
                                                        recovery_assessments
  - New Database Migrations Required:                   0 (ZERO)
  - New Database Tables Required:                       0 (ZERO)
  - New Database Columns Required:                      0 (ZERO)
  - Modified Database Constraints:                      0 (ZERO)
  - Alembic Head Revision:                              phase6b_recovery_foundation (UNALTERED)

  CERTIFICATION VERDICT: 100% ZERO-MIGRATION COMPATIBLE
================================================================================
```

---
*End of DIRS Phase 6D-B Milestone 0 Schema Compatibility Matrix.*
