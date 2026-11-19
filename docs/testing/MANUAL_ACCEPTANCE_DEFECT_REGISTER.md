# DIRS — Manual Acceptance Defect Register (11 Findings)

**Audit Date:** November 15, 2026  
**Auditor:** Senior Full-Stack, QA & GIS/AI Architecture Review  
**System Under Test:** Disaster Intelligence and Response System (DIRS) Phases 1–5G  
**Scope:** Manual Acceptance Testing Defect Audit  
**Status:** Forensic Audit Complete (Code Frozen — Awaiting Authorization)

---

## Executive Defect Summary Matrix

| ID | Title | Portal(s) | Category | Severity | Root Cause Status |
|:---|:---|:---|:---|:---|:---|
| **DEF-01** | Decision Review: Approve Dispatch Dialog Appears Behind GIS Map | Govt Command | Frontend (CSS / DOM) | **High** | **Confirmed** (Stacking context & missing React Portal) |
| **DEF-02** | AI Situation Query: Search Button Does Nothing / Apparent Inaction | Govt Command | Integration / Knowledge | **High** | **Confirmed** (No visual transition + Refusal parity + Missing KB coverage) |
| **DEF-03** | GIS Situation Map: Run KNN Spatial Query Produces No Visible Result | Govt Command | Integration (Schema) | **High** | **Confirmed** (Payload mismatch `point` vs `query_type` -> 422 error) |
| **DEF-04** | Scenario Laboratory: All Output Metrics Appear As Zero | Govt Command | Integration / Frontend | **Critical** | **Confirmed** (No-Op baseline fallback + `deltas` vs `delta` typo) |
| **DEF-05** | Comparative Stress: Run Multi-Scenario Comparison Does Not Work | Govt Command | Integration (Schema) | **High** | **Confirmed** (Payload mismatch `scenario_types` vs `scenario_ids` -> 422 error) |
| **DEF-06** | Citizen SOS: Distress Report Persistence, Routing & Audit Traceability | Citizen / Govt | Architectural Alignment | **Medium** | **Confirmed** (Calls generic `/incidents` instead of dedicated `/incidents/sos`) |
| **DEF-07** | Emergency Shelter Grid: View Shelter -> Get Directions Uses Mock Alert | Citizen | Frontend Incomplete | **Medium** | **Confirmed** (Invokes browser `alert()` placeholder; no navigation provider) |
| **DEF-08** | Citizen Grounded Safety Assistant: Returns Same Flood Response for All Disasters | Citizen | Frontend Mock / Backend KB | **Critical** | **Confirmed** (Frontend mock `setTimeout` + Missing disaster docs in KB) |
| **DEF-09** | Volunteer Turn-by-Turn Route: Mock Alert Instead of Navigation | Volunteer | Frontend Incomplete | **Medium** | **Confirmed** (Invokes browser `alert()` placeholder; no map/route provider) |
| **DEF-10** | Responder Fleet: Accept Task Lacks Persistence & Government Visibility | Volunteer / Govt | Frontend Mock / RBAC | **High** | **Confirmed** (Invokes browser `alert()`; zero API calls, no task persistence) |
| **DEF-11** | NGO Relief Logistics: Dispatch Stock Fails With "[object Object]" | NGO | Frontend (API Param & Serial.) | **High** | **Confirmed** (`?dispatch_quantity=` vs `?quantity=` -> 422 + array stringification) |

---

## Detailed Defect Records

### DEF-01: Decision Review: Approve Dispatch Dialog Appears Behind GIS Map
- **Portal:** Government Command Center (`/admin`)
- **Severity:** High
- **Category:** Frontend UI / CSS Stacking Context
- **Reproduction Steps:**
  1. Authenticate as Government Officer (`admin@dirs.gov`).
  2. In `/admin`, select an active incident from the Priority Incident Queue to load recommendations in `AICopilotPanel`.
  3. Under the "Decision Review" tab, click the "Approve Dispatch" button on an AI recommendation.
  4. Observe that the modal confirmation overlay and card render partially or completely behind the Leaflet GIS map controls, markers, or panes.
