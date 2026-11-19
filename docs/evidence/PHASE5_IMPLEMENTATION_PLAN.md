# DIRS Phase 5 — Optimization Layer Technical Implementation Roadmap (Sub-Phases 5B to 5M)

## Executive Summary

This document establishes the technical roadmap for implementing the Phase 5 Optimization Layer across sub-phases 5B through 5M. 

Implementation will proceed strictly sequentially following explicit authorization. Phase 3C and Phase 4 capabilities remain frozen and protected against regression throughout all sub-phases.

---

## 1. Sub-Phase Breakdown (5B to 5M)

```
┌───────────────────────────────────────────────────────────┐
│ PHASE 5A: Research, Data Modeling & Validation (CURRENT)  │
└─────────────────────────────┬─────────────────────────────┘
                              │ (Pending Authorization)
                              ▼
┌───────────────────────────────────────────────────────────┐
│ PHASE 5B: Database Schema Extensions (`Vehicle`, `OptRun`)│
├───────────────────────────────────────────────────────────┤
│ PHASE 5C: Graph & Distance Matrix Engine (NetworkX)       │
├───────────────────────────────────────────────────────────┤
│ PHASE 5D: Resource Allocation Solver (OR-Tools CP-SAT)    │
├───────────────────────────────────────────────────────────┤
│ PHASE 5E: Vehicle Routing Solver (OR-Tools Routing CVRPTW)│
├───────────────────────────────────────────────────────────┤
│ PHASE 5F: Volunteer & Shelter Assignment Engine           │
├───────────────────────────────────────────────────────────┤
│ PHASE 5G: Optimization Service Orchestration API          │
├───────────────────────────────────────────────────────────┤
│ PHASE 5H: Dynamic Event-Driven Re-Optimization System     │
├───────────────────────────────────────────────────────────┤
│ PHASE 5I: Government HITL Workflow & Audit Integration    │
├───────────────────────────────────────────────────────────┤
│ PHASE 5J: Frontend Command Center Optimization Dashboard  │
├───────────────────────────────────────────────────────────┤
│ PHASE 5K: Weight Sensitivity Study & Automated Tests      │
├───────────────────────────────────────────────────────────┤
│ PHASE 5L: Cyclone Vardah Demo Baseline & Empirical Results│
├───────────────────────────────────────────────────────────┤
│ PHASE 5M: Final Forensic Quality Gate & Code Freeze       │
└───────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Technical Scope by Sub-Phase

### Phase 5B — Database Schema & Data Model Extensions
- Create `backend/app/models/vehicle.py` (`Vehicle` model with weight/vol capacity, depot assignment, status).
- Create `backend/app/models/optimization.py` (`OptimizationRun`, `OptimizationRecommendation`, `OptimizationOverrideLog`).
- Run Alembic database migration scripts to apply schema changes to PostgreSQL/PostGIS.

### Phase 5C — Graph Engine & Travel Matrix Computation
- Create `backend/app/ai/optimization/graph.py`.
- Build NetworkX graph loader parsing PostGIS GeoJSON road edges.
- Implement dynamic edge penalty application based on active `RoadBlockage` records.
- Implement NxN travel time matrix generation via Dijkstra / SciPy all-pairs shortest paths.

### Phase 5D — Multi-Commodity Resource Allocation Engine
- Create `backend/app/ai/optimization/allocation.py`.
- Implement OR-Tools CP-SAT model for depot-to-incident commodity distribution.
- Support integer scaling ($\times 1000$), slack variable infeasibility handling, and priority weighting.

### Phase 5E — Capacitated Vehicle Routing Engine (CVRPTW-DB)
- Create `backend/app/ai/optimization/routing.py`.
- Implement Google OR-Tools `RoutingModel` for vehicle fleet path optimization.
- Configure capacity dimensions (weight & volume), time windows, and unvisited node drop penalties.

### Phase 5F — Volunteer Skill Matching & Shelter Assignment Engine
- Create `backend/app/ai/optimization/assignment.py`.
- Implement skill category matching algorithm matching registered volunteers to incidents based on skill tags (`MEDICAL`, `RESCUE`).
- Implement evacuee-to-shelter bed capacity allocation solver.

### Phase 5G — Optimization Service Orchestration API
- Create `backend/app/ai/optimization/service.py` (`OptimizationService`).
- Create `backend/app/api/v1/endpoints/optimization.py`.
- Expose REST API endpoints:
  - `POST /api/v1/optimization/run`: Triggers full optimization run.
  - `GET /api/v1/optimization/runs/{id}`: Fetches run details and recommendations.
  - `POST /api/v1/optimization/runs/{id}/approve`: Government HITL approval endpoint.
  - `POST /api/v1/optimization/runs/{id}/override`: Government HITL override endpoint.

### Phase 5H — Dynamic Re-Optimization & Event Trigger Engine
- Implement event listeners on `RoadBlockage` creation and `Incident` severity escalation.
- Automatically trigger async re-optimization job when new road blockages intersect active routes.

### Phase 5I — Government HITL Workflow & Audit Integration
- Connect approval/override endpoints to `backend/app/services/audit.py`.
- Ensure mandatory audit logging for all government user overrides with required justification text.

### Phase 5J — Frontend Command Center Optimization Dashboard
- Create React frontend components for optimization plan visualization.
- Implement Leaflet route trajectory rendering, blockage markers, and interactive override modal.

### Phase 5K — Weight Sensitivity Study & Automated Test Suite
- Create `backend/tests/test_optimization.py` covering all 8 validation test cases (`TEST-OPT-01` to `TEST-OPT-08`).
- Execute multi-configuration weight sensitivity study (Config 1 to Config 4) and document final production weight configuration.
- Verify target execution latency $<2,000\text{ms}$ (`TARGET`) for $N=50$ benchmark scale.

### Phase 5L — Cyclone Vardah Baseline Comparison & Empirical Verification
- Create `scripts/demo_phase5_optimization.py`.
- Execute automated end-to-end evaluation comparing Baseline A (Nearest Feasible Resource), Baseline B (FCFS Queue), and Phase 5 Optimizer against identical Cyclone Vardah inputs.
- Compute exact empirical metrics for Response Delay, SLA Compliance, Travel Distance, Unmet Demand, and Optimization Runtime, saving output to `docs/PHASE5_L_DEMO_RESULTS.md`.

### Phase 5M — Final Forensic Quality Gate & Code Freeze
- Run complete regression test suite (85/85 backend tests + Phase 3C tests + Phase 4 tests + Phase 5 tests).
- Freeze Phase 5 codebase and produce Capstone Final Quality Gate Report.
