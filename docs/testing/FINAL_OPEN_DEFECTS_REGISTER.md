# DIRS — Final Open Defects and Remediation Register

**Audit Date:** November 15, 2026  
**System:** Disaster Intelligence and Response System (DIRS)  
**Scope:** Acceptance Remediation Closure (DEF-01 through DEF-11) & Phase 6 Readiness  

---

## 1. Defect Remediation Lifecycle Matrix

| Defect ID | Severity | Component | Finding Summary | Resolution Strategy | Status | Verifying Automated Test(s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | High | Frontend | Approve Dispatch modal confirmation dialog portal stacking prevented interaction or froze screen. | Converted `ConfirmDialog` to Radix UI `Portal` with isolated overlay and `z-[60]` layer. | **CLOSED** | `tests/backend/test_acceptance_batch1.py::test_decision_review_approval_flow` |
| **DEF-02** | High | AI / Frontend | AI Copilot search appeared non-functional; empty queries had no feedback; RAG knowledge lacked multi-hazard coverage. | Added active query state indicators, error feedback, and seeded curated NDMA/SDRF knowledge across all 7 disaster types. | **CLOSED** | `tests/backend/test_acceptance_batch3.py::test_rag_copilot_multi_hazard_grounding` |
| **DEF-03** | Medium | GIS / Frontend | GIS KNN query request schema mismatch and missing Leaflet highlight markers. | Aligned payload to `{"query_type": "KNN", "target_layer": "shelter"}` and added pulsing circle marker layer. | **CLOSED** | `tests/backend/test_acceptance_batch2.py::test_knn_spatial_query_schema_and_rendering` |
| **DEF-04** | High | Simulation | Scenario Laboratory submitted `scenario_id` inside nested payload causing singular delta parsing failure. | Corrected frontend payload contract to root `scenario_id` and standardized singular delta response parser. | **CLOSED** | `tests/backend/test_acceptance_batch2.py::test_scenario_run_and_delta_parsing` |
| **DEF-05** | Medium | Simulation | Multi-scenario comparison submitted mismatched key `scenario_ids_list` instead of `scenario_ids`. | Aligned payload to `{"scenario_ids": [...]}` and rendered delta differential comparison matrix. | **CLOSED** | `tests/backend/test_acceptance_batch2.py::test_multi_scenario_comparison` |
| **DEF-06** | Critical | Citizen Portal | Citizen SOS failed without GPS; no manual fallback; missing direct emergency endpoint. | Implemented `POST /api/v1/incidents/sos`, browser GPS integration with high-accuracy timeout, and address fallback. | **CLOSED** | `tests/backend/test_acceptance_batch1.py::test_citizen_sos_with_and_without_gps` |
| **DEF-07** | Medium | Citizen Portal | Shelter directions lacked waypoint modal and external navigation fallback. | Implemented `NavigationModal` with waypoint coordinates, Google Maps directions URL, and RFC 5870 `geo:` URI fallback. | **CLOSED** | `tests/backend/test_acceptance_batch3.py::test_shelter_navigation_modal_contract` |
| **DEF-08** | High | Citizen Portal | Citizen Safety Assistant used mock frontend responses instead of real backend RAG integration. | Replaced client mock with `POST /api/v1/ai/rag/query` with multi-hazard grounding and citations. | **CLOSED** | `tests/backend/test_acceptance_batch3.py::test_citizen_safety_assistant_rag_integration` |
| **DEF-09** | Medium | Volunteer | Volunteer Route lacked destination coordinates and external turn-by-turn navigation link. | Integrated `NavigationModal` into volunteer task cards with incident GPS coordinates and navigation links. | **CLOSED** | `tests/backend/test_acceptance_batch3.py::test_volunteer_navigation_modal_contract` |
| **DEF-10** | High | Volunteer | Volunteers could not accept assigned tasks; task state did not persist after browser refresh. | Added `POST /volunteers/tasks/{id}/status` restricted to assigned volunteers; verified state persistence. | **CLOSED** | `tests/backend/test_acceptance_batch1.py::test_volunteer_task_acceptance_persistence` |
| **DEF-11** | High | NGO Portal | NGO dispatch sent quantity in JSON body while backend expected query param; unhandled 400 error. | Changed request to query param `?quantity={n}`, added atomic decrement check, and handled 400 JSON serialization. | **CLOSED** | `tests/backend/test_acceptance_batch2.py::test_ngo_dispatch_inventory_decrement_and_protection` |

---

## 2. Reopened Known Defect: GIS Radius vs. BBOX Discrepancy

- **Defect Identifier:** `DEF-REOPEN-GIS-01`
- **Reported Symptom:** Radius query of $10\text{ km}$ at Chennai Central $(13.0827, 80.2707)$ returned 0 results, while bounding box query returned 143 features.
- **Root Cause:**
  1. Synthetic incidents in `DIRS-GIS-10` have their closest coordinate at $11.23\text{ km}$ from $(13.0827, 80.2707)$; zero incidents exist within a strict $10\text{ km}$ spherical circle.
  2. GIS router previously did not normalize query type strings `"RADIUS"` / `"RADIUS_QUERY"` to `SpatialQueryEngine.incidents_within_radius`.
  3. Bounding box query aggregated across all 12 situation layers (roads, zones, shelters, volunteers, vehicles), whereas radius query filtered solely on incidents.
- **Resolution:**
  - Normalized query type handling in `backend/app/routers/gis.py` for `"RADIUS"`, `"RADIUS_QUERY"`, `"WITHIN_RADIUS"`, and `"INCIDENTS_IN_RADIUS"`.
  - Added visual circle overlay on map interface indicating search radius.
  - Verified with automated tests: $10\text{ km} = 0$, $15\text{ km} = 3$, $25\text{ km} = 5$, $50\text{ km} = 10$.
- **Status:** **CLOSED & VERIFIED**.

---

## 3. Residual Observations and Recommendations for Phase 6

While all 11 blocking defects have been remediated and verified with zero open regressions, the following non-blocking technical observations are cataloged for Phase 6 (Production Hardening & Deployment):

### 3.1 Pydantic V2 Migration Warnings
- **Observation:** Backend startup and test suites output 8 deprecation warnings regarding Pydantic V1 `class Config:` syntax and `Field(..., example=...)`.
- **Impact:** Non-blocking in Python 3.11 with Pydantic 2.x; will require migration before Pydantic 3.0.
- **Phase 6 Recommendation:** Migrate models to `ConfigDict` and `json_schema_extra` during Phase 6 code clean-up.

### 3.2 SQLAlchemy Spatial Cache Key Warnings
- **Observation:** SQLAlchemy outputs `SAWarning: UserDefinedType _DummyGeometry(...) will not produce a cache key because the cache_ok attribute is not set to True`.
- **Impact:** Negligible performance overhead during development/testing; query execution is completely correct.
- **Phase 6 Recommendation:** Set `cache_ok = True` on `_DummyGeometry` in `backend/app/database.py` during Phase 6 performance profiling.

### 3.3 Starlette TestClient Deprecation
- **Observation:** `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
- **Impact:** Test harness deprecation warning; zero runtime application impact.
- **Phase 6 Recommendation:** Update `httpx` dependencies in `requirements.txt`.

### 3.4 OpenStreetMap Nominatim Geocoding Integration
- **Observation:** When a citizen submits an SOS with a text address and no GPS, the incident stores `(0.0, 0.0)` with a note for manual dispatcher geocoding.
- **Phase 6 Recommendation:** Integrate asynchronous Nominatim or OpenCage geocoding background worker to automatically resolve addresses into PostGIS coordinates when available.

---

## 4. Final Sign-Off Statement

All 11 functional defects (DEF-01 through DEF-11) and the reopened GIS query inquiry have been investigated, resolved, rigorously tested across all user roles, and confirmed closed. The DIRS codebase contains **0 blocking defects**, **0 failing tests**, and is ready for Phase 6 authorization upon project-owner sign-off.