- **Expected Behavior:** Modal confirmation dialog must render on top of all application layers with `aria-modal="true"`, dimming the entire viewport including Leaflet map panes (`z-400` to `z-700`) and controls (`z-1000`).
- **Actual Behavior:** Dialog renders inline in `AICopilotPanel` inside a nested container with `z-50`. Leaflet's marker pane (`z-600`), popup pane (`z-700`), and zoom controls (`z-1000`) render above the modal.
- **Affected Files:**
  - `frontend/src/components/design-system/ConfirmDialog.tsx`
  - `frontend/src/components/AICopilotPanel.tsx`
  - `frontend/src/pages/admin/CommandCenter.tsx`
- **Backend API & Models:** None (display defect; triggers `POST /api/v1/ai/recommendations/{id}/approve` on confirm).
- **Proposed Minimal Correction:** Refactor `ConfirmDialog.tsx` to render through `createPortal(..., document.body)` with `z-[9999]`.
- **Regression Tests Required:** E2E / Cypress test checking modal overlay `z-index` and clickability above Leaflet container.

---

### DEF-02: AI Situation Query Search Button Apparent Inaction
- **Portal:** Government Command Center (`/admin`)
- **Severity:** High
- **Category:** Integration & Knowledge Base Coverage
- **Reproduction Steps:**
  1. Open Government Command Center (`/admin`), switch `AICopilotPanel` to "AI Situation Query".
  2. Enter "FIRE" into the query input and click "Search".
  3. The interface appears to do nothing; existing content remains static or an identical refusal banner is rendered.
- **Expected Behavior:** Submitting any query must show explicit visual loading, invoke `POST /api/v1/ai/rag/query`, and return differentiated, grounded guidance or an informative query-specific retrieval status.
- **Actual Behavior:** 
  1. `handleQuery` invokes `POST /api/v1/ai/rag/query` with `{ query: "FIRE", incident_id: null, mode: "GENERAL_COPILOT" }`.
  2. The knowledge base only contains documents for FLOOD, CYCLONE, and WHO triage.
  3. `HybridSearchRetriever` computes max similarity `0.1537` for "FIRE", failing the `top_similarity >= 0.35` threshold.
  4. `GroundingValidator` returns the identical refusal string: `"I don't have enough verified information in the DIRS database or authoritative emergency management knowledge base to answer this query."`.
  5. The UI does not clear the previous response or display a prominent loading indicator, so the newly returned refusal looks identical to pre-existing state.
- **Affected Files:**
  - `frontend/src/components/AICopilotPanel.tsx`
  - `backend/app/ai/rag/service.py`
  - `backend/app/ai/rag/grounding/validator.py`
- **Backend API & Models:** `POST /api/v1/ai/rag/query`; `KnowledgeDocument`, `KnowledgeChunk`, `RAGQueryLog`.
- **Proposed Minimal Correction:**
  - Frontend: Add loading skeleton, clear stale response on submit, handle errors via application notification.
  - Backend: Ingest curated knowledge summaries for Fire, Earthquake, Landslide, Tsunami, Chemical disasters.
- **Regression Tests Required:** Unit tests verifying RAG query execution for FIRE, EARTHQUAKE, and CYCLONE.

---

### DEF-03: GIS Situation Map: Run KNN Spatial Query Produces No Visible Result
- **Portal:** Government Command Center (`/admin/simulation`)
- **Severity:** High
- **Category:** Integration (Payload Schema Mismatch)
- **Reproduction Steps:**
  1. Navigate to `/admin/simulation` -> GIS Situation Map tab.
  2. Locate "Spatial Query Console" card.
  3. Select target layer "Nearby Shelters" and click "Run KNN Spatial Query".
  4. No results appear in the card list and no layer appears on the map.
