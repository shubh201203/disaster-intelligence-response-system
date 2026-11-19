# DIRS — Capstone Evidence Extraction: Role-by-Role Functional Inventory
## Module 04: Five-Role Persona Analysis, Access Controls & Cross-Layer Feature Matrix

**Document Identifier:** `DIRS-CAPSTONE-EVIDENCE-04`  
**Classification:** OFFICIAL / ACADEMIC CAPSTONE EVIDENCE  
**Degree Programme:** Bachelor of Technology (B.Tech) in Computer Science & Engineering  
**Institution:** VIT-AP University, Andhra Pradesh, India  
**Target Release:** DIRS v6.0 (Enterprise Hardened)  
**Audit Status:** STRICT READ-ONLY FORENSIC EXTRACTION  
**Evidence Sources:** `frontend/src/pages/`, `frontend/src/components/`, `backend/app/routers/`, `backend/app/core/deps.py`  

---

## 1. Role-by-Role Detailed Functional Inventory

DIRS enforces a strict least-privilege role hierarchy spanning five distinct user roles: `CITIZEN`, `VOLUNTEER`, `NGO`, `GOVT`, and `ADMIN`.

```
                  [ADMIN] (Super-Administrator / Optimization Planner)
                     |
                  [GOVT] (Government Command / Municipal Civil Engineer)
                     |
         +-----------+-----------+
         |                       |
       [NGO]                [VOLUNTEER]
  (Humanitarian Relief)  (Field Rescue & Inspection)
         |                       |
         +-----------+-----------+
                     |
                 [CITIZEN] (General Public / Evacuee)
```

---

### 1.1 Persona 1: CITIZEN

- **Primary Mission:** Crisis reporting, emergency survival beacon, shelter discovery, and recovery tracking.
- **Dashboard & Pages:**
  - `/citizen`: Citizen Home Dashboard with municipal recovery KPI stats, active safety alerts, and grounded RAG emergency assistant.
  - `/citizen/report`: Multi-step Incident Reporting Form with offline draft drawer.
  - `/shelters`: Interactive Geospatial Shelter Finder with distance and capacity filtering.
- **Available Actions:**
  - Submit emergency incident report with GPS coordinates, disaster category, injuries, and description.
  - Trigger one-touch SOS distress beacon.
  - Save, edit, view, and manually synchronize offline incident drafts.
  - Query grounded civil defense assistant using RAG knowledge chunks.
  - Query nearest emergency shelters within specified kilometer radii.
- **Backend APIs:**
  - `POST /api/v1/incidents` (with optional `Idempotency-Key`)
  - `POST /api/v1/incidents/sos`
  - `GET /api/v1/shelters/nearby`
  - `GET /api/v1/recovery/monitoring/community-metrics/summary`
  - `POST /api/v1/ai/rag/query`
- **Database Entities:** `users`, `citizen_profiles`, `incidents`, `incident_reports`, `alerts`, `shelters`, `knowledge_chunks`.
- **Business Rules & Restrictions:**
  - Cannot assign rescue tasks to volunteers.
  - Cannot certify field damage inspections.
  - Cannot view administrative precedence DAGs or trigger CP-SAT portfolio solvers.
  - Offline drafts are strictly isolated to the citizen's own user ID.
- **Relevant Components & Services:**
  - Frontend: `CitizenDashboard.tsx`, `ReportIncident.tsx`, `ShelterFinder.tsx`, `DraftSyncManager.tsx`.
  - Backend: `IncidentService`, `ShelterService`, `RAGService`, `CommunityMonitoringService`.

---

### 1.2 Persona 2: VOLUNTEER

- **Primary Mission:** On-the-ground rescue mission execution and field structural damage inspections.
- **Dashboard & Pages:**
  - `/volunteer`: Volunteer Mission Console, active rescue task queue, pipeline status update controls.
  - `/volunteer/inspection` (or tab): Standardized Field Damage Assessment Intake form.
- **Available Actions:**
  - View assigned rescue tasks with victim coordinates and emergency urgency score.
  - Transition task pipeline state: `ASSIGNED` $\to$ `IN_PROGRESS` $\to$ `COMPLETED` $\to$ `CANCELLED`.
  - Submit structural damage inspection reports (hazard type, damage percentage, structural habitability status, estimated restoration cost in INR).
  - Save and synchronize offline field damage assessment drafts.
- **Backend APIs:**
  - `GET /api/v1/volunteers/my-tasks`
  - `POST /api/v1/volunteers/tasks/{id}/status`
  - `POST /api/v1/recovery/damage-assessments/field-inspection` (with `Idempotency-Key`)
