# DIRS Phase 6D-B — Milestone 0: Implementation File Map
## Permitted Modification Boundaries, Milestone Allocation, and Frozen Component Demarcation

**Document ID:** `DIRS-PHASE6D-B-M0-03`  
**Phase:** Phase 6D-B (Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine)  
**Milestone:** Milestone 0 (Forensic Preflight & Schema Compatibility)  
**Lead Authors:** Principal Software Architect, Senior Python/FastAPI Engineer, Forensic Software Auditor  
**Date of Audit:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Executive Summary & Boundary Mandate

In strict compliance with Section 2 of the Master Execution Prompt:
- **Primary Permitted Application Area:** `backend/app/recovery/`
- **Permitted Test Area:** `tests/backend/` (only dedicated Phase 6D-B tests or narrowly necessary recovery additions)
- **Modifications Prohibited:** Any modification to files outside these designated boundaries requires explicit, written project-owner approval.

This document establishes the exact, file-by-file roadmap for Phase 6D-B implementation across Milestones 1 through 6, identifying newly created service files, existing integration touchpoints, and strictly frozen components.

---

## 2. Milestone-by-Milestone Implementation File Map

### Milestone 1: Domain Contracts & Pure Mathematical Services
*Goal: Implement isolated, testable pure mathematical logic with zero database dependencies.*

| Action | Target File Path | Purpose & Responsibility |
| :---: | :--- | :--- |
| **CREATE** | `backend/app/recovery/services/mcpi_prioritization_service.py` | Pure mathematical calculation of Multi-Criteria Recovery Priority Index ($\Pi_j$). |
| **CREATE** | `backend/app/recovery/services/vulnerability_scoring_service.py` | Two-branch vulnerability mapping ($\phi_V$), demographic conservation, unsegregated lower bounds. |
| **CREATE** | `backend/app/recovery/services/life_safety_triage_service.py` | Continuous safety hazard index ($S_L = 0.70 \phi_{\text{dam}} + 0.20 H_{\text{sec}} + 0.10 \Omega_{\text{occ}}$), bounding, Tier 1 policy filter. |
| **CREATE** | `backend/app/recovery/services/project_dependency_service.py` | Kahn's topological sort, cycle detection, forward/backward pass Critical Path Method (CPM-PL). |
| **CREATE** | `backend/app/recovery/services/calendar_cost_service.py` | Project execution age $\tau$ vs. calendar period $t$ cash-flow expansion ($C_{j, t}$). |
| **CREATE** | `backend/app/recovery/services/equity_calculation_service.py` | District-level equity quotas ($\underline{\theta}_d$), dynamic absorption bounds, and escrow reserves. |
| **CREATE** | `backend/app/recovery/services/cash_flow_solvency_service.py` | Multi-period liquidity carry-forward ($\Phi_t = \eta \Phi_{t-1} + B_t - E_t \ge 0$). |
| **CREATE** | `tests/backend/test_phase6d_mathematical_services.py` | Comprehensive unit tests for all Milestone 1 pure mathematical services. |

---

### Milestone 2: Optimization Model & CP-SAT Engine
*Goal: Implement Google OR-Tools CP-SAT discrete optimization model.*

| Action | Target File Path | Purpose & Responsibility |
| :---: | :--- | :--- |
| **CREATE** | `backend/app/recovery/services/recovery_cpsat_solver.py` | Pure CP-SAT integer programming model builder: selection variables ($w_j$), start periods ($x_{j, t}$), optional intervals, precedence ($w_j \le w_i, S_j \ge S_i + d_i + L_{ij}$), budget carry-forward ($\Phi_t \ge 0$), and objective maximization. |
| **CREATE** | `backend/app/recovery/services/recovery_optimization_orchestrator.py` | Solver orchestration: integer scaling, timeout enforcement (60s), deterministic seeding (`seed=42`), status mapping (`OPTIMAL`, `FEASIBLE`, `INFEASIBLE`). |
| **CREATE** | `tests/backend/test_phase6d_cpsat_solver.py` | Dedicated tests for CP-SAT model builder, integer scaling, timeout guards, and deterministic replication. |

---

### Milestone 3: Infeasibility Advisor & Human Override Governance
*Goal: Diagnostic conflict detection and immutable audit logging for human overrides.*

| Action | Target File Path | Purpose & Responsibility |
| :--- | :--- | :--- |
| **CREATE** | `backend/app/recovery/services/recovery_infeasibility_advisor.py` | Diagnostic conflict isolation: precedence cycle localization, early budget liquidity deficits, equity floor conflicts; structured JSON explanations. |
| **CREATE** | `backend/app/recovery/services/recovery_override_service.py` | Human-in-the-loop override governance: recording ministerial actions to `RecoveryOverrideLog`, justification validation ($\ge 20$ chars). |
| **CREATE** | `tests/backend/test_phase6d_infeasibility_override.py` | Tests for infeasibility diagnostics and prohibited vs. permitted override pathways. |

---

### Milestone 4: Recovery Service & API Integration
*Goal: Expose optimization capabilities via FastAPI endpoints within existing recovery router.*

