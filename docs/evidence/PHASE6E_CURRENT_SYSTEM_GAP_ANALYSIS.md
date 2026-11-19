# DIRS Phase 6E: Current System Gap Analysis & Architectural Feasibility

**Document Reference:** `DIRS-PHASE6E-DOC-02`  
**Security Classification:** Strict Internal Engineering Specification  
**Baseline Parent:** Phase 6D-B Permanent Closure & Gate 2 Certified Baseline  
**Mode:** FORENSIC INSPECTION, GAP IDENTIFICATION & ARCHITECTURAL VERIFICATION  

---

## 1. Executive Summary

This document provides a forensic gap analysis across the DIRS backend, database, and frontend to evaluate the architectural feasibility of the proposed accelerated execution programme (combining remaining Phase 6E, 6F, and 6G responsibilities).

The analysis substantiates:
1. **Frontend Architecture:** The application is built entirely on React 18 with TypeScript, Tailwind CSS, Lucide icons, and Recharts. All proposed UI deliverables must strictly follow React `.tsx` conventions. Vue or other frameworks are prohibited.
2. **Backend Integration Points:** The pure mathematical CPM and cycle detection algorithms exist in `backend/app/recovery/services/project_dependency_service.py`. Standalone graph compilation routes and dry-run cycle validation endpoints are currently missing and must be added under `/api/v1/recovery/`.
3. **Database Schema Feasibility:** A granular inspection of the 40 database tables reveals that most proposed features are supported by the existing schema or with application-layer patterns, while specific capabilities (such as strict foreign-key NGO donor tracking) require explicit classification.

---

## 2. Frontend Architecture & Dependency Verification

Inspection of `frontend/package.json` confirms the active frontend stack:

```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.28.9",
    "axios": "^1.6.8",
    "clsx": "^2.1.0",
    "leaflet": "^1.9.4",
    "lucide-react": "^0.359.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-leaflet": "^4.2.1",
    "react-router-dom": "^6.22.3",
    "recharts": "^2.12.3",
    "tailwind-merge": "^2.2.2"
  }
}
```

### 2.1 Critical Frontend Architectural Rules
- **Framework:** React 18 (`.tsx` files). No Vue, Svelte, or additional frameworks.
- **Visual Graph Rendering:** No heavy graph libraries (`reactflow`, `cytoscape`, `d3`) are installed. The precedence DAG visualizer will be implemented as a clean, performant, native SVG/HTML5 Canvas React component: `frontend/src/components/recovery/PrecedenceGraphVisualizer.tsx`.
- **Styling & Icons:** Tailwind CSS with `tailwind-merge` and `lucide-react`.
- **Charts & Metrics:** `recharts` for community metric trends and simulation delta visualizations.
- **Client Offline Storage:** Native HTML5 `indexedDB` API (via custom React hook `useOfflineDrafts.ts`), requiring zero external dependencies.

---

## 3. Backend Integration Verification

### 3.1 Existing Mathematical Services (`backend/app/recovery/services/`)
Inspection of `backend/app/recovery/services/project_dependency_service.py` confirms that the core precedence algorithms are already implemented:
- `ProjectDependencyService.detect_cycle_and_toposort(nodes, edges)`: Kahn's algorithm returning topological sort or raising `CyclicDependencyError` with the ordered cycle path.
- `ProjectDependencyService.compute_cpm_pl(activities, edges, period_days)`: Forward pass (ES, EF), backward pass (LS, LF), total float, free float, makespan, and critical path identification.
- `ProjectDependencyService.calculate_transitive_cascades(nodes, edges)`: Transitive reachability counts.
- `ProjectDependencyService.analyze_dag(activities, edges, period_days)`: Comprehensive DAG analysis structure.

### 3.2 Existing API Router (`backend/app/routers/recovery.py`)
The router has prefix `/recovery` (mounted under `/api/v1` in `main.py`). Existing dependency routes:
- `POST /api/v1/recovery/dependencies`: Inserts a persistent dependency edge with in-memory Kahn cycle detection (rejects cycles with HTTP 400).
- `GET /api/v1/recovery/dependencies`: Returns a flat list of raw `ProjectDependency` database rows.

### 3.3 Genuine Backend Route Gaps
To support interactive precedence visualization and simulation, the following endpoints are genuinely missing and must be added:
1. **Precedence Graph Compilation Route (`GET /api/v1/recovery/dependencies/graph`):**
   - *Status:* Missing.
   - *Function:* Queries all active `RecoveryProject` and `ProjectDependency` rows, executes `ProjectDependencyService.analyze_dag()`, and returns a structured graph payload: nodes (with coordinates, duration, ES/EF/LS/LF, float, critical flag), directed edges (with lag), and critical path node IDs.
