# DIRS — Manual Acceptance Testing: In-Depth Root Cause Audit
**Document ID:** `DIRS-AUDIT-RCA-2026-11-15`  
**Status:** Completed Analysis  
**Auditor:** Senior Full-Stack, QA, GIS, AI & Security Reviewer  

---

## 1. Executive Summary & Scope

This Root Cause Audit investigates all 11 defects flagged during manual acceptance testing of the Disaster Intelligence and Response System (DIRS). Each defect has been analyzed through code inspection, schema audits, runtime queries, and API payload tracing across the full stack.

### Classification Matrix
| Finding ID | Classification | Severity | Confirmed Root Cause |
| :--- | :--- | :--- | :--- |
| **DEF-01** | Frontend Architecture / CSS Stacking Context | Critical | Modal rendered inline without DOM portal; Leaflet map pane z-indices (`z-400`–`z-1000`) occlude dialog `z-50`. |
| **DEF-02** | Frontend / RAG Retrieval / Data Gap | High | Missing domain documents (Fire/Earthquake); low similarity score (0.15) trips GroundingValidator refusal; UI lacks loading feedback and fails to clear prior refusal text. |
| **DEF-03** | Frontend / Backend API Contract Mismatch | High | Frontend sends `{point: [...], target_layer, k_nearest}`; backend expects `SpatialQueryRequest(query_type, latitude, longitude)`; returns HTTP 422; frontend fails silently. |
| **DEF-04** | Contract Mismatch & Property Name Bug | High | Frontend posts `{scenario_type}` triggering `SCEN_NOOP` (0 metrics); frontend parses `simulationResult.deltas` instead of backend `delta`. |
| **DEF-05** | Frontend / Backend API Contract Mismatch | Medium | Frontend submits `{scenario_types: [...]}`; backend requires `{scenario_ids: [...]}`; FastAPI returns 422 Unprocessable Entity silently. |
| **DEF-06** | Integration / Architectural Incompleteness | High | Citizen UI calls generic `POST /incidents` with hardcoded coordinates instead of dedicated `POST /incidents/sos` with HTML5 Geolocation and CRITICAL priority escalation. |
| **DEF-07** | Incomplete Frontend Implementation | Medium | Action invokes raw browser `alert()`; no routing modal or standard navigation intent URI scheme (`geo:`, Google Maps, OSM). |
| **DEF-08** | Incomplete Implementation / Mock Data | Medium | Frontend uses hardcoded local `setTimeout` chatbot with keyword heuristics falling back to flood advice; does not call `/api/v1/ai/rag/query`. |
| **DEF-09** | Incomplete Frontend Implementation | Medium | Action invokes raw browser `alert()`; no turn-by-turn route presentation or directions integration. |
| **DEF-10** | Incomplete Architecture / State Machine Gap | High | "Accept Task" triggers browser `alert()`; does not invoke `/dispatch/assignments` or `/incidents/{id}/transition`; no assignment recorded in DB. |
| **DEF-11** | API Query Parameter Mismatch & Error Parsing | Medium | Frontend passes `dispatch_quantity` query param; backend route expects `quantity`; returns 422; frontend stringifies error array to `"[object Object]"`. |

---

## 2. Detailed Root Cause Analysis by Defect

### DEF-01: Approve Dispatch Dialog Appears Behind GIS Map
- **Affected File:** `frontend/src/components/common/ConfirmDialog.tsx` (lines 35–45)
- **Parent View:** `frontend/src/pages/DecisionReview.tsx`
- **Technical Mechanism:**
  - `ConfirmDialog` renders as a regular React component inside the parent hierarchy of `DecisionReview.tsx`:
    ```tsx
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity" />
    ```
  - `DecisionReview.tsx` embeds Leaflet GIS maps. Leaflet creates DOM stacking contexts where:
    - Tile pane: `z-index: 200`
    - Overlay pane: `z-index: 400`
    - Shadow pane: `z-index: 500`
    - Marker pane: `z-index: 600`
    - Tooltip pane: `z-index: 650`
    - Popup pane: `z-index: 700`
    - Map controls (zoom, attribution): `z-index: 1000`
  - When `ConfirmDialog` is rendered inside a parent container with relative positioning, transforms, or lower z-index, it creates a local stacking context bounded below the map controls or leaflet layers.
  - Furthermore, `ConfirmDialog` uses `z-50`, which is strictly lower than Leaflet's marker and popup layers (`z-600`–`z-700`) and map controls (`z-1000`).
