# DIRS — Capstone Evidence Extraction: System Architecture Specification
## Module 03: Architectural Topologies, Domain Flows & Implementation Schematics

**Document Identifier:** `DIRS-CAPSTONE-EVIDENCE-03`  
**Classification:** OFFICIAL / ACADEMIC CAPSTONE EVIDENCE  
**Degree Programme:** Bachelor of Technology (B.Tech) in Computer Science & Engineering  
**Institution:** VIT-AP University, Andhra Pradesh, India  
**Target Release:** DIRS v6.0 (Enterprise Hardened)  
**Audit Status:** STRICT READ-ONLY FORENSIC EXTRACTION  
**Evidence Sources:** `backend/app/main.py`, `backend/app/routers/`, `frontend/src/App.tsx`, `frontend/src/utils/offlineDraftStore.ts`  

---

## 1. High-Level System Architecture

DIRS is structured into four cohesive architectural tiers: the **Field Edge & Client Layer**, the **Local-First Client Resilience Layer**, the **Backend Application Gateway & Domain Service Layer**, and the **Persistence & Discrete Optimization Layer**.

```mermaid
graph TD
    subgraph Client Tier [Field Edge & Client Personas]
        Cit[Citizen: SOS, Incident Reporting, Shelter Finder]
        Vol[Volunteer: Mission Execution, Field Damage Assessment]
        NGO[NGO: Inventory Hub, Supply Dispatch]
        Govt[Government: Live Command Center, Engineering Certification]
        Adm[Admin: CP-SAT Optimization Solver Console]
    end

    subgraph Client Resilience [Local-First Offline Resilience]
        IDB[(IndexedDB Local Draft Store)]
        Vault[Web Crypto AES-256-GCM Vault]
        SyncMgr[Offline Synchronization & Idempotency Manager]
        QueryCache[TanStack React Query Cache]
    end

    subgraph Backend Core [FastAPI Gateway & Service Layer]
        API[FastAPI Gateway: 85 REST Endpoints & WebSockets]
        MW[Security Middleware: CSP, CORS, Payload Limiter]
        IdemSvc[Idempotency Service: SHA-256 Fingerprinting]
        AuthSvc[JWT Authentication & RBAC Router Guards]
        IncSvc[Incident Triage & GIS Spatial Service]
        DamSvc[Damage Assessment & Certification Service]
        DepSvc[Project Dependency Service: Kahn DAG & CPM-PL]
        MonSvc[Community Recovery & Confidence Decay Engine]
        SimSvc[What-If Forward Simulation Workbench]
        OptSvc[Phase 6D-B Recovery Optimization Service]
    end

    subgraph Persistence Layer [Storage & Optimization]
        DB[(PostgreSQL / PostGIS: 40 Relational Tables)]
        CPSAT[Google OR-Tools CP-SAT Discrete Constraint Engine]
    end

    Cit --> IDB
    Vol --> IDB
    IDB <--> Vault
    IDB --> SyncMgr
    SyncMgr --> API
    Govt --> QueryCache
    Adm --> QueryCache
    QueryCache --> API

    API --> MW
    MW --> IdemSvc
    IdemSvc --> AuthSvc
    AuthSvc --> IncSvc
    AuthSvc --> DamSvc
    AuthSvc --> DepSvc
    AuthSvc --> MonSvc
    AuthSvc --> SimSvc
    AuthSvc --> OptSvc

    IncSvc --> DB
    DamSvc --> DB
    DepSvc --> DB
    MonSvc --> DB
    SimSvc --> DB
    OptSvc --> DB
    OptSvc <--> CPSAT
```

---

## 2. Frontend Application Architecture

The frontend is a single-page application (SPA) built with React 18, TypeScript, and Vite.

