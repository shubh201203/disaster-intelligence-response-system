# DIRS — Manual Acceptance Testing: API Traceability Matrix
**Document ID:** `DIRS-AUDIT-ATM-2026-11-15`  
**Status:** Completed Analysis  
**Auditor:** Senior Full-Stack, QA, GIS, AI & Security Reviewer  

---

## 1. Traceability Overview

This document provides end-to-end API traceability for all 11 findings discovered during manual acceptance testing. Each finding is mapped from user interaction down to database models, state machines, and real-time events.

---

## 2. End-to-End Traceability Matrix

### Finding DEF-01: Approve Dispatch Dialog Appears Behind GIS Map
- **Frontend Component:** `frontend/src/pages/DecisionReview.tsx` -> `frontend/src/components/common/ConfirmDialog.tsx`
- **Trigger Event:** User clicks "Approve Dispatch" on an operational recommendation card.
- **Frontend Handler:** `handleApproveDispatch(planId: string)` opens `ConfirmDialog`.
- **HTTP Method & Endpoint:** `POST /api/v1/dispatch/plans/{plan_id}/approve`
- **Request Payload:** None (or `{ "notes": "Approved by Commander" }`)
- **Backend Route:** `backend/app/api/v1/endpoints/dispatch.py::approve_dispatch_plan`
- **Service Layer:** `backend/app/services/dispatch_service.py::approve_plan`
- **Database Models & Tables:** `DispatchPlan` (`dispatch_plans`), `Incident` (`incidents`), `AuditLog` (`audit_logs`)
- **Response Schema:** `DispatchPlanResponse(id, status="APPROVED", approved_at, approved_by)`
- **UI State Update:** On confirmation, updates plan status badge to `APPROVED`, invalidates React Query cache, refreshes dispatch list.
- **Breakdown Point:** CSS stacking context defect in `ConfirmDialog.tsx`. The modal is rendered inline without React portal at `z-50`, placing it beneath Leaflet map controls (`z-1000`) and popups (`z-700`).

---

### Finding DEF-02: AI Situation Query Inaction / Refusal Response
- **Frontend Component:** `frontend/src/components/ai/AICopilotPanel.tsx`
- **Trigger Event:** User submits query text in the search input box (e.g. "FIRE", "EARTHQUAKE", "FLOOD").
- **Frontend Handler:** `handleQuery()` sets `loading = true` and invokes `aiApi.queryRAG(query)`.
- **HTTP Method & Endpoint:** `POST /api/v1/ai/rag/query`
- **Request Payload:**
  ```json
  {
    "query": "FIRE EVACUATION PROTOCOL",
    "top_k": 5
  }
  ```
- **Backend Route:** `backend/app/api/v1/endpoints/ai.py::rag_query`
- **Service Layer:** `backend/app/services/rag_service.py::RAGService.query` -> `GroundingValidator.validate`
- **Database Models & Tables:** `KnowledgeChunk` (`knowledge_chunks`), `KnowledgeDocument` (`knowledge_documents`)
- **Response Schema:**
  ```json
  {
    "answer": "I don't have enough verified information in the official guidelines to answer this query safely.",
    "is_grounded": false,
    "confidence_score": 0.1537,
    "sources": []
  }
  ```
- **UI State Update:** `AICopilotPanel.tsx` sets `response = res.data.answer`.
- **Breakdown Point:**
  1. Missing fire/earthquake documents in DB cause `similarity_score < 0.35`, returning canned refusal.
  2. UI fails to show spinner or clear previous refusal output, making repeated queries appear unresponsive.

---

### Finding DEF-03: GIS KNN Spatial Query Produces No Visible Results
- **Frontend Component:** `frontend/src/pages/GISCommandCenter.tsx`
- **Trigger Event:** User selects KNN query tool on the GIS map and clicks a point.
- **Frontend Handler:** `handleSpatialQuery(e: LeafletMouseEvent)`
- **HTTP Method & Endpoint:** `POST /api/v1/gis/spatial-query`
- **Current (Faulty) Payload:**
  ```json
  {
    "point": [80.2707, 13.0827],
    "target_layer": "shelters",
    "k_nearest": 3
  }
  ```