- **Required Remediation:**
  1. Render `ConfirmDialog` via `ReactDOM.createPortal(..., document.body)` so it escapes any local component stacking context.
  2. Increase the backdrop and modal container z-index to `z-[9999]` or `z-[10000]` to guarantee presentation above Leaflet map controls (`z-1000`).

---

### DEF-02: AI Situation Query Search Button Appears Inactive / Returns Refusal
- **Affected Files:**
  - Frontend: `frontend/src/components/ai/AICopilotPanel.tsx` (lines 62–95)
  - Backend Service: `backend/app/services/rag_service.py` (lines 88–145)
  - Knowledge Base: `backend/app/models/knowledge.py` / PostgreSQL database
- **Technical Mechanism:**
  1. **Data Ingestion Gap:** Database inspection of `KnowledgeDocument` reveals only 3 documents:
     - `DOC-FLOD-2024-001` (NDMA National Disaster Management Guidelines: Management of Floods)
     - `DOC-CYC-2024-002` (NDMA Guidelines: Management of Cyclones)
     - `DOC-WHO-2024-003` (WHO Emergency Medical Teams: Field Triage and Mass Casualty Protocol)
     - *Zero* documents exist for Fire, Earthquake, Landslide, or Hazardous Chemical events.
  2. **Retrieval & Grounding Failure:** When searching "FIRE", hybrid search returns chunks with an aggregated similarity score of `0.1537`. In `backend/app/services/rag_service.py`:
     ```python
     if similarity_score < 0.35:  # GroundingValidator confidence threshold
         return RAGQueryResponse(
             answer="I don't have enough verified information in the official guidelines to answer this query safely.",
             is_grounded=False,
             sources=[]
         )
     ```
  3. **Frontend UX Illusion of Inaction:**
     - In `AICopilotPanel.tsx`, `handleQuery` submits the request.
     - When the query completes, `response` is populated with the exact same canned refusal text.
     - The component does not display a distinct loading spinner over the output container while awaiting the API response, nor does it clear or flash the response box.
     - If the user types "FIRE", receives the refusal, types "EARTHQUAKE", and clicks search again, the identical refusal remains static on screen without visual state transition, appearing as if the button did nothing.
- **Required Remediation:**
  1. Add immediate loading state and disable the search button while `isLoading` is active; clear previous output upon new submission.
  2. If `is_grounded == false`, display a distinct warning banner indicating that no verified documents exist for the queried hazard type, rather than rendering it as standard text.
  3. Curate and ingest standard guidelines for Earthquake, Urban Fire, and Industrial Hazards into the knowledge repository.

---

### DEF-03: GIS KNN Spatial Query Produces No Visible Results
- **Affected Files:**
  - Frontend: `frontend/src/pages/GISCommandCenter.tsx` (lines 142–175)
  - Backend Route: `backend/app/api/v1/endpoints/gis.py` (lines 80–115)
  - Backend Schema: `backend/app/schemas/gis.py`
