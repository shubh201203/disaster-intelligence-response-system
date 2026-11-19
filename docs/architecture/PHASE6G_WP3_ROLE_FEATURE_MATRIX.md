# DIRS — PHASE 6G WORK PACKAGE 3 ROLE-TO-FEATURE MATRIX
## Cross-Role Capabilities, Authorization Boundaries & Reuse Architecture

**Document Version:** 1.0.0  
**Phase Mapping:** Phase 6G Accelerated Programme — Work Package 3 (WP3)  
**Security Level:** Engineering Governance Specification  
**Status:** Canonical Reference  

---

## 1. Architectural Overview

The Disaster Intelligence and Response System (DIRS) enforces a strict **Role-Based Access Control (RBAC)** architecture across five authenticated user roles. This matrix details the operational capabilities, authorization policies, schema backing, offline resilience support, and reuse opportunities for each role.

```
                    ┌──────────────────────────────────────────────┐
                    │            DIRS UNIFIED APP SHELL            │
                    │        (Layout, Navbar, Sidebar, Auth)       │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌───────────────┬─────────────────┼─────────────────┬───────────────┐
         ▼               ▼                 ▼                 ▼               ▼
   ┌───────────┐   ┌───────────┐     ┌───────────┐     ┌───────────┐   ┌───────────┐
   │  CITIZEN  │   │ VOLUNTEER │     │    NGO    │     │   GOVT    │   │   ADMIN   │
   └─────┬─────┘   └─────┬─────┘     └─────┬─────┘     └─────┬─────┘   └─────┬─────┘
         │               │                 │                 │               │
  • SOS Distress   • Assigned Tasks   • Relief Stock    • Command HQ    • MILP Solver
  • Hazard Report  • Rescue Pipeline  • Stock Dispatch  • Precedence    • Budget Matrix
  • Shelter Grid   • Damage Inspect   • Incident Reqs   • Recovery Sim  • Infeasibility
  • Offline Drafts • Offline Drafts   • Org Scoping     • Verification  • Diagnostic Core
```

---

## 2. Comprehensive Role-to-Feature Matrix

| Feature / Capability | Citizen | Volunteer | NGO | Government (GOVT) | Administrator (ADMIN) | Backend Endpoint / Service | Database Schema Backing | Offline Resilience |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- | :---: |
| **Emergency SOS Distress Signal** | ✅ | ✅ | — | View | View | `POST /incidents/sos` | `incidents` | Supported (Draft Queue) |
| **Public Incident Hazard Reporting** | ✅ | ✅ | — | View / Verify | View | `POST /incidents` | `incidents` | Supported (IndexedDB Drafts) |
| **Structured Damage Assessment** | — | ✅ | ✅ | ✅ (Verify) | — | `POST /recovery/damage-assessments/field-inspection` | `recovery_assessments` | Supported (IndexedDB Drafts) |
| **Nearby Shelter Finder** | ✅ | ✅ | ✅ | ✅ | ✅ | `GET /shelters/nearby` | `shelters` | Cacheable |
| **RAG AI Safety Bot Guidance** | ✅ | ✅ | ✅ | ✅ | — | `POST /ai/rag/query` | `knowledge_chunks` | Online Only |
| **Assigned Rescue Tasks** | — | ✅ (Own Only) | — | Full Dispatch | — | `GET /volunteers/my-tasks` | `rescue_tasks` | Cacheable View |
| **Task Status Pipeline Transition** | — | ✅ (Own Only) | — | Override | — | `POST /volunteers/tasks/{id}/status` | `rescue_tasks`, `audit_logs` | Online Only |
| **Relief Inventory Stock Management** | — | — | ✅ (Own Org) | Full Oversight | — | `POST /resources`, `GET /resources` | `resources` | Online Only |
| **Stock Reservation & Dispatch** | — | — | ✅ (Own Org) | Full Oversight | — | `POST /resources/{id}/dispatch` | `resources`, `audit_logs` | Online Only |
| **Incident Resource Needs Coordination**| — | — | ✅ | Full Oversight | — | `GET /resources/requests` | `resource_requests` | Cacheable View |
| **Incident Verification & Triage** | — | — | — | ✅ | ✅ | `POST /incidents/{id}/verify` | `incidents` | Online Only |
| **Engineering Assessment Verification** | — | — | — | ✅ | — | `POST /recovery/damage-assessments/{id}/verify` | `recovery_assessments` | Online Only |
| **Infrastructure Precedence Network** | — | — | — | ✅ | — | `GET /recovery/dependencies/precedence-graph` | `recovery_projects`, `project_dependencies` | Online Only |
| **Dry-Run Edge Cycle Validation** | — | — | — | ✅ | — | `POST /recovery/dependencies/validate-edge` | Pure In-Memory CPM-PL | Online Only |
| **Community Recovery Indicators** | View | View | View | Full Access | Full Access | `GET /recovery/monitoring/community-metrics/summary` | `community_recovery_metrics` | Cacheable View |
| **What-If Recovery Simulation** | — | — | — | ✅ | ✅ | `POST /recovery/simulation/what-if` | Pure Read-Only Simulation | Online Only |
| **Vulnerability Rescoring Engine** | — | — | — | ✅ | ✅ | `POST /recovery/monitoring/vulnerability-rescore` | In-Memory Bayesian Rescorer | Online Only |
| **Recovery Optimization CP-SAT** | — | — | — | View / Run | ✅ (Full) | `POST /recovery/optimization/evaluate` | In-Memory CP-SAT Engine | Online Only |

---

## 3. Role-by-Role Forensic Analysis

