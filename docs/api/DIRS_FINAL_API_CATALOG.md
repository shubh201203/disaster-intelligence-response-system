# DIRS — Definitive Final API Catalog
## Disaster Intelligence and Response System (DIRS)

**Document Identifier:** `DIRS-CAPSTONE-API-003`  
**Classification:** OFFICIAL / API CONTRACT SPECIFICATION  
**Target Release:** DIRS v5.2 (Capstone Release)  
**Parent Programme:** Phase 6G / Accelerated Work Package 4 (Capstone Packaging & Verification)  
**Publication Date:** November 18, 2026  
**Status:** Certified / Complete  

---

## 1. API Architecture & Global Conventions

* **Base URL Prefix:** `/api/v1`
* **Protocol:** HTTP/1.1 and WebSockets (`/ws/feed`)
* **Transport Encryption:** TLS 1.3
* **Authentication Scheme:** `Authorization: Bearer <JWT>`
* **Content Type:** `application/json` (Payloads and responses)
* **Error Response Standard:**
  ```json
  {
    "detail": "Descriptive diagnostic error message"
  }
  ```
  FastAPI structured validation failures (`HTTP 422`):
  ```json
  {
    "detail": [
      {
        "loc": ["body", "field_name"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
  ```

---

## 2. Core Authentication & Identity Endpoints

### 2.1 User Login
* **Endpoint:** `POST /api/v1/auth/login`
* **Auth Requirement:** Public
* **Request Payload:**
  ```json
  {
    "email": "admin@dirs.gov",
    "password": "AdminPassword123!"
  }
  ```
