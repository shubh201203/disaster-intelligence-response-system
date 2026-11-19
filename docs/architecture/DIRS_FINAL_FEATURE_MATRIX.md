# DIRS — Definitive Final Feature Matrix
## Disaster Intelligence and Response System (DIRS)

**Document Identifier:** `DIRS-CAPSTONE-MATRIX-002`  
**Classification:** OFFICIAL / OPERATIONAL AUDIT  
**Target Release:** DIRS v5.2 (Capstone Release)  
**Parent Programme:** Phase 6G / Accelerated Work Package 4 (Capstone Packaging & Verification)  
**Publication Date:** November 18, 2026  
**Status:** Certified / Complete  

---

## 1. Feature Classification Taxonomy

Each capability in this matrix is classified based on forensic cross-layer tracing:
$$\text{UI Component} \longrightarrow \text{API Route} \longrightarrow \text{Backend Service} \longrightarrow \text{Data Model} \longrightarrow \text{Automated Tests}$$

* **`VERIFIED OPERATIONAL`:** Fully implemented, end-to-end traceable, directly executed in test suites with exit code 0 during WP4.
* **`VERIFIED PARTIAL`:** Functionally operational for core workflows, but specific sub-features depend on manual data preparation or operational configuration.
* **`DOCUMENTED ONLY`:** Mentioned in specifications or roadmap, but lacks underlying database schema or executable code.
* **`UNSUPPORTED`:** Formally out of scope (e.g. Phase 7, external cloud services, arbitrary database string hacks).

---

## 2. Complete Cross-Layer Feature Matrix