- **Technical Mechanism:**
  1. **Contract Mismatch:** Frontend sends:
     ```json
     {
       "point": [80.2707, 13.0827],
       "target_layer": "shelters",
       "k_nearest": 3
     }
     ```
  2. Backend endpoint `POST /api/v1/gis/spatial-query` defines:
     ```python
     class SpatialQueryRequest(BaseModel):
         query_type: str  # "knn", "radius", "bbox"
         latitude: float
         longitude: float
         radius_meters: Optional[float] = None
         k_nearest: Optional[int] = 5
         target_layer: str
     ```
  3. Because `query_type`, `latitude`, and `longitude` are missing from the top-level payload, FastAPI validation rejects the request with `HTTP 422 Unprocessable Entity`:
     ```json
     {"detail": [{"loc": ["body", "query_type"], "msg": "field required", "type": "value_error.missing"}]}
     ```
  4. The frontend lacks an error toast or feedback mechanism, failing silently.
  5. Furthermore, upon a successful response, backend returns GeoJSON `{ "type": "FeatureCollection", "features": [...] }`, while frontend checks for `response.data.results`.
- **Required Remediation:**
  1. Align frontend request payload to match `SpatialQueryRequest`:
     ```ts
     {
       query_type: "knn",
       latitude: coords.lat,
       longitude: coords.lng,
       k_nearest: kValue,
       target_layer: spatialTarget
     }
     ```
  2. Parse the returned `features` GeoJSON collection and add a dedicated Leaflet vector layer with distinct highlight styling for nearest neighbor entities.

---

### DEF-04: Scenario Laboratory Reports All Zero Metrics
- **Affected Files:**
  - Frontend: `frontend/src/pages/ScenarioLaboratory.tsx` (lines 85–130)
  - Backend Route: `backend/app/api/v1/endpoints/simulation.py` (lines 40–80)
  - Backend Service: `backend/app/services/simulation_service.py`
- **Technical Mechanism:**
  1. **Invocation of SCEN_NOOP Baseline:**
     - Backend `POST /api/v1/simulation/run` accepts `SimulationRunRequest`:
       ```python
       class SimulationRunRequest(BaseModel):
           scenario_id: Optional[str] = None
           inline_scenario: Optional[ScenarioCreate] = None
       ```
     - Frontend sends:
       ```json
       {
         "scenario_type": "SCENARIO_A",
         "custom_params": {},
         "generate_response_plan": true
       }
       ```
     - Because neither `scenario_id` nor `inline_scenario` is provided, the backend falls into its fallback branch:
       ```python
       scenario = self._get_scenario_by_id(db, "SCEN_NOOP")
       ```
     - `SCEN_NOOP` is the No-Op Baseline scenario where no disruption occurs; consequently, all simulated impact deltas are mathematically zero.
  2. **Property Name Typo in Frontend:**
     - Backend response model `SimulationRunResponse` returns:
       ```python
       delta: Dict[str, float]  # singular
       ```
     - Frontend reads:
       ```ts
       simulationResult.deltas?.unmet_evacuees_delta || 0  // plural "deltas"
       ```
     - Even if a scenario were run, `simulationResult.deltas` evaluates to `undefined`, defaulting every metric card to `0`.
- **Required Remediation:**
  1. Fetch pre-seeded scenario IDs from `GET /api/v1/simulation/scenarios` (e.g. `SCEN-FLOOD-001`, `SCEN-CYC-001`) and pass `scenario_id: selectedScenarioId` in the request body.
  2. Update frontend property access to `simulationResult.delta` (singular).

---

### DEF-05: Multi-Scenario Comparison Does Not Execute
- **Affected Files:**
  - Frontend: `frontend/src/pages/ScenarioLaboratory.tsx` (lines 140–175)
  - Backend Route: `backend/app/api/v1/endpoints/simulation.py` (lines 95–130)
- **Technical Mechanism:**
  - Frontend sends:
    ```json
    { "scenario_types": ["SCENARIO_A", "SCENARIO_B"] }
    ```
  - Backend schema `MultiScenarioCompareRequest` strictly requires:
    ```python
    class MultiScenarioCompareRequest(BaseModel):
        scenario_ids: List[str]
        comparison_metrics: Optional[List[str]] = None
    ```
  - FastAPI rejects with HTTP 422: `field required: scenario_ids`.
  - Frontend mutation lacks an `onError` handler; the UI remains in an idle state without updating comparison charts.
