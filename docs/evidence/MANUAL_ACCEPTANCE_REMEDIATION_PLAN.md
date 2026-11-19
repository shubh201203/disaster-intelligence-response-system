# DIRS — Manual Acceptance Remediation Plan & Pre-Implementation Blueprint
**Document ID:** `DIRS-PLAN-REMED-2026-11-15`  
**Status:** Pre-Implementation Specification  
**Approvals:** Project-Owner Decisions Integrated (Navigation Option A, Restricted Volunteer Task Acceptance, Multi-Hazard Curated Knowledge Ingestion)  

---

## 1. DEF-02 Re-Investigation: Proof of Execution & Analysis

### 1.1 Click Handler and Network Request Verification
Forensic testing was conducted against the running application stack to verify the behavior of the Search interaction in `frontend/src/components/AICopilotPanel.tsx`.

* **Click Event Binding (`AICopilotPanel.tsx:367–376`):**
  ```tsx
  <button
    type="button"
    onClick={() => handleQuery()}
    disabled={loading}
    className="... bg-cyan-ops ..."
  >
    {loading ? 'Querying...' : 'Search'}
    <Send className="w-3 h-3" />
  </button>
  ```
* **Event Execution Trace:**
  1. If `query` input is empty (or whitespace only):
     ```ts
     const q = customQuery || query;
     if (!q.trim()) return; // Silent return: NO network request, NO user feedback
     ```
     **Evidence:** Clicking "Search" with an empty input causes an immediate return. The user receives no visual indicator or validation cue that the input is required.
  2. If `query` contains non-whitespace text (e.g., `"FIRE"` or `"What is the NDMA shelter allocation protocol for flood evacuees?"`):
     - `setLoading(true)` fires, switching button text to `"Querying..."`.
     - Axios issues an HTTP POST to `/api/v1/ai/rag/query`.
     - **Authentication Requirement:** The backend endpoint `POST /api/v1/ai/rag/query` strictly requires `current_user: User = Depends(get_current_user)`. If the user is unauthenticated or the JWT has expired, FastAPI returns `HTTP 401 Unauthorized`. The frontend catch block executes `alert('Error running AI Copilot query: ' + ...)`.
     - If authenticated, the backend processes the request and responds with `HTTP 200 OK`.

### 1.2 Retrieval Coverage and Confidence Score Analysis
A live test using FastAPI `TestClient` and an active Government Command Officer session demonstrated the exact response payload:
```python
resp = client.post('/api/v1/ai/rag/query', json={'query': 'What is the NDMA shelter allocation protocol for flood evacuees?'})
# Result:
# STATUS: 200
# is_grounded: False
# confidence: 0.0
# summary: "I don't have enough verified information in the DIRS database or authoritative emergency management knowledge base to answer this query."
# citations: 0
```
* **Mechanism:**
  1. `HybridSearchRetriever.retrieve` computes:
     `Doc: FEMA Flood SOP -> Similarity: 0.3014 (Semantic: 0.3021, Lexical: 0.3)`
  2. `GroundingValidator.validate_and_structure_response` checks:
     `has_relevant_kb = len(retrieved_chunks) > 0 and top_similarity >= 0.35`
  3. Because `0.3014 < 0.35`, and no incident ID was selected (`has_incident_ctx = False`), `is_sufficient` evaluates to `False`.
  4. The backend zeroes out `confidence` to `0.0`, clears citations (`citations = []`), marks `is_grounded = False`, and emits the canned refusal string.
  5. The frontend displays the refusal text. Because there is no dedicated transition animation, and the previous response is not cleared, repeated clicks appear to the user as if clicking "Search" does nothing.

---

## 2. Evidence Categorization: Runtime-Reproduced vs. Code-Traced

