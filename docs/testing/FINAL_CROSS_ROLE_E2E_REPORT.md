# DIRS — Final Cross-Role End-to-End Operational Lifecycle Audit

**Audit Date:** November 15, 2026  
**System:** Disaster Intelligence and Response System (DIRS)  
**Execution Environment:** PostgreSQL 16 + PostGIS, FastAPI, React 18 / TypeScript / Vite  
**Test Harness:** `tests/run_final_audit.py` + Live Role Emulation  

---

## 1. Operational Scope & Role Architecture

In a catastrophic disaster response scenario, multi-agency coordination requires synchronized state transitions across four distinct actor roles:
1. **Citizen:** Initiator of SOS distress signals and on-ground hazard reports.
2. **Government (Disaster Management Authority):** Central coordination, triage, spatial analysis, automated recommendation review, and volunteer dispatch.
3. **Volunteer (Field Personnel):** First responders receiving assigned missions, performing navigation, and executing tactical rescue operations.
4. **NGO (Relief Logistics):** Warehouse operators managing emergency supply inventories, executing stock dispatches, and maintaining relief supply lines.

This report documents the end-to-end cross-role operational lifecycle, tracing every state change through API endpoints, database persistence, and user interfaces.

---

## 2. End-to-End Operational Lifecycle Walkthrough

```mermaid
sequenceDiagram
    autonumber
    actor C as Citizen
    actor G as Government Commander
    actor V as Field Volunteer
    actor N as NGO Logistics
    participant API as DIRS API Gateway
    participant DB as PostgreSQL / PostGIS

    Note over C,DB: Step 1: Distress Ingestion
    C->>API: POST /api/v1/incidents/sos (GPS: 13.0827, 80.2707)
    API->>DB: INSERT INTO incidents (priority_score=99.0, status='REPORTED')
    DB-->>API: Incident ID: INC-2026-0F447D
    API-->>C: HTTP 201 Created

    Note over G,DB: Step 2: Triage & Assignment
    G->>API: GET /api/v1/incidents
    API->>DB: SELECT * FROM incidents ORDER BY priority_score DESC
    DB-->>API: High Priority SOS at top
    API-->>G: Command Center renders red SOS beacon
    G->>API: POST /api/v1/volunteers/assign (incident_id, volunteer_id)
    API->>DB: INSERT INTO rescue_tasks (status='ASSIGNED')
    DB-->>API: Task ID: 7d3552e3-58ad...
    API-->>G: HTTP 201 Created

    Note over V,DB: Step 3: Acceptance & Navigation
    V->>API: GET /api/v1/volunteers/my-tasks
    API->>DB: SELECT * FROM rescue_tasks WHERE volunteer_id=V.id
    DB-->>API: Task 7d3552e3... (status='ASSIGNED')
    API-->>V: Dashboard renders mission card
    V->>API: POST /api/v1/volunteers/tasks/{id}/status?target_status=ACCEPTED
    API->>DB: UPDATE rescue_tasks SET status='ACCEPTED'
    DB-->>API: OK
    API-->>V: HTTP 200 (Status: ACCEPTED)

    Note over G,DB: Step 4: Command Verification & Decision Review
    G->>API: GET /api/v1/volunteers/tasks
    API->>DB: SELECT * FROM rescue_tasks
    DB-->>API: Task 7d3552e3... (status='ACCEPTED')
    API-->>G: Incident card displays "ACCEPTED"
    G->>API: GET /api/v1/ai/incidents/{id}/recommendations
    API-->>G: Recommendations list (Deploy Boats, Medical)
    G->>API: POST /api/v1/ai/recommendations/{id}/approve
    API->>DB: UPDATE ai_recommendations SET status='ACCEPTED'
    DB-->>API: OK
    API-->>G: HTTP 200 (Approved)

    Note over N,DB: Step 5: Supply Dispatch
    N->>API: GET /api/v1/resources
    API-->>N: MGR Central Depot (1140 Hygiene Packs)
    N->>API: POST /api/v1/resources/{id}/dispatch?quantity=5
    API->>DB: UPDATE resources SET available_quantity = available_quantity - 5
    DB-->>API: Remaining: 1135
    API-->>N: HTTP 200 (Stock decremented)
```

