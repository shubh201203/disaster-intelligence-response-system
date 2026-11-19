# DIRS Phase 6G Accelerated Programme: Work Package 3
# Cross-Role UI Integration Architecture & Runtime Specification

**Document Identifier:** `DIRS-PH6G-WP3-APP-INTEGRATION-001`  
**Security Classification:** OFFICIAL / SENSITIVE  
**Target Release:** DIRS v5.2 (Accelerated Programme WP3)  
**Parent Roadmap Phase:** Phase 6G — Cross-Role UI Integration, E2E Verification & Capstone Forensic Closure  
**Status:** Certified / Completed  

---

## 1. Executive Summary & Purpose

Work Package 3 (WP3) delivers an integrated, role-aware user experience across the Disaster Intelligence and Response System (DIRS). Prior to WP3, recovery intelligence capabilities (such as CPM-PL precedence visualizers from WP1 and Community Monitoring & What-If Simulation from WP2) operated alongside tactical disaster response features without cross-role coherence or offline resilience.

WP3 binds five distinct operational user personas—**Citizens**, **Volunteers**, **NGO Coordinators**, **Government Officers (GOVT)**, and **System Administrators (ADMIN)**—into a unified workflow engine. It establishes client-side offline draft handling via native browser IndexedDB, ensures strict least-privilege boundary enforcement, and provides clear institutional demarcations for multi-agency relief logistics.

---

## 2. Integrated Application Architecture

```mermaid
flowchart TD
    subgraph Client [Browser Runtime - React 18 SPA]
        Router[React Router v6 Protected Routes]
        AuthCtx[Auth Context & JWT Bearer Storage]
        NetworkHook[useNetworkStatus Hook]
        DraftEngine[useOfflineDrafts Hook]
        
        subgraph RolePortals [Persona Portals]
            CitPortal[Citizen Portal\n/citizen, /citizen/report]
            VolPortal[Volunteer Hub\n/volunteer]
            NgoPortal[NGO Supply Hub\n/ngo]
            GovtPortal[Command Center & Optimization\n/admin, /admin/simulation, /admin/recovery-optimization]
        end

        subgraph LocalStorageEngine [Browser Persistence Engine]
            IDB[Native IndexedDB Store\n'dirs_offline_db' / 'dirs_offline_drafts']
            QueueMgr[DraftSyncManager UI & Conflict Inspector]
            Banner[OfflineBanner & Reconnection Monitor]
        end
    end

    subgraph BackendAPI [FastAPI Backend Engine]
        AuthRouter[/api/v1/auth]
        IncidentRouter[/api/v1/incidents]
        RecoveryRouter[/api/v1/recovery]
        ResourceRouter[/api/v1/resources]
        AnalyticsRouter[/api/v1/analytics]
    end

    Router --> AuthCtx
    AuthCtx --> RolePortals
    NetworkHook --> Banner
    DraftEngine --> IDB
    DraftEngine --> QueueMgr
    QueueMgr --> BackendAPI
    RolePortals --> BackendAPI
```

---

## 3. Persona Integration Specifications

### 3.1 Citizen Portal (`/citizen`, `/citizen/report`, `/citizen/shelters`)
* **Role Identifier:** `CITIZEN`
* **Operational Scope:** Public disaster intake, emergency distress triggering, nearby shelter location, and essential community recovery status awareness.
* **Component Integrations:**
  * `CitizenDashboard.tsx`: Displays high-priority SOS emergency dispatch, public shelter search grid, real-time emergency hotlines, and the **Municipal Recovery & Essential Services Status Card** querying `/api/v1/recovery/monitoring/community-metrics/summary`. This allows citizens to view citywide restoration indicators (Power Grid, Potable Water, Healthcare Facilities, Schools/Safe Centers) across monitored wards.
  * `ReportIncident.tsx`: Embedded with `useOfflineDrafts('INCIDENT_REPORT')`, `OfflineBanner`, and `DraftSyncManager`. Enables citizens in low-connectivity disaster areas to record field incident reports locally. When disconnected, form submission automatically persists drafts into IndexedDB, with immediate retry capability upon reconnection.