### 3.1 Citizen Role (`CITIZEN`)
* **Core Mission:** Public disaster reporting, personal safety, emergency distress signaling, and shelter discovery.
* **Accessible Routes:** `/citizen`, `/citizen/report`, `/citizen/shelters`.
* **Existing Capabilities:**
  - Emergency SOS panic button with geolocation fallback to manual address description.
  - Public incident reporting (`ReportIncident.tsx`) with severity, casualty count, and infrastructure damage notes.
  - Grounded RAG chatbot for evacuation advice and safety protocols.
  - Shelter locator sorted by distance and occupancy.
* **WP3 Missing Capabilities & Enhancements:**
  - **Offline Draft Persistence:** Citizens in disaster disaster zones often face total cellular/Wi-Fi outages. Form state must persist locally in IndexedDB when network drops.
  - **Connection Status Telemetry:** Clear visual banner indicating online vs. offline connectivity state.
  - **Community Recovery Visibility:** High-level recovery progress indicator on dashboard informing citizens of municipal rehabilitation status without exposing sensitive engineering data.
* **Strict Security Boundaries:** Citizens have zero access to `/admin`, `/volunteer`, or `/ngo` routes. Direct navigation triggers automatic redirection to `/citizen`.

---

### 3.2 Volunteer Role (`VOLUNTEER`)
* **Core Mission:** Tactical on-the-ground rescue execution, responder status updates, and field damage/loss inspection.
* **Accessible Routes:** `/volunteer`, `/citizen/report`, `/citizen/shelters`.
* **Existing Capabilities:**
  - Profile card displaying certification, skills, and duty availability.
  - Assigned mission queue loaded from `/volunteers/my-tasks`.
  - Linear status pipeline transition (`ASSIGNED` $\to$ `ACCEPTED` $\to$ `EN_ROUTE` $\to$ `ARRIVED` $\to$ `COMPLETED`).
  - Tactical navigation modal with routing coordinates.
* **WP3 Missing Capabilities & Enhancements:**
  - **Field Inspection Form:** Volunteers on site can evaluate building and infrastructure damage. Providing an integrated Field Damage Inspection component backed by `POST /api/v1/recovery/damage-assessments/field-inspection`.
  - **Offline Field Inspection Drafts:** Volunteers frequently inspect collapsed structures or remote sectors without connectivity. Damage evaluations, structural notes, and GPS coordinates must persist in IndexedDB and queue for synchronization upon reconnection.
  - **Inspection Submission History & Status:** Feedback on pending vs. verified inspections submitted by the volunteer.
* **Strict Security Boundaries:** Volunteers cannot assign missions to themselves or alter other volunteers' tasks. Assignment is strictly governed by Government Command.

---

### 3.3 NGO Role (`NGO`)
* **Core Mission:** Relief logistics coordination, humanitarian commodity inventory, and emergency stock dispatch.
* **Accessible Routes:** `/ngo`, `/citizen/shelters`.
* **Existing Capabilities:**
  - Relief inventory stock management (`/resources`) with SKU creation and category tracking.
  - Transactional stock dispatch (`/resources/{id}/dispatch`) with concurrency locking (`with_for_update()`).
  - Inventory search and category filtering.
* **WP3 Schema Boundary & Gap Assessment:**
  - **Supported Ownership:** The `resources` table links directly to `users.id` via `owner_id` with `owner_type = "NGO"`. `NGOProfile` links to `users.id` providing verified organization credentials.
  - **Identified Schema Gap:** The database lacks an `ngo_pledges` table or an organization foreign key on `recovery_projects`. In accordance with prompt governance:
    > *Critical schema boundary: Do not store NGO identity in arbitrary fields such as `supplier_info` as a substitute for proper ownership.*
  - **Coordination Solution:** WP3 implements organization-scoped inventory views, displays NGO organization registration details, and surfaces incoming incident `resource_requests` so NGOs can view and fulfill urgent field requirements without violating schema boundaries.

---

### 3.4 Government Officer Role (`GOVT`)
* **Core Mission:** Emergency Command Center operations, volunteer dispatch, incident verification, infrastructure precedence visualization, and recovery simulation.
* **Accessible Routes:** `/admin` (Command Center), `/admin/simulation` (GIS & What-If Simulation), `/admin/recovery-optimization`, `/citizen`, `/volunteer`, `/ngo`.
* **Existing Capabilities:**
  - Incident triage and status verification.
  - Tactical volunteer rescue task assignment.
  - Precedence network visualization (`PrecedenceGraphVisualizer.tsx`).
  - What-If recovery forward simulation (`RecoverySimulationWorkbench.tsx`).
* **WP3 Enhancements:**
  - Coherent cross-module navigation between emergency operations and recovery intelligence.
  - Field inspection review and engineering verification workflow.
  - Unified operational readiness metrics.

---

### 3.5 Administrator Role (`ADMIN`)
* **Core Mission:** Mathematical optimization model configuration, solver parameter governance, and decision-support constraint solving.
* **Accessible Routes:** `/admin/recovery-optimization`.
* **Existing Capabilities:**
  - Comprehensive MILP CP-SAT recovery solver workbench.
  - 4-tier infeasibility diagnostics and assumption core inspection.
  - Dual-ledger solvency matrix (INR & CCU).
  - 1-based periodic Gantt timeline.
* **Boundary Invariance:** ADMIN controls remain 100% frozen under Gate 2 baseline guarantees.

---

## 4. Reuse Opportunities & Component Architecture

1. **Design System:** Reusing `OperationalCard`, `StatusBadge`, `SeverityBadge`, `KPIStat`, `ConfirmDialog`, `PageHeader`, `LoadingSkeleton`.
2. **API Client:** Leveraging existing `apiClient` with Axios JWT interceptor, correlation headers, and 130s solver timeouts.
3. **Draft Engine:** Reusable IndexedDB store schema (`dirs_offline_drafts`) serving both Citizen Incident Reports and Volunteer Field Inspections.
