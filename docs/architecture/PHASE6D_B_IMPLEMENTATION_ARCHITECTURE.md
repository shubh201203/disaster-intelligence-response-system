# DIRS Phase 6D-B: Implementation Architecture Specification

**Subsystem:** Disaster Intelligence and Response System (DIRS)  
**Phase:** 6D-B — Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine  
**Milestone:** Milestone 6 — Final Architecture Treatise & Permanent Freeze  
**Status:** Certified & Frozen  
**Date:** November 2026  

---

## 1. Architectural Overview & System Decomposition

Phase 6D-B delivers an enterprise-grade, mathematically verified recovery project scheduling and resource allocation engine. It enables decision-makers to evaluate complex disaster recovery portfolios under multi-period financial constraints, renewable resource bounds, predecessor project dependencies, district equity quotas, and life-safety deadlines.

The subsystem is architected into five strictly decoupled, unidirectional architectural tiers:

```mermaid
flowchart TD
    subgraph UI ["Tier 1: Frontend User Interface (React / Vite / Tailwind)"]
        ROV[RecoveryOptimizationView]
        SPC[ScenarioParametersCard]
        CPG[CandidateProjectsGrid]
        SCB[SolverControlBar]
        PST[ProjectScheduleTimeline - Gantt]
        FSM[FinancialSolvencyMatrix]
        IDV[InfeasibilityDiagnosticsView]
    end

    subgraph APIClient ["Tier 2: API Client & Lossless Transport Layer"]
        AC[Axios Client with dirs_token Interceptor]
        LP[Lossless JSON Parser - BigInt / String Preservation]
    end

    subgraph APISchemas ["Tier 3: Backend API Routing & Pydantic v2 DTOs"]
        FastAPI[/api/v1/recovery/optimization/evaluate]
        DTOReq[RecoveryOptimizationScenarioRequest]
        DTOResp[RecoveryOptimizationScenarioResponse]
        VAL[Pydantic v2 Strict Validators & Safety Boundary Guards]
    end

    subgraph CoreEngine ["Tier 4: Optimization Orchestration & CP-SAT Engine"]
        ORCH[RecoveryOptimizationOrchestrator]
        CPSAT[CPSATRecoveryEngine - OR-Tools CP-SAT]
        DIAG[Infeasibility Diagnostic & Core Extraction Engine]
    end

    subgraph PureMath ["Tier 5: Pure Mathematical Calculation Services (Milestone 1)"]
        EQS[EquityCalculationService]
        SCS[SolvencyCalculationService]
        DPS[ProjectDependencyService - Topo & CPM]
        QSS[ProjectScoringService - MCPI Quantization]
        RCS[ResourceCapacityService]
    end

    UI --> APIClient
    APIClient --> APISchemas
    APISchemas --> CoreEngine
    CoreEngine --> PureMath
```

---

## 2. Layer-by-Layer Architectural Details

### 2.1 Tier 1: Frontend Decision Support Interface
- **Primary Page Component:** `RecoveryOptimizationView.tsx` located at `/admin/recovery-optimization`. Protected by `ProtectedRoute` allowing only `ADMIN` and `GOVT` roles.
- **Scenario Configuration:** `ScenarioParametersCard.tsx` manages planning horizon $T \in [1, 120]$, initial cash liquidity, discrete periodic budget inflows, and district equity quotas.
- **Candidate Projects Grid:** `CandidateProjectsGrid.tsx` renders paginated, sortable candidate recovery projects with inline editing, deletion, and modal addition with client-side validation.
- **Solver Dispatch & Confirmation:** `SolverControlBar.tsx` displays human-in-the-loop pre-dispatch confirmation modals, preventing accidental execution.
- **Indeterminate State Management:** `IndeterminateSolverOverlay.tsx` locks background controls and displays a monotonic millisecond stopwatch while solver computation runs.
- **Visualizations:**
  - `ProjectScheduleTimeline.tsx`: Pure CSS Grid 1-based Gantt chart rendering scheduled project spans, precedence edges, and life-safety deadline markers.
  - `FinancialSolvencyMatrix.tsx`: Dual-ledger cash-flow matrix showing parallel CCU and INR periodic inflows, project expenditures, and carry-forward balances.
  - `InfeasibilityDiagnosticsView.tsx`: 4-tier structured diagnosis accordion rendering proven causes, necessary condition violations, solver-assisted hypotheses, and minimal assumption cores.