- **Database Entities:** `volunteer_profiles`, `rescue_tasks`, `recovery_assessments`.
- **Business Rules & Restrictions:**
  - Cannot self-assign rescue tasks (tasks must be assigned by Government Command or system dispatcher).
  - Field inspection reports enter status `PENDING_VERIFICATION`; volunteers cannot certify their own inspections.
  - Prohibited from accessing NGO supply inventory depots.
- **Relevant Components & Services:**
  - Frontend: `VolunteerDashboard.tsx`, `VolunteerFieldInspection.tsx`, `DraftSyncManager.tsx`.
  - Backend: `VolunteerService`, `RescueService`, `DamageAssessmentService`.

---

### 1.3 Persona 3: NGO (Non-Governmental Organization)

- **Primary Mission:** Humanitarian relief supply coordination, inventory management, and depot dispatching.
- **Dashboard & Pages:**
  - `/ngo`: NGO Logistics Hub, humanitarian inventory table, field relief demand feed.
- **Available Actions:**
  - Manage inventory across essential disaster relief categories (rations, water purification, trauma kits, blankets, emergency boats).
  - Toggle inventory scoping: "All Hubs" (aggregated disaster basin view) vs "My Organization Only".
  - View real-time civilian and shelter relief demand requests.
  - Execute concurrency-safe supply dispatch (allocates stock and decrements inventory with database locking).
- **Backend APIs:**
  - `GET /api/v1/resources`
  - `GET /api/v1/resources/requests`
  - `POST /api/v1/resources/{id}/dispatch`
  - `POST /api/v1/resources`
- **Database Entities:** `ngo_profiles`, `resources`, `resource_requests`, `donations`.
- **Business Rules & Restrictions:**
  - Concurrency safety: Dispatches use `SELECT ... FOR UPDATE` row-level locks to prevent stock overselling under simultaneous requests.
  - Cannot pledge capital infrastructure funding (statutory notice displayed; financial projects belong to municipal authorities).
  - Prohibited from modifying government engineering certifications or running CP-SAT solvers.
- **Relevant Components & Services:**
  - Frontend: `NGODashboard.tsx`.
  - Backend: `ResourceService`.

---

### 1.4 Persona 4: GOVT (Government Command & Municipal Engineers)

- **Primary Mission:** Tactical disaster command, engineering damage certification, infrastructure precedence analysis, and community recovery simulation.
- **Dashboard & Pages:**
  - `/admin`: Multi-Tab Government Command Center (Incidents, Infrastructure Precedence, Damage Certification).
  - `/admin/simulation`: Recovery Simulation Workbench (Ward Indicators, Vulnerability Rescoring, What-If Engine).
- **Available Actions:**
  - Triage incoming civilian incident reports; verify or reject reports; dispatch volunteer rescue missions.
  - Review incoming field damage inspections in the Engineering Certification Gate; certify damage levels (`MINIMAL`, `MODERATE`, `SEVERE`, `TOTAL_COLLAPSE`) with mandatory engineering rationale.
  - Inspect interactive SVG precedence DAG of civil reconstruction projects; toggle critical-path highlighting.
  - Execute zero-write Dry-Run Dependency Link Validator to test candidate precedence edges for circular cycles.
  - Track ward-level community recovery indicators; execute vulnerability rescoring ($\phi$); run What-If forward recovery simulations.
- **Backend APIs:**
  - `GET /api/v1/incidents`
  - `POST /api/v1/incidents/{id}/verify`
  - `GET /api/v1/recovery/assessments`
  - `POST /api/v1/recovery/damage-assessments/{id}/verify`
  - `GET /api/v1/recovery/dependencies/graph`
  - `POST /api/v1/recovery/dependencies/validate-edge`
  - `GET /api/v1/recovery/monitoring/community-metrics/summary`
  - `POST /api/v1/recovery/monitoring/vulnerability-rescore`
  - `POST /api/v1/recovery/simulation/what-if`
- **Database Entities:** `incidents`, `recovery_assessments`, `recovery_override_logs`, `recovery_projects`, `project_dependencies`, `community_recovery_metrics`, `simulation_runs`.
- **Business Rules & Restrictions:**
  - Only authorized `GOVT` or `ADMIN` roles can access `/admin` or `/admin/simulation`.
  - Damage verification commits an immutable audit entry into `recovery_override_logs`.
  - Precedence dry-run validator is strictly non-mutating (zero database writes).
- **Relevant Components & Services:**
  - Frontend: `CommandCenter.tsx`, `PrecedenceGraphVisualizer.tsx`, `RecoverySimulationWorkbench.tsx`, `DisasterSimulationView.tsx`.
  - Backend: `IncidentService`, `DamageAssessmentService`, `ProjectDependencyService`, `CommunityMonitoringService`, `RecoverySimulationService`.

---

### 1.5 Persona 5: ADMIN (Super-Administrator / Recovery Optimization Planner)