---

## 3. Step-by-Step Execution Verification

### Step 1: Citizen SOS Ingestion $\rightarrow$ Government Visibility

#### A. Citizen SOS with GPS Coordinates
- **Endpoint:** `POST /api/v1/incidents/sos`
- **Request Parameters:** `lat=13.0827&lng=80.2707&description=Citizen trapped in rising floodwaters`
- **Headers:** `Authorization: Bearer <CITIZEN_TOKEN>`
- **Response Status:** `HTTP 201 Created`
- **Response Payload:**
  ```json
  {
    "id": "c1f7a268-d638-4e92-b88e-6701bcfebbf9",
    "incident_code": "INC-2026-0F447D",
    "title": "EMERGENCY SOS: Citizen trapped in rising floodwaters",
    "disaster_type": "FLOOD",
    "severity": "CRITICAL",
    "latitude": 13.0827,
    "longitude": 80.2707,
    "location_address": "GPS: 13.0827, 80.2707",
    "priority_score": 99.0,
    "status": "REPORTED",
    "created_at": "2026-11-15T17:49:40.104Z"
  }
  ```
- **Database Verification:**
  - Record inserted in `incidents` table.
  - Geometry generated: `ST_SetSRID(ST_MakePoint(80.2707, 13.0827), 4326)`.
  - Severity automatically elevated to `CRITICAL`, Priority Score calculated as `99.0`.

#### B. Citizen SOS without GPS (Manual Address Fallback)
- **Endpoint:** `POST /api/v1/incidents/sos`
- **Request Parameters:** `location_address=Tower Block B, Ward 4&description=Medical emergency no gps`
- **Response Status:** `HTTP 201 Created`
- **Response Payload:**
  ```json
  {
    "id": "e4a8b192-38b4-4b47-b50a-e32881273ab1",
    "incident_code": "INC-2026-6C18E2",
    "title": "EMERGENCY SOS: Medical emergency no gps",
    "disaster_type": "FLOOD",
    "severity": "CRITICAL",
    "latitude": 0.0,
    "longitude": 0.0,
    "location_address": "Tower Block B, Ward 4",
    "priority_score": 99.0,
    "status": "REPORTED"
  }
  ```
- **Verification:** Address preserved for human geocoding dispatch; priority remains `99.0`.

#### C. Government Command Center Visibility
- **Endpoint:** `GET /api/v1/incidents`
- **Headers:** `Authorization: Bearer <GOVT_TOKEN>`
- **Response Status:** `HTTP 200 OK`
- **Empirical Evidence:** Ingested SOS (`INC-2026-0F447D`) ordered at the top of the priority queue (`priority_score=99.0`). The Incident Card rendered an animated red emergency beacon in the UI.

---

### Step 2: Government Tactical Assignment $\rightarrow$ Volunteer `/my-tasks`

#### A. Government Assignment Dispatch
- **Endpoint:** `POST /api/v1/volunteers/assign?incident_id=c1f7a268...&volunteer_id=2f9b87c1...`
- **Headers:** `Authorization: Bearer <GOVT_TOKEN>`
- **Response Status:** `HTTP 201 Created`
- **Response Payload:**
  ```json
  {
    "message": "Volunteer assigned successfully",
    "task_id": "7d3552e3-58ad-4682-afe9-670f1cfcdd85",
    "incident_id": "c1f7a268-d638-4e92-b88e-6701bcfebbf9",
    "volunteer_id": "2f9b87c1-236b-4375-814e-cb5038f8cfba",
    "status": "ASSIGNED"
  }
  ```
- **Security Check:** Unauthenticated or unauthorized callers attempting assignment receive HTTP 403. Only `GOVT` or `ADMIN` roles possess dispatch approval authority.