- **Required Backend Payload:**
  ```json
  {
    "query_type": "knn",
    "latitude": 13.0827,
    "longitude": 80.2707,
    "target_layer": "shelters",
    "k_nearest": 3
  }
  ```
- **Backend Route:** `backend/app/api/v1/endpoints/gis.py::spatial_query`
- **Service Layer:** `backend/app/services/gis_service.py::GISService.query_knn`
- **Database Models & Tables:** `Shelter` (`shelters`), `Hospital` (`hospitals`), using PostGIS `ST_Distance(geom, ST_SetSRID(ST_Point(lon, lat), 4326))`
- **Response Schema:** GeoJSON `FeatureCollection` containing nearest entity features and distance attributes.
- **Breakdown Point:** Payload mismatch causes HTTP 422 error. Frontend lacks error handling and expects `res.data.results` instead of GeoJSON `res.data.features`.

---

### Finding DEF-04: Scenario Laboratory Reports All Zero Metrics
- **Frontend Component:** `frontend/src/pages/ScenarioLaboratory.tsx`
- **Trigger Event:** User clicks "Run Simulation" button.
- **Frontend Handler:** `runSimulationMutation.mutate()`
- **HTTP Method & Endpoint:** `POST /api/v1/simulation/run`
- **Current (Faulty) Payload:**
  ```json
  {
    "scenario_type": "SCENARIO_A",
    "custom_params": {},
    "generate_response_plan": true
  }
  ```
- **Required Backend Payload:**
  ```json
  {
    "scenario_id": "SCEN-FLOOD-001"
  }
  ```
- **Backend Route:** `backend/app/api/v1/endpoints/simulation.py::run_simulation`
- **Service Layer:** `backend/app/services/simulation_service.py::SimulationService.run_scenario`
- **Database Models & Tables:** `Scenario` (`scenarios`), `SimulationRun` (`simulation_runs`)
- **Backend Response Schema:**
  ```json
  {
    "run_id": "sim-run-uuid",
    "scenario_id": "SCEN-FLOOD-001",
    "status": "COMPLETED",
    "delta": {
      "unmet_evacuees_delta": 420.0,
      "response_time_delta_mins": -18.5,
      "resource_utilization_delta": 0.35
    }
  }
  ```
- **Breakdown Point:**
  1. Absence of `scenario_id` triggers `SCEN_NOOP` baseline scenario, producing true 0 deltas.
  2. Frontend inspects `result.deltas?.unmet_evacuees_delta` (plural), resulting in `undefined || 0`.

---

### Finding DEF-05: Multi-Scenario Comparison Does Not Execute
- **Frontend Component:** `frontend/src/pages/ScenarioLaboratory.tsx`
- **Trigger Event:** User selects multiple scenarios and clicks "Compare Selected".
- **Frontend Handler:** `handleCompareScenarios()`
- **HTTP Method & Endpoint:** `POST /api/v1/simulation/compare`
- **Current (Faulty) Payload:**
  ```json
  {
    "scenario_types": ["SCENARIO_A", "SCENARIO_B"]
  }
  ```
- **Required Backend Payload:**
  ```json
  {
    "scenario_ids": ["SCEN-FLOOD-001", "SCEN-CYC-001"],
    "comparison_metrics": ["evacuees_served", "bottlenecks"]
  }
  ```
- **Backend Route:** `backend/app/api/v1/endpoints/simulation.py::compare_scenarios`
- **Service Layer:** `backend/app/services/simulation_service.py::SimulationService.compare_scenarios`
- **Database Models & Tables:** `SimulationRun` (`simulation_runs`), `Scenario` (`scenarios`)
- **Response Schema:** `MultiScenarioComparisonResponse(comparisons: List[ScenarioMetricSummary])`
- **Breakdown Point:** Backend schema validator rejects `scenario_types` with HTTP 422; frontend fails silently without updating charts.

---