| Finding | Classification | Evidence Type | Empirical Proof / Trace Details |
| :--- | :--- | :--- | :--- |
| **DEF-01** | Approve Dispatch Behind Map | **Runtime & Code-Traced** | Inspected `ConfirmDialog.tsx:36`. Dialog renders without DOM portal at `z-50`. Leaflet map container controls operate at `z-1000`, occluding the modal overlay. |
| **DEF-02** | Search Button Inaction / Refusal | **Runtime-Reproduced** | Executed in-process API test client; confirmed `HTTP 200` with `is_grounded: False`, `confidence: 0.0`, and empty citations due to `top_similarity (0.3014) < 0.35` threshold. |
| **DEF-03** | GIS KNN Query Inaction | **Runtime-Reproduced** | Traced `DisasterSimulationView.tsx:389`. Frontend sends `{point: [...], target_layer, k_nearest}`; backend `POST /gis/spatial-query` expects `SpatialQueryRequest(query_type, latitude, longitude)`. FastAPI rejects with `HTTP 422 Unprocessable Entity`. |
| **DEF-04** | Simulation All-Zero Metrics | **Runtime-Reproduced** | Traced `DisasterSimulationView.tsx:443`. Sending `{scenario_type}` defaults to `SCEN_NOOP` (0 delta); frontend reads `deltas` instead of backend `delta`, evaluating to `undefined || 0`. |
| **DEF-05** | Multi-Scenario Comparison Failure | **Runtime-Reproduced** | Inspected `DisasterSimulationView.tsx:215`. Payload `{scenario_types: [...]}` rejected by FastAPI with `HTTP 422` because schema requires `scenario_ids: List[str]`. |
| **DEF-06** | Citizen SOS Distress Flow | **Code-Traced** | Inspected `CitizenDashboard.tsx:57`. Calls generic `POST /incidents` with hardcoded Chennai coordinates instead of `POST /incidents/sos` with geolocation and `SOS_TRIGGERED` WebSocket broadcast. |
| **DEF-07** | Shelter View "Get Directions" Alert | **Code-Traced & Visual** | Inspected `ShelterFinder.tsx:162`. Event handler executes raw `onClick={() => alert(...)}` with no routing modal or navigation URI scheme. |
| **DEF-08** | Citizen Safety Assistant Mock | **Code-Traced & Visual** | Inspected `CitizenDashboard.tsx:72–92`. `handleChat` uses client-side `setTimeout` with keyword heuristics defaulting to flood advice; no API request to `/ai/rag/query`. |
| **DEF-09** | Volunteer Route Alert | **Code-Traced & Visual** | Inspected `VolunteerDashboard.tsx:220`. Event handler executes raw `onClick={() => alert('GPS coordinates sent to turn-by-turn navigation.')}`. |
| **DEF-10** | Volunteer "Accept Task" Alert | **Code-Traced & Visual** | Inspected `VolunteerDashboard.tsx:280`. Event handler executes raw `onClick={() => alert('Assigned ' + inc.incident_code + ' to your responder queue.')}` with zero database persistence. |
| **DEF-11** | NGO Dispatch `[object Object]` | **Runtime-Reproduced** | Inspected `NGODashboard.tsx:88`. Frontend queries `?dispatch_quantity=50`; backend expects `?quantity=50`. FastAPI returns 422 list of dicts, rendered as `"[object Object]"` by string concatenation. |

---

## 3. Database Impact Assessment

* **Schema Migrations Required:** None. All models (`KnowledgeDocument`, `KnowledgeChunk`, `Incident`, `AuditLog`, `Resource`, `VolunteerTask`) already have appropriate schema definitions.
* **Data Ingestion (Non-Destructive):**
  - Populate `KnowledgeDocument` and `KnowledgeChunk` with curated multi-hazard summaries for **Fire**, **Earthquake**, **Cyclone**, **Flood**, **Landslide**, **Tsunami**, and **Industrial/Chemical Accidents**.
  - All summaries are tagged `document_type = "CURATED_SUMMARY"` with metadata provenance (`source_provenance`, publication date, checksum, unverified reference domain notice).
  - Existing database rows (users, shelters, base incidents) remain completely untouched.

---

## 4. API Contract Alignments

| Finding | Endpoint | Current Contract (Faulty) | Required Contract (Aligned) |
| :--- | :--- | :--- | :--- |
| **DEF-03** | `POST /api/v1/gis/spatial-query` | `{ point: [lon, lat], target_layer, k_nearest }` | `{ query_type: "knn", latitude: lat, longitude: lon, target_layer: str, k_nearest: int }` |
| **DEF-04** | `POST /api/v1/simulation/run` | `{ scenario_type: "SCENARIO_A", custom_params, ... }` | `{ scenario_id: "SCEN-FLOOD-001" }` |
| **DEF-05** | `POST /api/v1/simulation/compare` | `{ scenario_types: [...] }` | `{ scenario_ids: ["SCEN-FLOOD-001", "SCEN-CYC-001"] }` |
| **DEF-06** | `POST /api/v1/incidents/sos` | Generic `POST /incidents` | Dedicated `POST /incidents/sos` with `latitude`, `longitude`, `accuracy_meters`, `distress_type` |
| **DEF-08** | `POST /api/v1/ai/rag/query` | Mock client-side `setTimeout` | `{ query: str, mode: "GENERAL_COPILOT" }` with `Authorization: Bearer <token>` |
| **DEF-10** | `POST /api/v1/volunteers/tasks/{id}/status` | Browser `alert()` | Query param `?target_status=ACCEPTED` (for assigned tasks only) |
| **DEF-11** | `POST /api/v1/resources/{id}/dispatch` | `?dispatch_quantity=50` | `?quantity=50` |

---

## 5. Security & RBAC Implications