- **Primary Mission:** High-level system governance and mathematical portfolio optimization.
- **Dashboard & Pages:**
  - `/admin/recovery-optimization`: Google OR-Tools CP-SAT Optimization Workbench.
  - Full access to all `/admin` Command Center and `/admin/simulation` features.
- **Available Actions:**
  - Configure multi-period planning horizons ($1 \le T \le 120$).
  - Configure periodic monetary budgets in INR (with exact cent summation) and periodic CCU resource limits.
  - Add, edit, partition, and delete candidate recovery projects.
  - Dispatch synchronous CP-SAT integer optimization solver with modal indeterminate execution stopwatch.
  - Inspect scheduled projects on a 1-based periodic Gantt timeline.
  - Verify authoritative dual-ledger solvency matrix (INR currency cash balance strings vs CCU integer balances).
  - Inspect 4-tier Infeasibility Diagnostic Core and Assumption Cores on unschedulable scenarios.
- **Backend APIs:**
  - `POST /api/v1/recovery/optimization/evaluate`
  - `GET /api/v1/recovery/optimization/templates`
- **Database Entities:** `optimization_runs`, `optimization_recommendations`, `optimization_override_logs`, `recovery_projects`.
- **Business Rules & Restrictions:**
  - Only `ADMIN` and `GOVT` roles can access the recovery optimization console.
  - Solver evaluation is stateless: does not mutate project database records unless explicitly applied.
  - If post-solve solvency check fails, the schedule is suppressed with status `POST_SOLVE_RECONCILIATION_FAILED`.
- **Relevant Components & Services:**
  - Frontend: `RecoveryOptimizationView.tsx`, `SolverControlBar.tsx`, `ProjectScheduleTimeline.tsx`, `FinancialSolvencyMatrix.tsx`, `InfeasibilityDiagnosticsView.tsx`.
  - Backend: `RecoveryCPSatSolver`, `RecoveryOptimizationService`, `SolvencyService`.

---

## 2. Comprehensive Cross-Layer Feature Matrix