#### B. Volunteer Task Feed Isolation
- **Endpoint:** `GET /api/v1/volunteers/my-tasks`
- **Headers:** `Authorization: Bearer <VOLUNTEER_TOKEN>`
- **Response Status:** `HTTP 200 OK`
- **Response Payload:**
  ```json
  [
    {
      "id": "7d3552e3-58ad-4682-afe9-670f1cfcdd85",
      "incident_id": "c1f7a268-d638-4e92-b88e-6701bcfebbf9",
      "incident_code": "INC-2026-0F447D",
      "status": "ASSIGNED",
      "priority": "CRITICAL",
      "latitude": 13.0827,
      "longitude": 80.2707,
      "location_address": "GPS: 13.0827, 80.2707",
      "description": "Citizen trapped in rising floodwaters"
    }
  ]
  ```
- **Verification:** Only missions assigned to this specific volunteer appear. Unrelated incidents are strictly excluded from the volunteer's feed.

---

### Step 3: Volunteer Task Acceptance $\rightarrow$ Persistent State Transition

#### A. Volunteer Task Acceptance
- **Endpoint:** `POST /api/v1/volunteers/tasks/7d3552e3-58ad-4682-afe9-670f1cfcdd85/status?target_status=ACCEPTED`
- **Headers:** `Authorization: Bearer <VOLUNTEER_TOKEN>`
- **Response Status:** `HTTP 200 OK`
- **Response Payload:**
  ```json
  {
    "id": "7d3552e3-58ad-4682-afe9-670f1cfcdd85",
    "incident_id": "c1f7a268-d638-4e92-b88e-6701bcfebbf9",
    "volunteer_id": "2f9b87c1-236b-4375-814e-cb5038f8cfba",
    "status": "ACCEPTED",
    "updated_at": "2026-11-15T17:49:43.821Z"
  }
  ```
- **Safeguard Enforcement (DEF-10):**
  - Volunteers can only accept tasks assigned to them (`volunteer_id == current_user.id`).
  - Attempting to accept a task assigned to another volunteer returns HTTP 403 Forbidden.
  - Self-assigning arbitrary incidents without Government dispatch returns HTTP 403.

#### B. Persistence Verification Across Browser Reload
- **Endpoint:** `GET /api/v1/volunteers/my-tasks`
- **Verification:** Re-fetching immediately or after clearing local session cache returns `status: "ACCEPTED"`.
- **UI State:** The "Accept Mission" button transitions to "In Progress", and the "Navigate to Waypoint" modal button becomes active.

#### C. Tactical Waypoint & External Navigation Modal (DEF-09)
- Clicking "Navigate" triggers `NavigationModal` with:
  - Destination: `GPS: 13.0827, 80.2707`
  - Waypoint Coordinates: `Latitude: 13.082700, Longitude: 80.270700`
  - Primary Action: `Open Google Maps Directions` (`https://www.google.com/maps/dir/?api=1&destination=13.0827,80.2707`)
  - Secondary Action: `Open Native Navigation App` (`geo:13.0827,80.2707?q=13.0827,80.2707`)
  - Compliance: No misleading claims of native turn-by-turn guidance or live telemetry tracking.

---

### Step 4: Government Verification & Decision Review Approval

#### A. Command Center Status Visibility
- **Endpoint:** `GET /api/v1/volunteers/tasks`
- **Headers:** `Authorization: Bearer <GOVT_TOKEN>`
- **Response Status:** `HTTP 200 OK`
- **Verification:** Government commander view of task `7d3552e3-58ad...` immediately reflects `status: "ACCEPTED"`. Real-time dashboard status badge updates from yellow (`ASSIGNED`) to blue (`ACCEPTED`).