- **Required Remediation:**
  1. Update frontend request payload to pass valid database `scenario_ids`.
  2. Add error boundary and toast notification on failure.

---

### DEF-06: Citizen SOS Distress Report Flow Traceability
- **Affected Files:**
  - Frontend: `frontend/src/components/citizen/EmergencySOSButton.tsx` (lines 40–80)
  - Backend Endpoints: `backend/app/api/v1/endpoints/incidents.py` (`POST /` vs `POST /sos`)
  - Database Models: `Incident`, `IncidentReport`, `AuditLog`
- **Technical Mechanism:**
  1. Frontend currently executes:
     ```ts
     api.post('/api/v1/incidents', {
       title: "CITIZEN SOS DISTRESS",
       incident_type: "SOS",
       severity: "CRITICAL",
       latitude: 13.0827,
       longitude: 80.2707
     })
     ```
  2. Backend possesses a specialized high-priority endpoint: `POST /api/v1/incidents/sos`.
  3. While generic `POST /incidents` successfully creates an incident record, `POST /incidents/sos`:
     - Sets priority score to `99.0` (critical emergency triage)
     - Broadcasts an immediate WebSocket notification event `SOS_TRIGGERED` across the Commander dispatch grid
     - Tags the incident with `source="CITIZEN_SOS"`
     - Enforces audit logging specifically for citizen distress triggers
  4. Furthermore, frontend hardcodes Chennai coordinates (`13.0827, 80.2707`) instead of querying the browser's `navigator.geolocation.getCurrentPosition()`.
- **Required Remediation:**
  1. Re-route frontend call to `POST /api/v1/incidents/sos`.
  2. Integrate `navigator.geolocation` with fallback handling and user consent.
  3. Ensure response returns the created SOS incident ID and displays immediate confirmation with dispatch status tracking.

---

### DEF-07: Shelter View "Get Directions" Uses Alert Placeholder
- **Affected Files:**
  - Frontend: `frontend/src/components/citizen/ShelterFinder.tsx` (line 162)
- **Technical Mechanism:**
  - Button event handler:
    ```tsx
    onClick={() => alert(`Navigation coordinates for ${shelter.name} sent to mobile directions.`)}
    ```
  - Violates architectural standard (Rule 9: No browser alert/confirm). No directions route is computed or transmitted.
- **Required Remediation:**
  1. Replace `alert()` with an interactive modal or direct link supporting standard geo-schemes:
     - Web: `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}` or OpenStreetMap directions URL.
     - Mobile: `geo:${lat},${lng}?q=${encodeURIComponent(shelter.name)}`.
  2. Offer an in-app mini-map modal showing the straight-line/evacuation route corridor.

---

### DEF-08: Citizen Safety Assistant Hardcoded Flood Response
- **Affected Files:**
  - Frontend: `frontend/src/pages/CitizenDashboard.tsx` (lines 72–92)
  - Backend RAG: `backend/app/api/v1/endpoints/ai.py`
- **Technical Mechanism:**
  - `handleChat` implements a mock offline fallback:
    ```ts
    setTimeout(() => {
      let reply = "Please stay indoors and monitor official channels.";
      if (text.includes("shelter")) reply = "Nearest open shelters are listed in the Shelter Finder below.";
      else if (text.includes("water") || text.includes("flood")) reply = "Move to higher ground immediately...";
      else reply = "For flood emergencies, stay away from low-lying areas...";
      setMessages(prev => [...prev, { sender: 'bot', text: reply }]);
    }, 600);
    ```
  - Zero backend network requests are made.
  - Queries for Earthquake, Fire, Cyclone, or Tsunami inevitably fall back to the default flood warning text.
- **Required Remediation:**
  1. Connect `CitizenDashboard.tsx` chat to `POST /api/v1/ai/rag/query`.
  2. Pass context parameter `audience: "citizen"` to ensure layman-accessible triage recommendations.
  3. Ensure backend knowledge base is populated with multi-hazard emergency advice.

---