| Module | Role | Feature Description | Frontend Component | API Endpoint | Backend Service | Database Entity | Verification Status |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **Auth** | ALL | JWT Login with Bearer Tokens | `Login.tsx` | `POST /auth/login` | `auth.py`, `security.py` | `users` | **IMPLEMENTED** |
| **Auth** | ALL | Role-Based Access Guards | `App.tsx` | Route Interceptor | `deps.py` (`require_role`) | `users` | **IMPLEMENTED** |
| **Auth** | ALL | HTTP 401 Auto-Logout & Session Cleanup | Axios Interceptor | Any Guarded Endpoint | `get_current_user` | `users` | **IMPLEMENTED** |
| **Citizen** | CITIZEN | Public Incident Reporting Form | `ReportIncident.tsx` | `POST /incidents` | `incident_service.py` | `incidents` | **IMPLEMENTED** |
| **Citizen** | CITIZEN | One-Touch SOS Emergency Beacon | `CitizenDashboard.tsx` | `POST /incidents/sos` | `incident_service.py` | `incidents`, `alerts` | **IMPLEMENTED** |
| **Citizen** | CITIZEN | Local-First Offline Incident Drafts | `useOfflineDrafts.ts` | IndexedDB (Client) | `offlineDraftStore.ts` | `dirs_offline_drafts` | **IMPLEMENTED** |
| **Citizen** | CITIZEN | Web Crypto AES-256-GCM Vault | `cryptoVault.ts` | Browser Crypto API | `offlineDraftStore.ts` | `dirs_offline_drafts` | **IMPLEMENTED** |
| **Citizen** | CITIZEN | Offline Sync Manager Drawer | `DraftSyncManager.tsx` | `POST /incidents` | `useOfflineDrafts.ts` | `dirs_offline_drafts` | **IMPLEMENTED** |
| **Citizen** | CITIZEN | Geospatial Shelter Finder | `ShelterFinder.tsx` | `GET /shelters/nearby` | `shelter_service.py` | `shelters` | **IMPLEMENTED** |
| **Citizen** | CITIZEN | Grounded RAG Emergency Assistant | `CitizenDashboard.tsx` | `POST /ai/rag/query` | `rag/service.py` | `knowledge_chunks` | **IMPLEMENTED** |
| **Volunteer** | VOLUNTEER | Assigned Rescue Mission Queue | `VolunteerDashboard.tsx` | `GET /volunteers/my-tasks`| `volunteer_service.py` | `rescue_tasks` | **IMPLEMENTED** |
| **Volunteer** | VOLUNTEER | Mission Pipeline Status Updates | `VolunteerDashboard.tsx` | `POST /volunteers/tasks/{id}/status`| `rescue_service.py` | `rescue_tasks` | **IMPLEMENTED** |
| **Volunteer** | VOLUNTEER | Field Damage Inspection Intake | `VolunteerFieldInspection.tsx`| `POST /recovery/.../field-inspection`| `damage_assessment_service.py`| `recovery_assessments`| **IMPLEMENTED** |
| **Volunteer** | VOLUNTEER | Offline Field Inspection Drafts | `useOfflineDrafts.ts` | IndexedDB (Client) | `offlineDraftStore.ts` | `dirs_offline_drafts` | **IMPLEMENTED** |
| **NGO** | NGO | Relief Depot Inventory Table | `NGODashboard.tsx` | `GET /resources` | `resource_service.py` | `resources` | **IMPLEMENTED** |
| **NGO** | NGO | Inventory Scope (All Hubs vs Org) | `NGODashboard.tsx` | `GET /resources` (Client filtered)| Frontend `owner_id` match | `resources` | **IMPLEMENTED** |
| **NGO** | NGO | Civilian Relief Demands Feed | `NGODashboard.tsx` | `GET /resources/requests` | `resource_service.py` | `resource_requests` | **IMPLEMENTED** |
| **NGO** | NGO | Concurrency-Safe Stock Dispatch | `NGODashboard.tsx` | `POST /resources/{id}/dispatch` | `resource_service.py` | `resources` | **IMPLEMENTED** |
| **Command** | GOVT | Live Emergency Incident Map Feed | `CommandCenter.tsx` | `GET /incidents` | `incident_service.py` | `incidents` | **IMPLEMENTED** |
| **Command** | GOVT | Incident Verification / Rejection | `CommandCenter.tsx` | `POST /incidents/{id}/verify`| `incident_service.py` | `incidents` | **IMPLEMENTED** |
| **Command** | GOVT | Multi-Sector Precedence DAG View | `PrecedenceGraphVisualizer.tsx`| `GET /recovery/dependencies/graph`| `project_dependency_service.py`| `project_dependencies`| **IMPLEMENTED** |
| **Command** | GOVT | Critical Path Highlighting (CPM-PL) | `PrecedenceGraphVisualizer.tsx`| `GET /recovery/dependencies/graph`| `project_dependency_service.py`| `project_dependencies`| **IMPLEMENTED** |
| **Command** | GOVT | Dry-Run Dependency Link Validator | `PrecedenceGraphVisualizer.tsx`| `POST /recovery/.../validate-edge`| `project_dependency_service.py`| None (Dry run) | **IMPLEMENTED** |
| **Command** | GOVT | Engineering Inspection Review Gate | `CommandCenter.tsx` | `GET /recovery/assessments` | `damage_assessment_service.py`| `recovery_assessments`| **IMPLEMENTED** |
| **Command** | GOVT | Statutory Damage Certification Modal| Certification Modal | `POST /recovery/.../{id}/verify` | `damage_assessment_service.py`| `recovery_override_logs`| **IMPLEMENTED** |
| **Simulation**| GOVT | Ward Recovery Indicators Dashboard | `DisasterSimulationView.tsx` | `GET /recovery/.../summary` | `community_monitoring_service.py`| `community_recovery_metrics`| **IMPLEMENTED** |
| **Simulation**| GOVT | Vulnerability Rescoring ($\phi$) | `RecoverySimulationWorkbench.tsx`| `POST /recovery/.../vulnerability-rescore`| `vulnerability_scoring_service.py`| `community_recovery_metrics`| **IMPLEMENTED** |
| **Simulation**| GOVT | What-If Forward Recovery Simulation | `RecoverySimulationWorkbench.tsx`| `POST /recovery/simulation/what-if`| `recovery_simulation_service.py`| None (Calculation)| **IMPLEMENTED** |
| **Optimization**| ADMIN | CP-SAT Multi-Period Solver Console | `RecoveryOptimizationView.tsx`| `POST /recovery/.../evaluate`| `recovery_cpsat_solver.py`| `optimization_runs` | **IMPLEMENTED** |
| **Optimization**| ADMIN | 1-Based Periodic Gantt Timeline | `ProjectScheduleTimeline.tsx` | Contract payload rendering | Frontend 1-based CSS grid | None (In-memory) | **IMPLEMENTED** |
| **Optimization**| ADMIN | Dual-Ledger Solvency Matrix | `FinancialSolvencyMatrix.tsx`| Contract payload rendering | `solvency_service.py` | None (In-memory) | **IMPLEMENTED** |
| **Optimization**| ADMIN | 4-Tier Infeasibility Diagnostics | `InfeasibilityDiagnosticsView.tsx`| Contract payload rendering | `infeasibility_service.py`| None (In-memory) | **IMPLEMENTED** |
| **NGO** | NGO | Capital Infrastructure Pledging | None | None | None | None | **DOCUMENTED ONLY** |
| **Backend** | SYS | Multi-Worker Distributed Idempotency| None | None | `idempotency.py` (Local only) | None | **PARTIAL** |