### Finding DEF-06: Citizen SOS Distress Report Flow Traceability
- **Frontend Component:** `frontend/src/components/citizen/EmergencySOSButton.tsx`
- **Trigger Event:** Citizen clicks "SEND EMERGENCY SOS".
- **Frontend Handler:** `sendSOS()`
- **Current Route Invoked:** `POST /api/v1/incidents` with hardcoded Chennai coordinates (`13.0827, 80.2707`).
- **Target Specialized Route:** `POST /api/v1/incidents/sos`
- **Target Payload:**
  ```json
  {
    "latitude": 13.0827,
    "longitude": 80.2707,
    "accuracy_meters": 12.5,
    "distress_type": "MEDICAL_EVACUATION",
    "contact_phone": "+91-9876543210",
    "details": "Trapped on roof due to rising water."
  }
  ```
- **Backend Route:** `backend/app/api/v1/endpoints/incidents.py::create_sos_incident`
- **Service Layer:** `backend/app/services/incident_service.py::IncidentService.create_sos`
- **Database Models & Tables:**
  - `Incident`: `severity = "CRITICAL"`, `priority_score = 99.0`, `source = "CITIZEN_SOS"`
  - `IncidentReport`: Raw report capture
  - `AuditLog`: `action = "CITIZEN_SOS_TRIGGERED"`
- **WebSocket Broadcast:** Channel `commander_alerts`, Event `SOS_TRIGGERED` with incident coordinates.
- **Breakdown Point:** Frontend bypassed the dedicated `/sos` route, omitting critical priority escalation and real-time Commander WebSocket dispatch notifications.

---