### 2.2 Tier 2: Lossless Client Transport Layer
- **Axios Client (`apiClient.ts`):** Enforces a 130,000 ms client request timeout providing a buffer over the backend 120s CP-SAT search timeout cap, injects Bearer JWT authentication tokens, and normalizes errors into typed `OptimizationError` structures. (Note: The 120s server cap applies to the solver search phase; end-to-end response time for large models may include pre-search model generation overhead).
- **Lossless JSON Parser (`losslessParser.ts`):** Overrides default `JSON.parse` to intercept 64-bit integer objective values ($> 2^{53} - 1$) and decimal monetary figures, preserving them as lossless strings to prevent IEEE-754 double precision corruption.

### 2.3 Tier 3: API Routing & Validation Layer
- **API Endpoint:** `POST /api/v1/recovery/optimization/evaluate`
- **Pydantic v2 DTOs (`app.schemas.recovery_optimization`):** Enforces strict types, rejects unknown fields (`extra="forbid"`), rejects non-finite IEEE-754 floats (`NaN`, `+inf`, `-inf`), and verifies the RSK-M2-07 caller-mandatory safety deadline contract.
- **Zero Database Mutation Invariant:** Evaluation is stateless and purely analytical; 0 database writes, queries, or transactions are executed.

### 2.4 Tier 4: Optimization Engine & Orchestration
- **Orchestrator (`RecoveryOptimizationOrchestrator`):** Implements a 12-stage pipeline:
  1. Input parameter normalization and candidate project validation.
  2. Currency-to-Cent (CCU) fixed-point scaling ($1\text{ INR} = 100\text{ CCU}$).
  3. Precedence graph cycle detection and critical path method (CPM) bounds calculation.
  4. Solvency feasibility pre-checks.
  5. CP-SAT mathematical model construction and variable instantiation.
  6. Constraint generation (precedence, solvency, renewable resources, district equity, blackout ring-fencing, mandatory deadlines).
  7. Multi-threaded CP-SAT search invocation with deterministic random seed (`seed = 42`).
  8. Schedule extraction and post-solve reconciliation.
  9. Dual-ledger accounting calculation.
  10. Infeasibility core isolation and 4-tier diagnostic classification.
  11. SHA-256 scenario input fingerprinting.
  12. Response DTO serialization.
- **CP-SAT Engine (`CPSATRecoveryEngine`):** Solves exact integer linear programming problems using Google OR-Tools CP-SAT with boolean interval variables, cumulative resource constraints, and exact 64-bit integer objective maximization.

### 2.5 Tier 5: Pure Mathematical Services
- **`EquityCalculationService`:** Calculates district equity targets, unabsorbed policy escrows, and uncontacted blackout reserve ring-fencing.
- **`SolvencyCalculationService`:** Computes discrete cash-flow carry-forward balances under fiscal retention rate $\gamma \in [0.0, 1.0]$.
- **`ProjectDependencyService`:** Executes topological sorting, cycle detection via Tarjan/Kahn algorithms, and earliest/latest start period calculations.
- **`ProjectScoringService`:** Quantizes Multi-Criteria Prioritization Index (MCPI) scores into integer objective coefficients.
- **`ResourceCapacityService`:** Evaluates multi-resource periodic demand bounds.

---

## 3. Security, Access Control & Least Privilege Architecture

The Phase 6D-B architecture adheres to strict role-based access control (RBAC) and defense-in-depth:
1. **Frontend Route Guards (`ProtectedRoute.tsx`):**
   - Unauthenticated users are redirected to `/login`.
   - Non-administrative roles (`CITIZEN`, `VOLUNTEER`, `NGO`) attempting to visit `/admin/recovery-optimization`, `/admin`, or `/admin/simulation` are denied access and redirected to their role dashboards (`/dashboard`, `/volunteer`, `/ngo`).
   - Administrative roles (`ADMIN`, `GOVT`) are granted authorized access.
2. **Backend API Authorization:**
   - The endpoint `/recovery/optimization/evaluate` enforces JWT authentication via FastAPI security dependencies (`get_current_active_user`).
   - Non-admin JWT tokens return HTTP 403 Forbidden with sanitized error payloads.
3. **Auditability & Traceability:**
   - Every request is tagged with an `X-Correlation-ID` header.
   - Every response contains a SHA-256 cryptographic fingerprint computed over canonical scenario parameters.

---

## 4. Architectural Invariants

1. **Zero Database Migrations:** Alembic revision is frozen at `phase6b_recovery_foundation` across exactly 40 relational tables.
2. **Zero In-Memory Drift:** Pure math calculation services are stateless and deterministic.
3. **Lossless Precision:** Monetary quantities are calculated in integer CCU cents (1/100 INR) with 0 floating-point rounding errors.
4. **Reproducibility:** Given identical inputs and `seed = 42`, CP-SAT guarantees bit-for-bit identical schedules and objectives.