| Module | Role | Feature Description | UI Component | API Endpoint | Backend Service | Database Entity | Test Reference | Forensic Status |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **Auth** | ALL | JWT Login with Bearer Tokens | `Login.tsx` | `POST /auth/login` | `auth.py`, `security.py` | `users` | `test_auth.py`, `TC-E2E-02` | **VERIFIED OPERATIONAL** |
| **Auth** | ALL | User Registration & Role Selection | `Register.tsx` | `POST /auth/register` | `auth.py` | `users`, `*_profiles` | `test_auth.py` | **VERIFIED OPERATIONAL** |
| **Auth** | ALL | Session Expiry Auto-Logout | Axios Interceptor | Any guarded endpoint | `get_current_user` | `users` | `TC-E2E-29`, `crossRoleOffline.spec.ts` | **VERIFIED OPERATIONAL** |
| **Auth** | ALL | Multi-User Cache Partitioning | Dashboards | Cache query keys | Query Key scoping | Memory / IndexedDB | `crossRoleOffline.spec.ts` | **VERIFIED OPERATIONAL** |
| **Citizen** | CITIZEN | Public Incident Reporting Form | `ReportIncident.tsx` | `POST /incidents` | `incident_service.py` | `incidents`, `incident_reports` | `test_incidents.py`, `crossRoleOffline.spec.ts` | **VERIFIED OPERATIONAL** |
| **Citizen** | CITIZEN | Emergency SOS Distress Signal | `CitizenDashboard.tsx` | `POST /incidents/sos` | `incident_service.py` | `incidents`, `alerts` | `test_sos.py` | **VERIFIED OPERATIONAL** |
| **Citizen** | CITIZEN | Offline Incident Draft Persistence | `useOfflineDrafts.ts` | IndexedDB (Client) | `offlineDraftStore.ts` | `dirs_offline_drafts` | `TC-WP3-E2E-01`, `crossRoleOffline.spec.ts` | **VERIFIED OPERATIONAL** |
| **Citizen** | CITIZEN | Offline Draft Sync Queue Manager | `DraftSyncManager.tsx` | `POST /incidents` | `useOfflineDrafts.ts` | `dirs_offline_drafts` | `TC-WP3-E2E-01`, `crossRoleOffline.spec.ts` | **VERIFIED OPERATIONAL** |
| **Citizen** | CITIZEN | Shelter Finder & Geospatial Query | `ShelterFinder.tsx` | `GET /shelters/nearby` | `shelter_service.py` | `shelters` | `test_shelters.py`, `test_gis.py` | **VERIFIED OPERATIONAL** |
| **Citizen** | CITIZEN | Municipal Recovery Status Indicator | `CitizenDashboard.tsx` | `GET /recovery/monitoring/community-metrics/summary` | `community_monitoring_service.py` | `community_recovery_metrics` | `TC-WP3-E2E-02`, `communityMonitoring.spec.ts` | **VERIFIED OPERATIONAL** |
| **Citizen** | CITIZEN | Grounded RAG Emergency Assistant | `CitizenDashboard.tsx` | `POST /ai/rag/query` | `rag/service.py` | `knowledge_chunks` | `test_phase3c_rag.py` | **VERIFIED OPERATIONAL** |
| **Volunteer** | VOLUNTEER | Assigned Mission Task Queue | `VolunteerDashboard.tsx` | `GET /volunteers/my-tasks` | `volunteer_service.py` | `rescue_tasks` | `test_volunteers.py` | **VERIFIED OPERATIONAL** |
| **Volunteer** | VOLUNTEER | Mission Pipeline State Updates | `VolunteerDashboard.tsx` | `POST /volunteers/tasks/{id}/status` | `rescue_service.py` | `rescue_tasks` | `test_volunteers.py` | **VERIFIED OPERATIONAL** |
| **Volunteer** | VOLUNTEER | Field Damage Inspection Intake | `VolunteerFieldInspection.tsx` | `POST /recovery/damage-assessments/field-inspection` | `damage_assessment_service.py` | `recovery_assessments` | `TC-WP3-E2E-03`, `crossRoleOffline.spec.ts` | **VERIFIED OPERATIONAL** |
| **Volunteer** | VOLUNTEER | Offline Field Inspection Drafts | `useOfflineDrafts.ts` | IndexedDB (Client) | `offlineDraftStore.ts` | `dirs_offline_drafts` | `TC-WP3-E2E-03`, `crossRoleOffline.spec.ts` | **VERIFIED OPERATIONAL** |
| **Volunteer** | VOLUNTEER | Self-Task-Assignment Denial Guard | `VolunteerDashboard.tsx` | Route / API Guards | `require_role("GOVT")` | `rescue_tasks` | `test_phase6g_wp3_cross_role_offline.py` | **VERIFIED OPERATIONAL** |
| **NGO** | NGO | Humanitarian Inventory Depot View | `NGODashboard.tsx` | `GET /resources` | `resource_service.py` | `resources` | `test_resources.py`, `TC-WP3-E2E-04` | **VERIFIED OPERATIONAL** |
| **NGO** | NGO | Inventory Scoping (All Hubs vs My Org) | `NGODashboard.tsx` | `GET /resources` (Client filtered) | Frontend filtering on `owner_id` | `resources` | `TC-WP3-E2E-04`, `crossRoleOffline.spec.ts` | **VERIFIED OPERATIONAL** |
| **NGO** | NGO | Field Relief Demands Feed | `NGODashboard.tsx` | `GET /resources/requests` | `resource_service.py` | `resource_requests` | `TC-WP3-E2E-04`, `crossRoleOffline.spec.ts` | **VERIFIED OPERATIONAL** |
| **NGO** | NGO | Concurrency-Safe Stock Dispatch | `NGODashboard.tsx` | `POST /resources/{id}/dispatch` | `resource_service.py` (`with_for_update`) | `resources` | `test_resources.py` | **VERIFIED OPERATIONAL** |
| **NGO** | NGO | Capital Infrastructure Pledging | None (Prohibited) | None (Out of Scope) | Statutory Institutional Notice | None (No `ngo_pledges` table) | `PHASE6G_WP3_ROLE_FEATURE_MATRIX.md` | **UNSUPPORTED** |
| **Command** | GOVT | Live Emergency Incident Feed | `CommandCenter.tsx` | `GET /incidents` | `incident_service.py` | `incidents` | `test_incidents.py` | **VERIFIED OPERATIONAL** |
| **Command** | GOVT | Multi-Sector Precedence DAG View | `PrecedenceGraphVisualizer.tsx` | `GET /recovery/dependencies/graph` | `project_dependency_service.py` | `recovery_projects`, `project_dependencies` | `TC-WP1-01`, `test_phase6e_wp1_precedence_graph.py` | **VERIFIED OPERATIONAL** |
| **Command** | GOVT | CPM-PL Critical Path Highlighting | `PrecedenceGraphVisualizer.tsx` | `GET /recovery/dependencies/graph` | `project_dependency_service.py` | `project_dependencies` | `TC-WP1-02`, `TC-WP1-03` | **VERIFIED OPERATIONAL** |
| **Command** | GOVT | Dry-Run Dependency Link Validator | `PrecedenceGraphVisualizer.tsx` | `POST /recovery/dependencies/validate-edge` | `project_dependency_service.py` (Zero-write) | None (Dry run) | `TC-WP1-04`, `test_phase6e_wp1_precedence_graph.py` | **VERIFIED OPERATIONAL** |
| **Command** | GOVT | Engineering Inspection Review Gate | `CommandCenter.tsx` | `GET /recovery/assessments` | `damage_assessment_service.py` | `recovery_assessments` | `TC-WP3-E2E-05`, `crossRoleOffline.spec.ts` | **VERIFIED OPERATIONAL** |
| **Command** | GOVT | Statutory Damage Level Certification | Certification Modal | `POST /recovery/damage-assessments/{id}/verify` | `damage_assessment_service.py` | `recovery_assessments`, `recovery_override_logs` | `TC-WP3-E2E-05`, `test_phase6g_wp3_cross_role_offline.py` | **VERIFIED OPERATIONAL** |
| **Simulation** | GOVT | Community Indicator Aggregation | `DisasterSimulationView.tsx` | `GET /recovery/monitoring/community-metrics/summary` | `community_monitoring_service.py` | `community_recovery_metrics` | `TC-WP2-01`, `communityMonitoring.spec.ts` | **VERIFIED OPERATIONAL** |
| **Simulation** | GOVT | Vulnerability Rescoring ($\phi$) | `RecoverySimulationWorkbench.tsx` | `POST /recovery/monitoring/vulnerability-rescore` | `vulnerability_scoring_service.py` | `community_recovery_metrics` | `TC-WP2-03`, `test_phase6f_wp2_community_simulation.py` | **VERIFIED OPERATIONAL** |
| **Simulation** | GOVT | What-If Recovery Forward Simulation | `RecoverySimulationWorkbench.tsx` | `POST /recovery/simulation/what-if` | `recovery_simulation_service.py` | Read-only calculation | `TC-WP2-02`, `test_phase6f_wp2_community_simulation.py` | **VERIFIED OPERATIONAL** |
| **Optimization** | GOVT / ADMIN | CP-SAT Portfolio Optimization | `RecoveryOptimizationView.tsx` | `POST /recovery/optimization/evaluate` | `recovery_cpsat_solver.py` | `optimization_runs`, `recovery_projects` | `test_phase6d_cpsat_solver.py`, `TC-E2E-22` | **VERIFIED OPERATIONAL** |
| **Optimization** | GOVT / ADMIN | 1-Based Periodic Gantt Timeline | `ProjectScheduleTimeline.tsx` | Contract payload evaluation | Frontend 1-based column grid | In-memory evaluation | `TC-E2E-23`, `stage4Visualizations.spec.ts` | **VERIFIED OPERATIONAL** |
| **Optimization** | GOVT / ADMIN | Dual-Ledger Solvency Matrix | `FinancialSolvencyMatrix.tsx` | Dual dictionary balance | `cash_flow_solvency_service.py` | In-memory evaluation | `TC-E2E-25`, `stage4Visualizations.spec.ts` | **VERIFIED OPERATIONAL** |
| **Optimization** | GOVT / ADMIN | 4-Tier Infeasibility Diagnostics | `InfeasibilityDiagnosticsView.tsx` | Tier 1-4 diagnostic findings | `infeasibility_advisor.py` | `optimization_runs` | `TC-E2E-26`, `test_phase6d_cpsat_solver.py` | **VERIFIED OPERATIONAL** |
| **Optimization** | GOVT / ADMIN | Indeterminate Stopwatch Overlay | `IndeterminateSolverOverlay.tsx` | Dispatch interceptor | Frontend elapsed timer | In-memory evaluation | `TC-E2E-20`, `TC-E2E-21` | **VERIFIED OPERATIONAL** |
| **Enterprise** | ALL | Enterprise P2P / CRDT Sync | None | None | None | None | None | **UNSUPPORTED** (Phase 7) |
| **Enterprise** | ALL | Multi-Cloud Deployment & Helm | None | None | None | None | None | **UNSUPPORTED** (Phase 7) |
| **Enterprise** | ALL | Automated Hardware TEE Security | None | None | None | None | None | **UNSUPPORTED** (Phase 7) |