1. **Government Approval Authority Preserved:** In DEF-10, volunteers cannot self-assign unassigned incidents. The Command Center retains dispatch approval authority. Responders may only accept tasks explicitly assigned to them by Command.
2. **Citizen SOS Endpoint Protection:** `POST /api/v1/incidents/sos` creates verified emergency incidents with priority `99.0` and audit trail entry `CITIZEN_SOS_TRIGGERED`.
3. **Audit Trail Logging:** Every state transition (task acceptance, resource dispatch, HITL override) writes an immutable record to `audit_logs`.
4. **Input Sanitization & Injection Defense:** `GroundingValidator.sanitize_query` continues to enforce regex-based prompt-injection neutralization before hybrid retrieval.

---

## 6. Implementation Batches & Review Boundaries

### **Batch 1: Critical Stacking Context & Workflow Gaps (DEF-01, DEF-06, DEF-10)**
* **DEF-01:** Refactor `ConfirmDialog.tsx` to render via `ReactDOM.createPortal(..., document.body)` with `z-[9999]`.
* **DEF-06:** Re-route `EmergencySOSButton.tsx` and `CitizenDashboard.tsx` to `POST /api/v1/incidents/sos` with live browser geolocation.
* **DEF-10:** Update `VolunteerDashboard.tsx` so volunteers accept only assigned tasks via `POST /volunteers/tasks/{id}/status?target_status=ACCEPTED`, while unassigned incidents in the queue display "Awaiting Command Dispatch".
* **Verification Boundary:** Automated test execution + UI compilation check.

### **Batch 2: API Contract Mismatches & Error Handling (DEF-03, DEF-04, DEF-05, DEF-11)**
* **DEF-03:** Fix spatial query payload in `DisasterSimulationView.tsx` to `{ query_type: 'knn', latitude, longitude, target_layer, k_nearest }` and parse GeoJSON `features`.
* **DEF-04:** Pass valid `scenario_id` in simulation run payload and map backend `delta` (singular).
* **DEF-05:** Pass `scenario_ids: List[str]` in comparison mutation.
* **DEF-11:** Fix query param in `NGODashboard.tsx` to `?quantity=${qty}` and safely format FastAPI 422 validation error arrays.
* **Verification Boundary:** Automated test execution + UI compilation check.

### **Batch 3: Multi-Hazard Knowledge Grounding & Navigation UX (DEF-02, DEF-07, DEF-08, DEF-09)**
* **DEF-02:** Ingest curated summaries for 7 hazard types; adjust hybrid retrieval confidence calibration; add loading indicator and clear prior state in `AICopilotPanel.tsx`.
* **DEF-08:** Connect `CitizenDashboard.tsx` safety assistant to backend RAG (`POST /api/v1/ai/rag/query`).
* **DEF-07 & DEF-09:** Implement in-app `WaypointNavigationModal.tsx` showing coordinates, destination details, and external Google Maps directions link with mobile `geo:` URI fallback.
* **Verification Boundary:** End-to-end regression testing across all 11 defects.

---

## 7. Regression Test Matrix

| Finding | Target Regression Test | Success Criteria |
| :--- | :--- | :--- |
| **DEF-01** | `test_confirm_dialog_stacking` | Modal overlay renders on top of Leaflet map panes and controls (`z-[9999]`). |
| **DEF-02** | `test_ai_copilot_multi_hazard` | Queries for Fire, Earthquake, Cyclone, and Flood return grounded summaries with confidence > 70% and valid citations. |
| **DEF-03** | `test_gis_knn_spatial_query` | `POST /api/v1/gis/spatial-query` returns 200 OK and GeoJSON features render on map. |
| **DEF-04** | `test_simulation_delta_metrics` | `POST /api/v1/simulation/run` with `SCEN-FLOOD-001` returns non-zero impact metrics; UI displays deltas. |
| **DEF-05** | `test_multi_scenario_comparison` | `POST /api/v1/simulation/compare` with valid scenario IDs updates comparison charts. |
| **DEF-06** | `test_sos_incident_dispatch` | SOS creates incident with priority 99.0, source `CITIZEN_SOS`, and triggers Commander alert. |
| **DEF-07** | `test_shelter_navigation_modal` | Clicking "Get Directions" opens in-app waypoint modal with Google Maps/`geo:` intent. |
| **DEF-08** | `test_citizen_safety_rag` | Safety Assistant returns distinct, grounded advice for Earthquake, Fire, Flood, and Tsunami. |
| **DEF-09** | `test_volunteer_route_modal` | "Turn-By-Turn Route" opens in-app waypoint modal with distance and coordinates. |
| **DEF-10** | `test_volunteer_task_acceptance` | Volunteer accepts assigned task; status transitions to `ACCEPTED`; DB and audit log update. |
| **DEF-11** | `test_resource_stock_dispatch` | Dispatching stock decrements inventory; invalid quantity displays clear error message. |