- **Expected Behavior:** Backend executes spatial proximity search, returns GeoJSON feature collection, frontend displays top-k items in the list and renders them as highlighted markers on Leaflet map.
- **Actual Behavior:**
  - Frontend mutation sends `{ point: [80.2707, 13.0827], target_layer: "shelter", k_nearest: 3 }`.
  - Backend `POST /api/v1/gis/spatial-query` expects `SpatialQueryRequest` with required `query_type: str` (e.g. `NEAREST_SHELTER`), `latitude: float`, `longitude: float`.
  - FastAPI returns `422 Unprocessable Entity` (`missing: query_type`).
  - Frontend catches error silently; response property mapping (`spatialQueryResults.results` vs backend `features`) is also broken.
- **Affected Files:**
  - `frontend/src/pages/admin/DisasterSimulationView.tsx`
  - `backend/app/routers/gis.py`
  - `backend/app/schemas/simulation.py`
- **Backend API & Models:** `POST /api/v1/gis/spatial-query`.
- **Proposed Minimal Correction:** Map `spatialTarget` to valid `query_type` (`NEAREST_SHELTER`, `NEAREST_DEPOT`), provide `latitude`/`longitude`, read `features` from response, and plot markers on map.
- **Regression Tests Required:** Test suite verifying spatial query with valid payload returns 200 and features.

---

### DEF-04: Scenario Laboratory: All Output Metrics Appear As Zero
- **Portal:** Government Command Center (`/admin/simulation`)
- **Severity:** Critical
- **Category:** Integration / Frontend Field Name Typo
- **Reproduction Steps:**
  1. Navigate to `/admin/simulation` -> Scenario Laboratory tab.
  2. Select Archetype A: Flash Flood Influx.
  3. Click "Execute What-If Simulation".
  4. Observe all KPI cards display `0` (Unmet Evacuation: 0, Resource Shortfall: 0, Fleet Disruption: 0, Shelters Isolated: 0).
- **Expected Behavior:** Evaluates non-zero impact deltas comparing scenario state against base operational state.
- **Actual Behavior:**
  1. Frontend sends `{ scenario_type: "SCENARIO_A", custom_params: {...}, generate_response_plan: true }`.
  2. Backend expects `SimulationRunRequest(scenario_id, inline_scenario, base_workload, seed)`. Since neither is provided, backend executes fallback `SCEN_NOOP` (No-Op Baseline Scenario), which legitimately produces 0 deltas.
  3. Backend returns field `delta`, but frontend reads `simulationResult.deltas` (with 's'), defaulting to `'0'` even if non-zero deltas existed.
- **Affected Files:**
  - `frontend/src/pages/admin/DisasterSimulationView.tsx`
  - `backend/app/routers/simulation.py`
  - `backend/app/schemas/simulation.py`
- **Backend API & Models:** `POST /api/v1/simulation/run`; `SimulationScenario`, `SimulationRun`.
- **Proposed Minimal Correction:** Frontend must pass valid `scenario_id` (or `inline_scenario`) matching backend archetypes and read `simulationResult.delta` (singular).
- **Regression Tests Required:** Automated simulation test confirming Archetype A generates non-zero delta metrics.

---

### DEF-05: Comparative Stress: Run Multi-Scenario Comparison Does Not Work
- **Portal:** Government Command Center (`/admin/simulation`)
- **Severity:** High
- **Category:** Integration (Payload Schema Mismatch)
- **Reproduction Steps:**
  1. Navigate to `/admin/simulation` -> Multi-Scenario Comparative Stress tab.
  2. Click "Run Multi-Scenario Comparison".
  3. Button briefly spins and reverts; no table or comparison cards appear.