2. **Dry-Run Cycle Validation Route (`POST /api/v1/recovery/dependencies/validate-edge`):**
   - *Status:* Missing.
   - *Function:* Accepts candidate edge `(predecessor_id, successor_id, lag_days)`, runs cycle detection against the existing graph in memory without committing to the database, and returns `{is_valid: bool, cycle_path: List[str]}`.
3. **Community Metrics Aggregated Summary (`GET /api/v1/recovery/community-metrics/summary`):**
   - *Status:* Missing.
   - *Function:* Aggregates longitudinal ward indicators into sector health scores with exponential confidence decay ($C(t) = C_0 \cdot e^{-\lambda t}$).
4. **What-If Scenario Simulation (`POST /api/v1/recovery/simulation/what-if`):**
   - *Status:* Missing.
   - *Function:* Evaluates parameter perturbations (budget shifts, resource shocks) in memory and returns comparative projected completion timelines without mutating database state.

---

## 4. Database Feasibility Matrix

A critical examination of the existing 40 tables and SQLAlchemy models in `backend/app/models/recovery.py` yields the following feature classifications:

| Domain / Proposed Feature | Relevant Model(s) | Key Existing Columns | Feasibility Classification | Justification & Architectural Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Project Precedence DAG** | `ProjectDependency`, `RecoveryProject` | `predecessor_project_id`, `successor_project_id`, `lag_days`, `is_critical_path`, `duration_days` | **Supported by existing schema** | All topology, lag, and duration data already exist. CPM calculation is executed dynamically in the application layer. |
| **Community Recovery Metrics** | `CommunityRecoveryMetric` | `ward_code`, `metric_date`, `power_grid_restoration_pct`, `potable_water_access_pct`, `overall_recovery_score`, `data_confidence`, `freshness_status` | **Supported by existing schema** | All multi-sector indicator columns and data confidence fields exist. Temporal decay is computed dynamically on read. |
| **Recovery What-If Simulation** | In-memory execution over `RecoveryProject` & `RecoveryResource` | Budget, cost profile, duration, resources | **Supported by existing schema** | The simulation engine runs in memory; results are returned directly in the response payload without database mutations. |
| **Volunteer Field Assessments** | `RecoveryAssessment` | `assessment_code`, `inspector_id`, `damage_level`, `provenance_tier`, `evidence_media_urls`, `verification_status` | **Supported by existing schema** | Field surveys map to `RecoveryAssessment` with `provenance_tier="TIER_1_FIELD_INSPECTOR"`. Offline caching uses browser IndexedDB. |
| **Recovery Needs Tracking** | `RecoveryNeed`, `StructuredRecoveryNeed` | `ward_code`, `sector`, `affected_households`, `displaced_persons`, `unmet_need_score`, `census_baseline_population` | **Supported by existing schema** | Quantitative human need models are fully defined. Population reconciliation is already handled by `population_reconciliation.py`. |
| **NGO Resource Pledging** | `RecoveryResource` | `project_id`, `material_category`, `quantity_required`, `quantity_delivered`, `supplier_info`, `delivery_status` | **Supported with application-layer changes** | `RecoveryResource` does not have an explicit `pledged_by_user_id` foreign key. Pledges can be recorded by updating `supplier_info` (e.g. `"PLEDGE: NGO_ID"`) and `delivery_status="PLEDGED"`. If strict relational integrity to `users.id` is required, it will **Require schema changes**. |
| **Citizen Damage Crowdsourcing** | `RecoveryAssessment` | `inspector_id`, `incident_id`, `damage_level`, `provenance_tier`, `latitude`, `longitude` | **Supported with application-layer changes** | Citizens can submit initial reports mapped to `provenance_tier="TIER_0_CITIZEN_CROWDSOURCE"`. Active `incident_id` is supplied in context. |
| **Direct Citizen Subsidy Claims** | None (disbursement ledger) | N/A | **Requires further investigation** | If Phase 6E requires financial grant disbursements or bank account disbursements to citizens, a dedicated claims ledger would be required. In Phase 6E, scope is limited to damage reporting and ward status tracking. |

---

## 5. Summary of Architectural Verification

1. **Frontend:** React 18, TypeScript, Tailwind CSS, Lucide icons, Recharts, and HTML5 Canvas/SVG. Zero Vue files permitted.
2. **Backend:** Leverage existing `ProjectDependencyService` math logic; expose missing REST endpoints under `/api/v1/recovery/`.
3. **Database:** Core capabilities are 100% supported by the existing schema. NGO pledging and citizen reporting will use application-layer metadata patterns, avoiding risky schema migrations during this phase.