### 2.1 Component Structure & Module Hierarchy
- `src/App.tsx`: Central route table defining route guards and role-based redirects.
- `src/pages/`: Role-specific view components:
  - `citizen/`: `CitizenDashboard.tsx`, `ReportIncident.tsx`, `ShelterFinder.tsx`.
  - `volunteer/`: `VolunteerDashboard.tsx`, `VolunteerFieldInspection.tsx`.
  - `ngo/`: `NGODashboard.tsx`.
  - `admin/`: `CommandCenter.tsx`, `RecoveryOptimizationView.tsx`, `DisasterSimulationView.tsx`.
- `src/components/`: Reusable, modular presentation components:
  - `recovery/`: `SolverControlBar.tsx`, `SolverStatusBanner.tsx`, `OptimizationKPIStats.tsx`, `ProjectScheduleTimeline.tsx`, `FinancialSolvencyMatrix.tsx`, `InfeasibilityDiagnosticsView.tsx`, `IndeterminateSolverOverlay.tsx`, `PrecedenceGraphVisualizer.tsx`, `RecoverySimulationWorkbench.tsx`.
  - `layout/`: `Sidebar.tsx`, `Navbar.tsx`.
  - `common/`: `DraftSyncManager.tsx`, `OfflineBanner.tsx`.
- `src/hooks/`: Custom stateful hooks:
  - `useOfflineDrafts.ts`: Local-first IndexedDB draft management, vault unlocking, background synchronization.
  - `useRecoveryOptimization.ts`: CP-SAT solver dispatch, indeterminate timer, solvency data caching.
  - `useNetworkStatus.ts`: Online/offline connectivity detection via `navigator.onLine` and window events.
- `src/utils/`:
  - `offlineDraftStore.ts`: Transactional IndexedDB access layer and session key manager.
  - `cryptoVault.ts`: W3C Web Crypto AES-256-GCM authenticated encryption engine.

---

## 3. Backend Architecture & Service Modularity

The backend is built with FastAPI, adhering strictly to a layered service-oriented architecture:

```
backend/
├── app/
│   ├── main.py                  # ASGI Application, Security Middleware, Lifespan/Startup
│   ├── config.py                # Pydantic v2 Settings with fail-closed security validators
│   ├── database.py              # SQLAlchemy engine, declarative Base, sessionmaker
│   ├── core/
│   │   ├── security.py          # BCrypt password hashing, JWT creation & decoding
│   │   ├── deps.py              # Dependency injection: get_db, get_current_user, require_role
│   │   ├── idempotency.py       # IdempotencyService with SHA-256 request fingerprinting
│   │   ├── logger.py            # Structured logging with sensitive data redaction filter
│   │   └── websocket_manager.py # Real-time event broadcasting (/ws/feed)
│   ├── models/                  # SQLAlchemy ORM relational models (40 tables)
│   ├── schemas/                 # Pydantic v2 data transfer objects (DTOs)
│   ├── routers/                 # Modular API endpoints (85 endpoints across 14 modules)
│   ├── services/                # Core business logic (incidents, volunteers, shelters, GIS)
│   └── recovery/                # Mathematical recovery domain sub-system
│       ├── optimization/        # Google OR-Tools CP-SAT solver implementation
│       ├── services/            # CPM-PL, Kahn DAG, vulnerability rescoring, simulation
│       └── schemas/             # Exact integer and currency string DTO contracts
```

---

## 4. Database Architecture & Schema Invariants