* **Response (`200 OK`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "user": {
      "id": "usr-001-uuid",
      "email": "admin@dirs.gov",
      "full_name": "Disaster Commissioner",
      "role": "GOVT",
      "phone": "+91-44-25619001",
      "is_active": true
    }
  }
  ```
* **Error Codes:** `401 Unauthorized` (Invalid credentials), `422 Unprocessable` (Malformed body).

### 2.2 Current User Profile
* **Endpoint:** `GET /api/v1/auth/me`
* **Auth Requirement:** Authenticated (Any role)
* **Response (`200 OK`):** `UserResponse` DTO.
* **Error Codes:** `401 Unauthorized` (Expired / missing token).

---

## 3. Incident Management & SOS Endpoints

### 3.1 Report Disaster Incident
* **Endpoint:** `POST /api/v1/incidents`
* **Auth Requirement:** Authenticated (`CITIZEN`, `VOLUNTEER`, `GOVT`, `ADMIN`)
* **Request Payload (`IncidentCreate`):**
  ```json
  {
    "title": "Severe Flash Flooding at Adyar Bridge",
    "description": "Water rising above road level, multiple vehicles stranded.",
    "disaster_type": "FLOOD",
    "severity": 4,
    "latitude": 13.0060,
    "longitude": 80.2570,
    "address": "Adyar Bridge Road, Ward 172, Chennai",
    "casualties": 3,
    "needs_evacuation": true,
    "damage_level": "HEAVY"
  }
  ```
* **Response (`201 Created`):** `IncidentResponse` object with UUID `id`, `status: "REPORTED"`, and timestamps.
* **Operational Purpose:** Primary intake for citizen and responder disaster observations.

### 3.2 Emergency SOS Distress Signal
* **Endpoint:** `POST /api/v1/incidents/sos`
* **Auth Requirement:** Authenticated (`CITIZEN`, `VOLUNTEER`, `GOVT`)
* **Request Payload:**
  ```json
  {
    "latitude": 13.0060,
    "longitude": 80.2570,
    "address": "Near Velachery MRTS Station",
    "device_battery": 35
  }
  ```
* **Response (`201 Created`):** High-priority incident record with `severity: 5` and automated alert broadcast.

### 3.3 Incident Verification & Triage
* **Endpoint:** `PUT /api/v1/incidents/{incident_id}/verify`
* **Auth Requirement:** Authenticated (`GOVT`, `ADMIN`)
* **Request Payload:**
  ```json
  {
    "action": "VERIFY",
    "notes": "Confirmed on CCTV and field patrol unit 4."
  }
  ```
* **Response (`200 OK`):** Updated incident record with `status: "VERIFIED"`.

---

## 4. Volunteer Mobilization & Field Inspection Endpoints

### 4.1 Assigned Tasks Queue
* **Endpoint:** `GET /api/v1/volunteers/my-tasks`
* **Auth Requirement:** Authenticated (`VOLUNTEER`)
* **Response (`200 OK`):** List of `RescueTask` entities assigned to the logged-in volunteer.

### 4.2 Update Task Pipeline Status
* **Endpoint:** `POST /api/v1/volunteers/tasks/{task_id}/status`
* **Auth Requirement:** Authenticated (`VOLUNTEER`, `GOVT`)
* **Request Payload:**
  ```json
  {
    "status": "EN_ROUTE"
  }
  ```
* **Response (`200 OK`):** Updated task status.

### 4.3 Submit Field Damage Inspection
* **Endpoint:** `POST /api/v1/recovery/damage-assessments/field-inspection`
* **Auth Requirement:** Authenticated (`VOLUNTEER`, `GOVT`, `ADMIN`)
* **Request Payload (`DamageAssessmentFieldCreate`):**
  ```json
  {
    "facility_name": "Adyar Primary Health Centre",
    "sector": "HEALTH",
    "ward": "Ward 172",
    "observed_damage_level": "MODERATE",
    "structural_notes": "Roof sheet dislodged, perimeter wall collapsed.",
    "immediate_hazard": "Exposed electrical wiring near flooded floor.",
    "assessor_confidence": 0.88,
    "latitude": 13.0062,
    "longitude": 80.2575,
    "incident_id": "optional-incident-uuid"
  }
  ```
* **Response (`201 Created`):** `RecoveryAssessment` DTO with `verification_status: "PENDING_VERIFICATION"`.

---

## 5. NGO Relief Logistics & Inventory Endpoints

### 5.1 Humanitarian Inventory Stock Query
* **Endpoint:** `GET /api/v1/resources`
* **Auth Requirement:** Authenticated (`NGO`, `GOVT`, `ADMIN`)
* **Response (`200 OK`):** List of `ResourceResponse` objects (water purification units, rations, blankets, medical kits).

### 5.2 Field Relief Demands Feed
* **Endpoint:** `GET /api/v1/resources/requests`
* **Auth Requirement:** Authenticated (`NGO`, `GOVT`, `ADMIN`)
* **Response (`200 OK`):** List of `ResourceRequest` items requested by responders or evacuation shelters.

### 5.3 Concurrency-Safe Inventory Stock Dispatch
* **Endpoint:** `POST /api/v1/resources/{resource_id}/dispatch?quantity=50`
* **Auth Requirement:** Authenticated (`NGO`, `GOVT`, `ADMIN`)
* **Response (`200 OK`):** Updated `Resource` record with decremented available quantity.
* **Operational Guard:** Uses SQLAlchemy `with_for_update()` to prevent race conditions during simultaneous field dispatches.

---

## 6. Infrastructure Precedence & Dependency Endpoints (Phase 6E / WP1)

### 6.1 Precedence Graph Extraction API
* **Endpoint:** `GET /api/v1/recovery/dependencies/graph?period_days=30.0`
* **Auth Requirement:** Authenticated (`GOVT`, `ADMIN`)
* **Response (`200 OK`):**
  ```json
  {
    "nodes": [
      {
        "id": "proj-001",
        "name": "Substation Clearance & Drainage",
        "sector": "POWER",
        "duration_periods": 2,
        "early_start": 1,
        "early_finish": 3,
        "late_start": 1,
        "late_finish": 3,
        "total_float": 0,
        "free_float": 0,
        "is_critical": true
      }
    ],
    "edges": [
      {
        "source": "proj-001",
        "target": "proj-002",
        "lag_periods": 0,
        "is_critical": true
      }
    ],
    "critical_path": ["proj-001", "proj-002"],
    "project_makespan": 5,
    "has_cycles": false,
    "cycle_details": null
  }
  ```

### 6.2 Dry-Run Dependency Edge Validation API
* **Endpoint:** `POST /api/v1/recovery/dependencies/validate-edge`
* **Auth Requirement:** Authenticated (`GOVT`, `ADMIN`)
* **Request Payload:**
  ```json
  {
    "predecessor_id": "proj-003",
    "successor_id": "proj-001",
    "lag_days": 0
  }
  ```
* **Response (`200 OK`):**
  ```json
  {
    "is_valid": false,
    "error_code": "CYCLIC_DEPENDENCY",
    "message": "Candidate dependency edge creates a circular cycle.",
    "cycle_path": ["proj-001", "proj-002", "proj-003", "proj-001"]
  }
  ```
* **Operational Invariant:** Pure read-only Kahn analysis. **Zero database mutations occur.**

---

## 7. Community Recovery Monitoring & Simulation Endpoints (Phase 6F / WP2)

### 7.1 Community Metrics Summary
* **Endpoint:** `GET /api/v1/recovery/monitoring/community-metrics/summary`
* **Auth Requirement:** Authenticated (`CITIZEN`, `VOLUNTEER`, `NGO`, `GOVT`, `ADMIN`)
* **Response (`200 OK`):**
  ```json
  {
    "total_wards_monitored": 15,
    "average_recovery_score": 78.4,
    "sector_restoration_averages": {
      "power": 85.0,
      "water": 74.5,
      "health": 80.0,
      "schools": 70.0,
      "livelihoods": 82.5
    },
    "freshness_distribution": {
      "FRESH": 12,
      "MODERATE": 3,
      "STALE_AMBER": 0,
      "EXPIRED_RED": 0
    }
  }
  ```

### 7.2 Vulnerability Rescoring Engine
* **Endpoint:** `POST /api/v1/recovery/monitoring/vulnerability-rescore`
* **Auth Requirement:** Authenticated (`GOVT`)
* **Request Payload:**
  ```json
  {
    "ward": "Ward 172",
    "observed_damage_level": "MODERATE",
    "observation_age_hours": 12.0
  }
  ```
* **Response (`200 OK`):**
  ```json
  {
    "ward": "Ward 172",
    "baseline_vulnerability": 0.65,
    "rescored_vulnerability": 0.58,
    "delta": -0.07,
    "confidence_factor": 0.94,
    "freshness_category": "FRESH"
  }
  ```

### 7.3 What-If Recovery Forward Simulation Workbench
* **Endpoint:** `POST /api/v1/recovery/simulation/what-if`
* **Auth Requirement:** Authenticated (`GOVT`)
* **Request Payload:**
  ```json
  {
    "horizon_periods": 12,
    "budget_multiplier": 1.25,
    "resource_capacity_multiplier": 1.0,
    "recurrence_shock_period": null,
    "priority_sector": "POWER"
  }
  ```
* **Response (`200 OK`):**
  ```json
  {
    "simulated_trajectory": [
      { "period": 1, "recovery_score": 42.0 },
      { "period": 2, "recovery_score": 51.5 },
      { "period": 12, "recovery_score": 96.0 }
    ],
    "bottlenecks": [
      { "resource_name": "Structural Concrete Crews", "deficit_units": 14, "impact": "HIGH" }
    ],
    "is_non_mutating": true
  }
  ```

---

## 8. Recovery Optimization Engine Endpoints (Phase 6D-B)

### 8.1 Evaluate Recovery Portfolio Optimization
* **Endpoint:** `POST /api/v1/recovery/optimization/evaluate`
* **Auth Requirement:** Authenticated (`GOVT`, `ADMIN`)
* **Request Payload (`RecoveryOptimizationRequest`):**
  - Horizon $T \in [1, 120]$.
  - Candidate projects with costs, durations, release dates, deadlines, and dependencies.
  - Periodic budgets with exact decimal strings.
  - Resource capacities and district equity targets.
* **Response (`200 OK` / `202 Accepted`):**
  ```json
  {
    "status": "OPTIMAL",
    "is_feasible": true,
    "schedule": [
      {
        "project_id": "proj-001",
        "start_period": 1,
        "completion_period": 2,
        "assigned_funding": "MUNICIPAL_DISASTER_FUND",
        "cost_inr": "25000000.00"
      }
    ],
    "solvency_summary": {
      "ccu_balance": 150000,
      "inr_balance": "84500000.00"
    },
    "diagnostics": []
  }
  ```
* **Error Handling:** Returns structured Tier 1–4 diagnostics if infeasible; returns `504 Gateway Timeout` or normalized `SOLVER_TIMEOUT` if CP-SAT search ceiling is exceeded.