### 3.2 Volunteer Responder Hub (`/volunteer`)
* **Role Identifier:** `VOLUNTEER`
* **Operational Scope:** Tactical field task acceptance, survivor extraction pipelines, and rapid infrastructure damage inspection.
* **Component Integrations:**
  * `VolunteerDashboard.tsx`: Features a tabbed interface toggling between "Tactical Rescue Missions" and "Field Damage Inspection".
  * `VolunteerFieldInspection.tsx`: Embedded component enabling certified field volunteers to submit damage assessments (`DamageAssessmentFieldCreate`) referencing target incidents. Captures facility name, sector classification, damage rating (NONE, MINOR, MODERATE, SEVERE, DESTROYED), operational state, structural integrity notes, and GPS coordinates.
  * **Offline Resilience:** Embedded with `useOfflineDrafts('FIELD_INSPECTION')`. Field volunteers in signal-compromised disaster zones can record multiple structural damage assessments without connectivity; drafts queue in IndexedDB and synchronize to `/api/v1/recovery/damage-assessments/field-inspection` upon returning to network coverage.
  * **Verification Boundary:** Assessments submitted by volunteers enter `PENDING_VERIFICATION` status. Volunteers are strictly blocked from self-verifying; statutory engineering certification remains restricted to `GOVT` engineers.

### 3.3 NGO Relief & Dispatch Hub (`/ngo`)
* **Role Identifier:** `NGO`
* **Operational Scope:** Humanitarian commodity warehousing, relief dispatch to impacted clusters, and field demand fulfillment.
* **Component Integrations:**
  * `NGODashboard.tsx`: Features organization profile recognition (`org_name`, `registration_no`, authorized representative, verified partner badge).
  * **Inventory Scoping Toggle:** Interactive toggle allowing NGO coordinators to switch between "All Hubs" (comprehensive multi-agency situational visibility) and "My Org Only" (filtering inventory to depot stocks owned directly by the logged-in NGO).
  * **Field Relief Demands:** Live feed querying `GET /api/v1/resources/requests` with incident title joins, allowing NGOs to identify real-time humanitarian supply deficits (food, water, medicine, shelter tarpaulins) submitted by citizens or responders.
  * **Institutional Governance Policy:** Formal notice demarcating that capital project pledges and structural restoration are governed by statutory financial sanctions; NGOs participate through commodity aid and framework partnerships without unbacked database string substitutions.

### 3.4 Government Command Center (`/admin`, `/admin/simulation`, `/admin/recovery-optimization`)
* **Role Identifier:** `GOVT` (Super-role) and `ADMIN`
* **Operational Scope:** Executive situational command, multi-sector damage certification, mathematical recovery portfolio optimization (MILP/CP-SAT), and CPM-PL precedence network orchestration.
* **Component Integrations:**
  * `CommandCenter.tsx`: Three-tab operational command interface:
    1. *Live Emergency Operations:* Incident map, priority queue, shelter status, and resource allocation.
    2. *Infrastructure Precedence (CPM-PL):* Interactive DAG visualizer, critical path highlighting, and dependency cycle validation.
    3. *Field Inspections Verification Pipeline:* Interactive verification table querying `/api/v1/recovery/assessments`. Displays volunteer assessments awaiting certification. Authorized government engineers review field notes and open the Engineering Certification Modal to execute statutory approval (`POST /recovery/damage-assessments/{id}/verify`) with actions (`VERIFY`, `DISPUTE`, `REJECT`), certified damage levels, and required engineering rationale.

---

## 4. Cross-Role Navigation & Least-Privilege Route Guards

All application routes are protected by `ProtectedRoute` in `frontend/src/App.tsx`, enforcing least privilege based on authenticated JWT tokens:

| Route | Authorized Roles | Unauthorized Behavior |
| :--- | :--- | :--- |
| `/citizen` | `CITIZEN`, `GOVT` | Redirects to `/login` if unauthenticated, or fallback based on role |
| `/citizen/report` | `CITIZEN`, `VOLUNTEER`, `GOVT` | Redirects to fallback portal |
| `/citizen/shelters` | `CITIZEN`, `VOLUNTEER`, `NGO`, `GOVT`, `ADMIN` | Open to all authenticated principals |
| `/volunteer` | `VOLUNTEER`, `GOVT` | Citizens/NGOs redirected to home portal |
| `/ngo` | `NGO`, `GOVT` | Citizens/Volunteers redirected to home portal |
| `/admin` | `GOVT` | Citizens/Volunteers/NGOs redirected to `/citizen`; ADMIN redirected to `/admin/recovery-optimization` |
| `/admin/simulation` | `GOVT` | Strictly restricted to government executive command |
| `/admin/recovery-optimization` | `GOVT`, `ADMIN` | Super-access for mathematical optimization solver |

---

## 5. Architectural Verification & Zero-Drift Integrity

1. **Gate 2 Baseline Preservation:** All 23 Gate 2 baseline files and `task.md` remain 100% frozen.
2. **Schema & Migration Head:** Database migrations remain locked at `phase6b_recovery_foundation` across exactly 40 tables. Zero schema modifications or Alembic migrations were introduced.
3. **Solver Mathematics:** The CP-SAT and MILP recovery optimization solvers remain unaltered.
4. **Build Invariant:** Production build (`npm run build`) compiles cleanly without TypeScript or Vite errors.