- **Total Tables:** Exactly **40 Relational Tables**.
- **Alembic Version Head:** `phase6b_recovery_foundation`.
- **Dialect Support:** PostgreSQL 16 with PostGIS 3.4 spatial extensions (production), SQLite (test fallback).
- **Core Entity Groups:**
  1. **Identity & RBAC:** `users`, `citizen_profiles`, `volunteer_profiles`, `ngo_profiles`, `audit_logs`.
  2. **Emergency Operations:** `incidents`, `incident_reports`, `incident_media`, `incident_clusters`, `alerts`, `shelters`, `road_blockages`, `rescue_tasks`.
  3. **Humanitarian Logistics:** `resources`, `resource_requests`, `donations`, `vehicles`, `resource_demand_predictions`.
  4. **Post-Disaster Recovery:** `recovery_assessments`, `recovery_needs`, `recovery_projects`, `project_dependencies`, `recovery_resources`, `recovery_override_logs`, `community_recovery_metrics`.
  5. **Optimization & Simulation:** `optimization_runs`, `optimization_recommendations`, `optimization_override_logs`, `simulation_scenarios`, `simulation_runs`.
  6. **AI & Knowledge:** `knowledge_documents`, `knowledge_chunks`, `rag_query_logs`, `cv_damage_assessments`, `ai_predictions`, `ai_recommendations`.

---

## 5. Domain Interaction Flows

### 5.1 Role-Based Route Authorization Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Router as React Router & Route Guards
    participant API as FastAPI Gateway
    participant Auth as Auth Middleware (deps.py)
    participant Service as Protected Service

    User->>Router: Navigate to Route (e.g. /admin/recovery-optimization)
    alt Unauthenticated
        Router-->>User: Redirect to /login
    else Authenticated
        Router->>Router: Check user.role in allowed_roles
        alt Role Unauthorized (e.g. CITIZEN navigating to /admin)
            Router-->>User: Deny Access / Redirect to Role Home
        else Role Authorized
            Router->>API: HTTP Request with Header (Authorization: Bearer <JWT>)
            API->>Auth: Extract JWT & Validate Signature (HS256)
            Auth->>Auth: Verify Token Expiration & Role Claims
            alt Token Invalid or Expired
                Auth-->>User: HTTP 401 Unauthorized (Auto-Logout)
            else Insufficient Role Permissions
                Auth-->>User: HTTP 403 Forbidden
            else Verification Succeeded
                Auth->>Service: Dispatch Request with Current Principal
                Service-->>User: Return HTTP 200/201 JSON Payload
            end
        end
    end
```

### 5.2 Incident Lifecycle & Emergency Response Flow

```mermaid
sequenceDiagram
    autonumber
    actor Citizen
    actor Volunteer
    actor Govt as Government Command
    participant Client as Local Draft Store / React UI
    participant Backend as FastAPI & IncidentService
    participant WS as WebSocket Feed (/ws/feed)
    participant DB as PostgreSQL Database

    Citizen->>Client: Submit Incident / SOS Distress
    alt Network Disconnected
        Client->>Client: Seal Draft with AES-256-GCM & Save to IndexedDB
    else Network Connected
        Client->>Backend: POST /api/v1/incidents (with Idempotency-Key)
        Backend->>Backend: Check Idempotency Cache (Prevent Duplicate)
        Backend->>DB: Insert Incident Record (Status: REPORTED)
        Backend->>WS: Broadcast INCIDENT_CREATED Event
        WS-->>Govt: Real-Time Incident Marker Rendered on Map
        Backend-->>Citizen: HTTP 201 Created (Incident UUID & Code)
    end

    Govt->>Backend: POST /api/v1/incidents/{id}/verify (Action: VERIFY)
    Backend->>DB: Update Incident Status -> VERIFIED
    Backend->>DB: Auto-Generate Rescue Task in rescue_tasks
    Backend->>WS: Broadcast TASK_CREATED Event
    WS-->>Volunteer: Mission Appears on Volunteer Task Queue

    Volunteer->>Backend: POST /api/v1/volunteers/tasks/{id}/status (ASSIGNED -> IN_PROGRESS)
    Volunteer->>Backend: POST /api/v1/recovery/damage-assessments/field-inspection
    Backend->>DB: Insert recovery_assessments (Status: PENDING_VERIFICATION)
    Backend->>WS: Broadcast ASSESSMENT_SUBMITTED Event
    WS-->>Govt: Flagged for Engineering Review

    Govt->>Backend: POST /api/v1/recovery/damage-assessments/{id}/verify (Decision: VERIFIED)
    Backend->>DB: Commit Certified Damage Level & Update Ward Recovery Metrics