- **Expected Behavior:** Sends registered scenario IDs, receives `MultiScenarioCompareResponse`, and renders side-by-side metric comparison table.
- **Actual Behavior:**
  - Frontend sends `{ scenario_types: ['SCENARIO_A', 'SCENARIO_B', 'SCENARIO_C', 'SCENARIO_E'] }`.
  - Backend schema `MultiScenarioCompareRequest` strictly requires `scenario_ids: List[str]`.
  - Backend returns `422 Unprocessable Entity` (`missing: scenario_ids`).
- **Affected Files:**
  - `frontend/src/pages/admin/DisasterSimulationView.tsx`
  - `backend/app/routers/simulation.py`
  - `backend/app/schemas/simulation.py`
- **Backend API & Models:** `POST /api/v1/simulation/compare`; `SimulationScenario`.
- **Proposed Minimal Correction:** Query existing scenarios via `GET /simulation/scenarios` (or seed archetype scenario IDs) and pass `scenario_ids: string[]`.
- **Regression Tests Required:** Multi-scenario comparison endpoint test with valid `scenario_ids`.

---

### DEF-06: Citizen SOS: Distress Report Persistence, Routing & Audit Traceability
- **Portal:** Citizen Portal (`/citizen`) & Government Command Center (`/admin`)
- **Severity:** Medium
- **Category:** Workflow & API Endpoint Alignment
- **Reproduction Steps:**
  1. Login as Citizen (`citizen@dirs.org`).
  2. On Citizen Dashboard, click "TRIGGER SOS DISTRESS", confirm dialog.
  3. Button changes to "SOS RECORDED IN COMMAND QUEUE".
- **Expected Behavior:** Distress signal should be recorded with high precision GPS coordinates, assigned `CRITICAL` priority (score 99.0), broadcast to Command Center via WebSocket `SOS_TRIGGERED`, and logged in `audit_logs`.
- **Actual Behavior:**
  - Frontend invokes generic `POST /api/v1/incidents` with hardcoded Chennai center coordinates (`13.0827, 80.2707`).
  - Backend does persist to `incidents`, `incident_reports`, and `audit_logs`, but assigns normal algorithmic priority (score ~55-65), not 99.0.
  - Dedicated backend endpoint `POST /api/v1/incidents/sos` exists specifically for panic signals (sets score 99.0, broadcasts `SOS_TRIGGERED`), but is not utilized by the frontend.
- **Affected Files:**
  - `frontend/src/pages/citizen/CitizenDashboard.tsx`
  - `backend/app/routers/incidents.py`
  - `backend/app/services/incident_service.py`
- **Backend API & Models:** `POST /api/v1/incidents/sos`; `Incident`, `IncidentReport`, `AuditLog`.
- **Proposed Minimal Correction:** Update `CitizenDashboard.tsx` to call `POST /api/v1/incidents/sos` with live browser geolocation.
- **Regression Tests Required:** Test verifying SOS endpoint creates incident with score 99.0 and broadcasts event.

---

### DEF-07: Emergency Shelter Grid: View Shelter -> Get Directions Uses Mock Alert
- **Portal:** Citizen Portal (`/citizen/shelters`)
- **Severity:** Medium
- **Category:** Frontend Incomplete Implementation
- **Reproduction Steps:**
  1. Login as Citizen (`citizen@dirs.org`) and open Nearby Shelters.
  2. On any shelter card, click "Get Directions".
  3. A browser `alert("Navigation coordinates for [Shelter Name] sent to mobile directions.")` is displayed.
- **Expected Behavior:** Actionable directions: open navigation provider (Google Maps or OpenStreetMap directions in new tab) with shelter coordinates, or display application modal with coordinates and route information.
- **Actual Behavior:** Invokes browser `alert()`; no navigation service is opened and coordinates are not dispatched.
- **Affected Files:** `frontend/src/pages/citizen/ShelterFinder.tsx`.
- **Backend API & Models:** None (client navigation).
- **Proposed Minimal Correction:** Open `https://www.google.com/maps/dir/?api=1&destination=${s.latitude},${s.longitude}` in a new tab with `rel="noopener noreferrer"`.
- **Regression Tests Required:** Unit test checking Get Directions click handler opens navigation URL.