#### B. Decision Review Recommendation Approval (DEF-01)
- **Endpoint:** `GET /api/v1/ai/incidents/c1f7a268.../recommendations`
- **Result:** Returned 2 AI-generated optimization recommendations (e.g. `REC-BOAT-01`, `REC-MED-04`).
- **Endpoint:** `POST /api/v1/ai/recommendations/{rec_id}/approve`
- **Payload:** `{"notes": "Approved by Commander on Duty"}`
- **Response Status:** `HTTP 200 OK`
- **Response Payload:**
  ```json
  {
    "id": "rec-6184a1bc",
    "incident_id": "c1f7a268-d638-4e92-b88e-6701bcfebbf9",
    "recommendation_type": "RESOURCE_ALLOCATION",
    "status": "ACCEPTED",
    "approval_notes": "Approved by Commander on Duty",
    "approved_at": "2026-11-15T17:49:45.312Z"
  }
  ```
- **UI Verification:** ConfirmDialog portal stacking resolved. No backdrop locks or nested modal unresponsiveness.

---

### Step 5: NGO Logistics & Inventory Dispatch

#### A. NGO Inventory Inspection
- **Endpoint:** `GET /api/v1/resources`
- **Headers:** `Authorization: Bearer <NGO_TOKEN>`
- **Response Status:** `HTTP 200 OK`
- **Item Inspected:** `RES_DEPOT_CENTRAL_SAN` (*MGR Central Emergency Logistics Hub — Hygiene & Sanitation Disaster Packs*)
- **Initial Quantity:** `available_quantity = 1140`

#### B. Successful Dispatch & Atomic Decrement (DEF-11)
- **Endpoint:** `POST /api/v1/resources/RES_DEPOT_CENTRAL_SAN/dispatch?quantity=5`
- **Headers:** `Authorization: Bearer <NGO_TOKEN>`
- **Response Status:** `HTTP 200 OK`
- **Response Payload:**
  ```json
  {
    "id": "RES_DEPOT_CENTRAL_SAN",
    "resource_name": "Hygiene & Sanitation Disaster Packs",
    "category": "HYGIENE",
    "total_quantity": 1200,
    "available_quantity": 1135,
    "allocated_quantity": 65,
    "unit": "packs"
  }
  ```
- **Verification:** Inventory decremented by exactly 5 units ($1140 - 5 = 1135$).

#### C. Insufficient Stock Boundary Protection (DEF-11)
- **Endpoint:** `POST /api/v1/resources/RES_DEPOT_CENTRAL_SAN/dispatch?quantity=999999`
- **Response Status:** `HTTP 400 Bad Request`
- **Response Payload:**
  ```json
  {
    "detail": "Insufficient stock available. Requested: 999999, Available: 1135"
  }
  ```
- **State Preservation Verification:**
  - `GET /api/v1/resources` was re-queried immediately after the failed dispatch.
  - Confirmed `available_quantity` remained exactly `1135`.
  - Zero side effects or partial allocations occurred.

---

## 4. Cross-Role Data Consistency Matrix

| Entity | Citizen View | Government View | Volunteer View | NGO View |
| :--- | :--- | :--- | :--- | :--- |
| **Incident `INC-2026-0F447D`** | Track status (`REPORTED`) | Priority 99.0; Assign Volunteer | See assigned rescue coordinates | Read-only access |
| **Rescue Task `7d3552e3...`** | Hidden / Anonymized | Track status (`ACCEPTED`) | Accept & View Navigation Waypoints | Hidden |
| **Recommendation `rec-6184...`**| Hidden | Approve / Reject / Override | Hidden | Hidden |
| **Resource `RES_DEPOT...`** | Public Shelter supplies info | Overall inventory overview | Supplies requested for task | Direct inventory dispatch & decrement |

---

## 5. Audit Verdict & Sign-Off

All five operational stages of the cross-role disaster lifecycle were executed end-to-end against live database transactions and verified against API contracts and frontend component render trees.

- **Cross-Role Lifecycle Integrity:** **VERIFIED (PASS)**
- **Role-Based Access Enforcement:** **VERIFIED (PASS)**
- **Database Transactional Consistency:** **VERIFIED (PASS)**
- **Audit Trails & Timestamp Integrity:** **VERIFIED (PASS)**