```

### 5.3 Offline Draft Synchronization & Replay Flow

```mermaid
sequenceDiagram
    autonumber
    actor FieldUser as Field Worker
    participant IDB as Browser IndexedDB
    participant Vault as Web Crypto Vault
    participant Sync as DraftSyncManager Hook
    participant API as Backend REST API

    FieldUser->>Sync: Fill Form & Save Offline Draft
    Sync->>Vault: encryptDraftPayload(payload, sessionKey)
    Vault-->>Sync: Return DIRS_VAULT_V2 Ciphertext Envelope
    Sync->>IDB: store.put(draft) [Status: DRAFT]
    Note over IDB: Data safely persisted at rest

    FieldUser->>Sync: Device Regains Connectivity -> Trigger Sync
    Sync->>IDB: Read Draft & Update Status -> SYNCING
    Sync->>Vault: decryptDraftPayload(envelope, sessionKey)
    Vault-->>Sync: Plain JSON Payload
    Sync->>API: POST /api/v1/... (Header: Idempotency-Key: draft.client_draft_id)
    
    alt Server Accepts Request
        API-->>Sync: HTTP 201 Created { id: "server-uuid-123" }
        Sync->>IDB: Update Status -> SYNCED, Record server_acknowledged_id
    else Network Drops During Transit
        Sync->>IDB: Update Status -> FAILED, Preserve Draft Intact
    else Duplicate Retry Attempted
        API-->>Sync: HTTP 200 Replay (Identical Server Record)
        Sync->>IDB: Update Status -> SYNCED
    end
```

### 5.4 Recovery Portfolio Optimization & Solvency Flow

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Optimization Administrator
    participant UI as RecoveryOptimizationView
    participant Client as Axios API Client (130s Timeout)
    participant OptAPI as Recovery Optimization Router
    participant Solver as OR-Tools CP-SAT Solver
    participant Solvency as Solvency Service

    Admin->>UI: Configure Scenario (Horizon T, Budgets INR, CCU Capacities)
    UI->>UI: Client-Side Boundary Validation (1 <= T <= 120, positive budgets)
    Admin->>UI: Click "Evaluate Recovery Portfolio"
    UI->>UI: Display Indeterminate Stopwatch Overlay (Controls Locked)
    UI->>Client: Dispatch POST /api/v1/recovery/optimization/evaluate
    Client->>OptAPI: Transmit Scenario Payload
    
    OptAPI->>OptAPI: Pre-Solve Validation (Acyclicity, Solvency Feasibility)
    OptAPI->>Solver: Build CP-SAT Model (Decision variables, constraints)
    Note over Solver: Branch-and-Bound Integer Search
    Solver-->>OptAPI: Solver Termination (OPTIMAL / FEASIBLE / INFEASIBLE)

    alt Solution Found
        OptAPI->>Solvency: Authoritative Post-Solve Solvency Check
        Solvency->>Solvency: Verify Dual-Ledger Non-Negative Balances
        alt Solvency Check Passes
            OptAPI-->>Client: HTTP 200 JSON (Status: OPTIMAL, Exact Schedule, Solvency Matrix)
            Client-->>UI: Render 1-Based Periodic Gantt Chart & KPI Cards
        else Solvency Failed
            OptAPI-->>Client: HTTP 200 JSON (Status: POST_SOLVE_RECONCILIATION_FAILED)
            Client-->>UI: Suppress Schedule & Render Red Rejection Diagnostic
        end
    else Infeasible Scenario
        OptAPI->>OptAPI: Extract 4-Tier Infeasibility Diagnostic Core
        OptAPI-->>Client: HTTP 200 JSON (Status: INFEASIBLE, Diagnostic Findings)
        Client-->>UI: Render Diagnostic Findings Drawer (Zero Hallucinated Causes)
    end
```