---

### DEF-08: Citizen Grounded Safety Assistant: Returns Same Flood Response for All Disasters
- **Portal:** Citizen Portal (`/citizen`)
- **Severity:** Critical
- **Category:** Frontend Mock / Backend Knowledge Coverage Gap
- **Reproduction Steps:**
  1. Login as Citizen, open Grounded Safety Assistant chat.
  2. Submit queries for different hazards: "earthquake precautions", "fire safety", "cyclone evacuation".
  3. Every query receives the same response: `"Seek higher ground immediately if water rises above 1 foot. Do not walk or drive through flood waters..."`
- **Expected Behavior:** Assistant must recognize disaster category, query the backend RAG pipeline, and provide differentiated, grounded guidance.
- **Actual Behavior:**
  - Frontend `CitizenDashboard.tsx` uses a local `setTimeout` mock with hardcoded keyword checks for 'shelter', 'hospital', 'water', falling back to flood text for all other inputs. Zero network requests are made.
  - Backend `KnowledgeDocument` table only contains 3 summaries (Flood, Cyclone, WHO Medical); no knowledge exists for Earthquake, Fire, Landslide, Tsunami, Chemical.
- **Affected Files:**
  - `frontend/src/pages/citizen/CitizenDashboard.tsx`
  - `backend/app/routers/rag.py`
  - `backend/app/ai/rag/service.py`
  - `backend/app/ai/rag/generation/llm_provider.py`
- **Backend API & Models:** `POST /api/v1/ai/rag/query`; `KnowledgeDocument`, `KnowledgeChunk`, `RAGQueryLog`.
- **Proposed Minimal Correction:**
  - Connect `CitizenDashboard.tsx` chat to `POST /api/v1/ai/rag/query`.
  - Ingest curated summaries for Earthquake, Fire, Landslide, Tsunami, Chemical accidents.
  - Ensure deterministic fallback differentiates disaster categories.
- **Regression Tests Required:** Backend tests submitting queries for all 7 disaster categories verifying differentiated responses.

---

### DEF-09: Volunteer Turn-by-Turn Route: Mock Alert Instead of Navigation
- **Portal:** Volunteer Hub (`/volunteer`)
- **Severity:** Medium
- **Category:** Frontend Incomplete Implementation
- **Reproduction Steps:**
  1. Login as Volunteer (`volunteer@dirs.org`).
  2. Under Active Mission Telemetry, click "Turn-By-Turn Route".
  3. A browser `alert("GPS coordinates sent to turn-by-turn navigation.")` pops up.
- **Expected Behavior:** Opens external navigation directions to assigned incident/shelter coordinates or displays waypoint routing modal.
- **Actual Behavior:** Raw browser `alert()` placeholder; no navigation service is launched.
- **Affected Files:** `frontend/src/pages/volunteer/VolunteerDashboard.tsx`.
- **Backend API & Models:** None (client navigation).
- **Proposed Minimal Correction:** Open navigation URL with task incident coordinates (`s.latitude`, `s.longitude`) or display route coordinates dialog.
- **Regression Tests Required:** Test checking navigation action handler.

---

### DEF-10: Responder Fleet: Accept Task Lacks Persistence & Government Visibility
- **Portal:** Volunteer Hub (`/volunteer`) & Government Command Center (`/admin`)
- **Severity:** High
- **Category:** Frontend Mock / Missing Self-Assignment Endpoint
- **Reproduction Steps:**
  1. Login as Volunteer (`volunteer@dirs.org`).
  2. Under Available Verified Incidents, click "Accept Task" on an incident.
  3. Browser alert: `"Assigned INC-2026-XXXX to your responder queue."`
  4. Incident remains unassigned in database, does not update active task pipeline, and Government Command has no record of the assignment.