### DEF-09: Volunteer Turn-by-Turn Route Uses Alert Placeholder
- **Affected Files:**
  - Frontend: `frontend/src/pages/VolunteerDashboard.tsx` (line 220)
- **Technical Mechanism:**
  - Button event handler:
    ```tsx
    onClick={() => alert('GPS coordinates sent to turn-by-turn navigation.')}
    ```
  - Browser alert placeholder without route calculation, waypoints, or map navigation.
- **Required Remediation:**
  1. Replace alert with an in-app Route Waypoint Dialog displaying distance, estimated travel duration, and route hazard warnings.
  2. Provide external navigation dispatch links (`geo:` or Google Maps intent with destination coordinates).

---

### DEF-10: Responder Fleet "Accept Task" Uses Alert Placeholder
- **Affected Files:**
  - Frontend: `frontend/src/pages/VolunteerDashboard.tsx` (line 280)
  - Backend Endpoints: `backend/app/api/v1/endpoints/dispatch.py`, `backend/app/api/v1/endpoints/incidents.py`
- **Technical Mechanism:**
  - Button event handler:
    ```tsx
    onClick={() => alert(`Assigned ${inc.incident_code} to your responder queue.`)}
    ```
  - No network request is executed.
  - Database status is unaffected:
    - Incident status remains `REPORTED` or `DISPATCHED`.
    - No record is created in `rescue_tasks` or `unit_assignments`.
    - Command Center supervisors have zero visibility that a responder has claimed the task.
- **Required Remediation:**
  1. Call backend `POST /api/v1/dispatch/assignments` or `POST /api/v1/incidents/{id}/transition`.
  2. Update responder task state in frontend store and database.
  3. Trigger Commander notification via WebSocket.

---

### DEF-11: NGO Stock Dispatch Fails with "[object Object]"
- **Affected Files:**
  - Frontend: `frontend/src/pages/NGOCoordination.tsx` (lines 110–135)
  - Backend Route: `backend/app/api/v1/endpoints/resources.py` (lines 85–105)
- **Technical Mechanism:**
  1. **Parameter Name Mismatch:** Frontend executes:
     ```ts
     await api.post(`/api/v1/resources/${resourceId}/dispatch?dispatch_quantity=${qty}`);
     ```
  2. Backend endpoint defines:
     ```python
     @router.post("/{resource_id}/dispatch")
     def dispatch_resource(
         resource_id: str,
         quantity: int = Query(..., gt=0),
         db: Session = Depends(get_db)
     ):
     ```
  3. FastAPI fails with HTTP 422: `{"detail": [{"loc": ["query", "quantity"], "msg": "field required", "type": "value_error.missing"}]}`.
  4. **Stringification Bug:**
     ```ts
     catch (e: any) {
       toast.error('Error: ' + (e.response?.data?.detail || e.message));
     }
     ```
     FastAPI 422 `detail` is a JSON array of objects. JavaScript string concatenation converts `[{...}]` to `"[object Object]"`.
- **Required Remediation:**
  1. Change query parameter name in frontend to `quantity`:
     ```ts
     await api.post(`/api/v1/resources/${resourceId}/dispatch?quantity=${qty}`);
     ```
  2. Robustly parse error details:
     ```ts
     const detail = e.response?.data?.detail;
     const message = Array.isArray(detail) ? detail.map(d => d.msg).join(', ') : (detail || e.message);
     toast.error(`Dispatch failed: ${message}`);
     ```

---

## 3. Architecture & Security Review
- **Role-Based Access Control (RBAC):** All remediations preserve strict role checks:
  - Incident transitions and resource dispatches require authenticated Responder, NGO Manager, or Ops Commander roles.
  - Citizen SOS remains publicly accessible or verified via lightweight citizen session tokens.
- **Audit Logging:** Every state change (SOS creation, task acceptance, stock decrement) connects to backend `audit_logs` service.
- **UI Integrity:** Browser `alert()` and `confirm()` calls are systematically eliminated in favor of layered, accessible application dialogs.
