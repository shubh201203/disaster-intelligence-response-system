# DIRS Phase 6A — API & Integration Design Specification
## RESTful Endpoints, Schema Contracts, Role-Based Access Control, and Service Boundaries

**Document ID:** `DIRS-PHASE6A-DOC-07`  
**System:** Disaster Intelligence and Response System (DIRS)  
**Classification:** API CONTRACT & INTEGRATION SPECIFICATION  
**Author:** Principal Full-Stack Systems Architect & API Designer  

---

## 1. API Architecture Overview

The Phase 6 Recovery API is mounted as a dedicated router group under the existing `/api/v1` namespace:
- Base Prefix: `/api/v1/recovery`
- Protocol: JSON over HTTPS, Bearer JWT Authentication (`OAuth2PasswordBearer`)
- Design Standards: OpenAPI 3.1 compliant, explicit Pydantic 2.x response schemas, strict HTTP status semantics.

---

## 2. Recovery Endpoint Catalog

### 2.1 Post-Disaster Damage Assessment

#### `POST /api/v1/recovery/assessments`
- **Role Permission:** `GOVT`, `VOLUNTEER`
- **Purpose:** Ingests a structured engineering damage assessment for a facility or infrastructure asset.
- **Request Body:**
  ```json
  {
    "incident_id": "c1f7a268-d638-4e92-b88e-6701bcfebbf9",
    "sector": "HEALTH",
    "facility_name": "District Primary Health Centre Sector 4",
    "damage_level": "MODERATE",
    "is_operational": false,
    "estimated_reconstruction_cost": 2450000.0,
    "structural_notes": "Eastern wing roof sheared; boundary wall collapsed; medical refrigeration functional on backup power.",
    "evidence_media_urls": ["/static/uploads/dmg_phc_01.jpg"],
    "latitude": 13.0850,
    "longitude": 80.2750
  }
  ```
- **Response Status:** `HTTP 201 Created`
- **Response Schema:** Returns `RecoveryAssessmentResponse` with generated `id`, `assessment_code`, and `verification_status: "PENDING_VERIFICATION"`.

#### `POST /api/v1/recovery/assessments/{id}/verify`
- **Role Permission:** `GOVT` only (Human-in-the-loop gate)
- **Purpose:** Official government validation or rejection of a field assessment.
- **Request Body:**
  ```json
  {
    "action": "VERIFY",
    "verified_cost": 2300000.0,
    "notes": "Verified by Executive Engineer PWD. Structural frame intact; re-entry permitted after roof reinforcement."
  }
  ```
- **Response Status:** `HTTP 200 OK`

---

### 2.2 Recovery Needs & Double-Count Reconciliation

#### `GET /api/v1/recovery/needs`
- **Role Permission:** `GOVT`, `NGO`, `CITIZEN`
- **Query Parameters:** `ward_code`, `district`, `sector`
- **Response Status:** `HTTP 200 OK`
- **Response Payload:** Returns array of aggregated needs by ward with `is_reconciled: true` confirming reconciliation against census baseline caps to prevent double-counting.

---

### 2.3 Capital Recovery Projects & Dependencies

#### `POST /api/v1/recovery/projects`
- **Role Permission:** `GOVT`
- **Purpose:** Formal creation of an actionable capital reconstruction project.
- **Request Body:**
  ```json
  {
    "title": "Sub-station 33kV Feeder Cable Reconstruction",
    "sector": "POWER",
    "need_id": "need-71829a",
    "estimated_cost": 4800000.0,
    "estimated_duration_days": 21,
    "lead_agency": "State Electricity Board (TANGEDCO)",
    "latitude": 13.0820,
    "longitude": 80.2680
  }
  ```
- **Response Status:** `HTTP 201 Created`

#### `POST /api/v1/recovery/dependencies`
- **Role Permission:** `GOVT`
- **Purpose:** Adds a Directed Acyclic Graph (DAG) edge between two recovery projects.
- **Request Body:**
  ```json
  {
    "predecessor_project_id": "proj-access-road-01",
    "successor_project_id": "proj-substation-02",
    "dependency_type": "FINISH_TO_START",
    "lag_days": 2,
    "rationale": "Heavy utility cranes require access road stabilization prior to transformer delivery."
  }
  ```
- **Error Handling:** Returns `HTTP 400 Bad Request` with detail `"Cyclic dependency detected: Adding this edge creates a cycle in the project graph"` if cycle validation fails.

---

### 2.4 Optimization & Prioritization Solvers

#### `POST /api/v1/recovery/prioritization/calculate`
- **Role Permission:** `GOVT`
- **Purpose:** Computes the Multi-Criteria Recovery Priority Index (MCPI) across all approved candidate projects.
- **Request Body:**
  ```json
  {
    "weight_life_safety": 0.30,
    "weight_criticality": 0.25,
    "weight_vulnerability": 0.20,
    "weight_dependency": 0.15,
    "weight_economic": 0.10
  }
  ```
- **Constraint:** Weights must sum to $1.0 \pm 10^{-4}$. Returns `HTTP 422 Unprocessable Entity` if weights do not reconcile.
- **Response Status:** `HTTP 200 OK`
- **Response Schema:** Returns ranked project array with individual score breakdown and confidence values.

#### `POST /api/v1/recovery/restoration-graph/solve`
- **Role Permission:** `GOVT`
- **Purpose:** Solves the Critical Path Method (CPM) and Multi-Period Project Scheduling problem using OR-Tools.
- **Request Body:**
  ```json
  {
    "planning_horizon_weeks": 26,
    "periodic_budget_envelope": 15000000.0,
    "enforce_critical_path": true
  }
  ```
- **Response Status:** `HTTP 200 OK`
- **Response Payload:** Returns makespan $T_{\max}$, list of critical path nodes, float schedule ($ES, EF, LS, LF, TF$), and cash-flow burn rate per period.

---

### 2.5 Government Decision & Approval Gates

#### `POST /api/v1/recovery/projects/{id}/approve`
- **Role Permission:** `GOVT` (Administrative Authority)
- **Request Body:**
  ```json
  {
    "funding_source": "STATE_DISASTER_RECOVERY_FUND",
    "approved_budget": 4800000.0,
    "sanction_order_number": "SDRF/REC/2026/ORD-881",
    "notes": "Approved following technical vetting by TANGEDCO Chief Engineer."
  }
  ```
- **Response Status:** `HTTP 200 OK`
- **Side Effect:** Dispatches immutable record to `audit_logs` and `recovery_override_logs`.

---

### 2.6 Community Recovery Monitoring & Staleness

#### `GET /api/v1/recovery/community-monitoring`
- **Role Permission:** `ALL_ROLES` (Public Dashboard)
- **Response Payload:** Ward-level recovery progress, percentage of restored utilities, shelter-to-home transition ratios, and indicator freshness flags (`FRESH`, `STALE_AMBER`, `EXPIRED_RED`).

---

### 2.7 Recovery What-If Scenario Simulator

#### `POST /api/v1/recovery/simulation/run`
- **Role Permission:** `GOVT`
- **Purpose:** Executes a what-if simulation (e.g. 25% funding cut, 3-week cement supply chain delay) against a cloned project graph.
- **Guarantees:** Live operational project records and financial accounts are strictly unmodified (`is_simulated: true`, `status: "PROPOSED"`).
- **Response Status:** `HTTP 200 OK`
- **Response Schema:** Comparative delta showing delayed completion dates, dropped projects, and unmet community demand.