- **Expected Behavior:** Claiming a task creates/updates a `RescueTask` with status `ACCEPTED`, assigns `volunteer_id`, transitions incident, updates volunteer telemetry, and broadcasts `TASK_ASSIGNED` to Command Center.
- **Actual Behavior:** Pure browser `alert()` with zero API calls.
- **Affected Files:**
  - `frontend/src/pages/volunteer/VolunteerDashboard.tsx`
  - `backend/app/routers/volunteers.py`
  - `backend/app/services/rescue_service.py`
- **Backend API & Models:** `RescueTask`, `Incident`, `User`, `AuditLog`.
- **Proposed Minimal Correction:** Wire "Accept Task" button to backend task claiming endpoint; allow volunteers to accept available verified tasks; update UI state and broadcast WebSocket event.
- **Regression Tests Required:** Test verifying volunteer task acceptance persists `RescueTask` and updates status.

---

### DEF-11: NGO Relief Logistics: Dispatch Stock Fails With "[object Object]"
- **Portal:** NGO Relief Supply & Dispatch Hub (`/ngo`)
- **Severity:** High
- **Category:** Integration (Parameter Name Mismatch & Error Serialization)
- **Reproduction Steps:**
  1. Login as NGO (`ngo@dirs.org`).
  2. On any inventory item, click "Dispatch".
  3. Enter dispatch quantity (e.g. 50) and click "Confirm Dispatch".
  4. Alert displays: `"Error dispatching stock: [object Object]"`.
- **Expected Behavior:** Stock is dispatched, `available_quantity` decrements in database, `RESOURCE_DISPATCHED` audit log and WebSocket event are created, and modal closes.
- **Actual Behavior:**
  - Frontend calls: `POST /api/v1/resources/{id}/dispatch?dispatch_quantity=50`.
  - Backend expects: `quantity: int = Query(...)`.
  - FastAPI returns `422 Unprocessable Entity` with `{"detail": [{"type":"missing","loc":["query","quantity"],"msg":"Field required"}]}`.
  - Frontend stringifies error array via string concatenation, rendering `"[object Object]"`.
- **Affected Files:**
  - `frontend/src/pages/ngo/NGODashboard.tsx`
  - `backend/app/routers/resources.py`
- **Backend API & Models:** `POST /api/v1/resources/{resource_id}/dispatch`; `Resource`, `AuditLog`.
- **Proposed Minimal Correction:** In `NGODashboard.tsx`, change `?dispatch_quantity=${dispatchQty}` to `?quantity=${dispatchQty}`. Improve error message extraction from FastAPI 422 arrays.
- **Regression Tests Required:** Test confirming dispatch endpoint succeeds with `?quantity=` and fails with informative error on invalid quantity.

---

## Shared Component Vulnerability Analysis

1. **`ConfirmDialog.tsx` (Shared Modal Component):**
   - Lacks `createPortal` and uses `z-50`, causing modal layering issues whenever a Leaflet GIS map or high z-index element is present.
   - Impacts: Government Command Center (`CommandCenter.tsx`), Citizen Portal SOS (`CitizenDashboard.tsx`), NGO Dashboard (`NGODashboard.tsx`).
2. **Error Message Serialization Pattern:**
   - In multiple components (`AICopilotPanel.tsx`, `NGODashboard.tsx`, `CitizenDashboard.tsx`), error catching does `(e.response?.data?.detail || e.message)`. When FastAPI returns 422, `detail` is an array of objects, resulting in `[object Object]`.
3. **Mock `window.alert()` Usages:**
   - Prevalent across `ShelterFinder.tsx`, `VolunteerDashboard.tsx`, `AICopilotPanel.tsx`, and `NGODashboard.tsx`, violating the application requirement for properly layered in-app dialogs and notifications.