| Action | Target File Path | Purpose & Responsibility |
| :---: | :--- | :--- |
| **UPDATE** | `backend/app/schemas/recovery.py` | Add Pydantic contracts: `RecoveryOptimizationRequest`, `RecoveryOptimizationResponse`, `ScheduledProjectItem`, `InfeasibilityDiagnosticResponse`. |
| **UPDATE** | `backend/app/recovery/services/recovery_service.py` | Add orchestrating methods: `calculate_portfolio_mcpi()`, `solve_recovery_schedule()`, `explain_schedule_infeasibility()`, `record_schedule_override()`. |
| **UPDATE** | `backend/app/routers/recovery.py` | Expose recovery optimization endpoints under prefix `/recovery/optimization/*` with RBAC (`GOVT`, `ADMIN`). |
| **CREATE** | `tests/backend/test_phase6d_recovery_api.py` | End-to-end API integration tests, RBAC authorization gates, request validation. |

---

### Milestone 5: Regression, Adversarial Validation & Safety Audit
*Goal: Prove system correctness, regression safety, and zero schema disruption.*

| Action | Target File Path | Purpose & Responsibility |
| :---: | :--- | :--- |
| **CREATE** | `tests/backend/test_phase6d_adversarial_regression.py` | Adversarial edge cases: blackout districts, missing baselines, unsegregated demographics, cycle attempts, malformed costs. |
| **VERIFY** | `tests/backend/` | Full regression run (382 passing baseline tests verified). |
| **BUILD** | `frontend/` | Frontend production build verification (`npm run build`). |

---

### Milestone 6: Final Integration, Documentation & Release Candidate
*Goal: Release candidate packaging and forensic sign-off.*

| Action | Target File Path | Purpose & Responsibility |
| :---: | :--- | :--- |
| **CREATE** | `docs/PHASE6D_B_IMPLEMENTATION_ARCHITECTURE.md` | Final implementation architecture treatise. |
| **CREATE** | `docs/PHASE6D_B_API_REFERENCE.md` | Complete REST API endpoint documentation. |
| **CREATE** | `docs/PHASE6D_B_MATHEMATICAL_TRACEABILITY.md` | Code-to-formula mathematical traceability matrix. |
| **CREATE** | `docs/PHASE6D_B_POLICY_CONFIGURATION_GUIDE.md` | Administrator guide for policy thresholds and weights. |
| **CREATE** | `docs/PHASE6D_B_OPERATIONS_AND_LIMITATIONS.md` | Operational boundaries, disclaimers, and caveats. |
| **CREATE** | `docs/PHASE6D_B_FINAL_TEST_REPORT.md` | Comprehensive test execution report. |
| **CREATE** | `docs/PHASE6D_B_ZERO_MIGRATION_FINAL_SIGNOFF.md` | Formal certification of zero schema mutations. |
| **CREATE** | `docs/PHASE6D_B_FROZEN_PHASE_FINAL_SIGNOFF.md` | Formal certification that Phases 1–6C remain untouched. |
| **CREATE** | `docs/PHASE6D_B_FINAL_READINESS_GATE.md` | Release candidate readiness gate verdict. |

---

## 3. Strictly Frozen & Prohibited Components Inventory

The following directories, modules, models, and artifacts are **100% frozen** and must NOT be edited, deleted, or replaced:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        STRICTLY FROZEN CODEBASE REPOSITORIES                           │
└────────────────────────────────────────────────────────────────────────────────────────┘

  1. DATABASE MIGRATIONS (ABSOLUTELY FORBIDDEN):
     - `backend/alembic/` (All versions, env.py, script.py.mako)
     - `backend/alembic.ini`
     - Alembic revision head: `phase6b_recovery_foundation` (LOCKED)

  2. DATABASE MODELS (FROZEN):
     - `backend/app/models/` (All existing SQLAlchemy models)
     - Zero new tables, columns, constraints, or relationships.

  3. CORE SECURITY & AUTHENTICATION (FROZEN):
     - `backend/app/core/security.py`, `backend/app/core/deps.py`
     - RBAC roles (`GOVT`, `VOLUNTEER`, `CITIZEN`, `NGO`, `ADMIN`) unchanged.

  4. PHASE 1–5G PRODUCTION ENGINES (FROZEN):
     - Phase 3B CV runtime: `cv_damage_model.pkl`, feature extractors (UNTOUCHED)
     - Phase 3C Grounded RAG: Knowledge base, safety embeddings (UNTOUCHED)
     - Phase 5D Resource Allocation Optimization Engine (UNTOUCHED)
     - Phase 5E Vehicle Routing & Evacuation Dispatch Engine (UNTOUCHED)
     - Phase 5F Shelter & Volunteer Operations Engine (UNTOUCHED)
     - Phase 5G Incident Simulation & Scenario Laboratory (UNTOUCHED)

  5. PHASE 6C SERVICES (FROZEN):
     - `backend/app/recovery/services/damage_assessment_service.py` (UNTOUCHED)
     - `backend/app/recovery/services/population_reconciliation.py` (UNTOUCHED)
     - `backend/app/recovery/services/recovery_needs_service.py` (UNTOUCHED)
     - `backend/app/recovery/services/recovery_spatial_service.py` (UNTOUCHED)

  6. FRONTEND APPLICATION CODE (FROZEN DURING BACKEND MILESTONES):
     - `frontend/src/` (All components, pages, hooks, context)
```

---
*End of DIRS Phase 6D-B Milestone 0 Implementation File Map.*