### Finding DEF-07: Shelter View "Get Directions" Uses Alert Placeholder
- **Frontend Component:** `frontend/src/components/citizen/ShelterFinder.tsx`
- **Trigger Event:** Citizen clicks "Get Directions" on a nearby shelter card.
- **Frontend Handler:** `onClick={() => alert(...)}`
- **HTTP Method & Endpoint:** None (No API call or navigation link exists).
- **Target Architecture:**
  - In-App: Route Modal displaying distance, bearing, and evacuation corridor status via `/api/v1/gis/route-corridor`.
  - External Launch: Standard navigation URI:
    - Web: `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
    - Mobile: `geo:${lat},${lng}?q=${encodeURIComponent(shelter.name)}`
- **Database Models Involved:** `Shelter` (`shelters` with PostGIS coordinates).
- **Breakdown Point:** Unimplemented stub using browser `alert()`.

---

### Finding DEF-08: Citizen Safety Assistant Hardcoded Flood Response
- **Frontend Component:** `frontend/src/pages/CitizenDashboard.tsx`
- **Trigger Event:** Citizen types any safety question into the assistant input.
- **Frontend Handler:** `handleChat(text: string)`
- **HTTP Method & Endpoint:** None (Mock `setTimeout` in client code).
- **Target Backend Route:** `POST /api/v1/ai/rag/query`
- **Target Request Payload:**
  ```json
  {
    "query": "What should I do during an earthquake?",
    "top_k": 3,
    "audience": "citizen"
  }
  ```
- **Service Layer:** `RAGService.query` querying public safety documents.
- **Database Models & Tables:** `KnowledgeChunk`, `KnowledgeDocument`.
- **Breakdown Point:** Hardcoded client-side heuristic with a default fallback to flood advice; no network request executed.

---

### Finding DEF-09: Volunteer Turn-by-Turn Route Uses Alert Placeholder
- **Frontend Component:** `frontend/src/pages/VolunteerDashboard.tsx`
- **Trigger Event:** Volunteer clicks "Turn-by-Turn Route" on an assigned incident.
- **Frontend Handler:** `onClick={() => alert('GPS coordinates sent to turn-by-turn navigation.')}`
- **HTTP Method & Endpoint:** None.
- **Target Architecture:**
  - Route Waypoint Modal showing turn-by-turn waypoint coordinates and road hazard conditions.
  - External Launch: Navigation intent (`geo:lat,lng` or external map provider).
- **Breakdown Point:** Incomplete implementation relying on browser `alert()`.

---

### Finding DEF-10: Responder Fleet "Accept Task" Uses Alert Placeholder
- **Frontend Component:** `frontend/src/pages/VolunteerDashboard.tsx`
- **Trigger Event:** Responder clicks "Accept Task" on an incident in the queue.
- **Frontend Handler:** `onClick={() => alert(`Assigned ${inc.incident_code} to your responder queue.`)}`
- **HTTP Method & Endpoint:** None (No backend request executed).
- **Target Route:** `POST /api/v1/dispatch/assignments` or `POST /api/v1/incidents/{incident_id}/transition`
- **Target Request Payload:**
  ```json
  {
    "incident_id": "inc-uuid-1234",
    "unit_id": "VOL-UNIT-07",
    "new_status": "DISPATCHED"
  }
  ```
- **Backend Route:** `backend/app/api/v1/endpoints/incidents.py::transition_status`
- **Service Layer:** `backend/app/services/incident_service.py`
- **Database Models & Tables:** `Incident` (`status` -> `ASSIGNED`), `RescueTask` / `UnitAssignment`, `AuditLog`.
- **WebSocket Broadcast:** Channel `dispatch_updates`, Event `TASK_ACCEPTED`.
- **Breakdown Point:** Complete frontend stub; task acceptance is never recorded in backend or database.

---

### Finding DEF-11: NGO Stock Dispatch Fails with "[object Object]"
- **Frontend Component:** `frontend/src/pages/NGOCoordination.tsx`
- **Trigger Event:** NGO Coordinator submits dispatch quantity for a warehouse resource.
- **Frontend Handler:** `handleDispatchResource(resourceId, quantity)`
- **HTTP Method & Endpoint:** `POST /api/v1/resources/{resource_id}/dispatch`
- **Current (Faulty) Request URL:** `/api/v1/resources/{id}/dispatch?dispatch_quantity=50`
- **Required Request URL:** `/api/v1/resources/{id}/dispatch?quantity=50`
- **Backend Route:** `backend/app/api/v1/endpoints/resources.py::dispatch_resource`
  ```python
  @router.post("/{resource_id}/dispatch")
  def dispatch_resource(
      resource_id: str,
      quantity: int = Query(..., gt=0),
      db: Session = Depends(get_db)
  ):
  ```
- **Database Models & Tables:** `Resource` (`resources` -> decrements `available_quantity`), `AuditLog`.
- **Response Schema:** `ResourceResponse(id, available_quantity, status)`
- **Error Breakdown:**
  1. Query parameter mismatch triggers FastAPI HTTP 422 error response.
  2. Frontend toast catches the error and evaluates `'Error: ' + e.response.data.detail`, rendering `Error: [object Object]` because `detail` is a list of validation error dictionaries.

---

## 3. Summary of API Fixes Required

| Defect ID | Layer | Contract / Implementation Fix |
| :--- | :--- | :--- |
| **DEF-01** | Frontend | Render `ConfirmDialog` in `createPortal(..., document.body)` with `z-[9999]`. |
| **DEF-02** | Full-Stack | Ingest Fire/Earthquake knowledge; display loading indicator & ungrounded warning banner. |
| **DEF-03** | Frontend | Update payload to `{ query_type: 'knn', latitude, longitude, target_layer, k_nearest }`; parse `features`. |
| **DEF-04** | Frontend | Send `scenario_id` instead of `scenario_type`; map `simulationResult.delta` (singular). |
| **DEF-05** | Frontend | Pass `scenario_ids: List[str]` in comparison mutation payload. |
| **DEF-06** | Frontend | Route SOS triggers to `POST /api/v1/incidents/sos` with live browser geolocation. |
| **DEF-07** | Frontend | Replace `alert()` with Navigation Direction modal and standard geo-links. |
| **DEF-08** | Frontend | Replace mock chatbot with `POST /api/v1/ai/rag/query`. |
| **DEF-09** | Frontend | Replace `alert()` with Route Navigation modal and waypoint mapping. |
| **DEF-10** | Full-Stack | Connect "Accept Task" to `POST /api/v1/incidents/{id}/transition` and update responder state. |
| **DEF-11** | Frontend | Change query parameter to `?quantity=${qty}` and format FastAPI 422 error arrays. |
