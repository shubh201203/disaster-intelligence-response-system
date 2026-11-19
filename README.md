# Disaster Intelligence and Response System (DIRS)

> **Enterprise-Grade, Full-Stack Disaster Management Platform Integrating Machine Learning, Computer Vision, Geospatial Analytics, and Mathematical Recovery Optimization**

[![Python 3.11](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.2.0-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2.2-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL / PostGIS](https://img.shields.io/badge/PostgreSQL-PostGIS-336791?logo=postgresql&logoColor=white)](https://postgis.net/)
[![OR-Tools](https://img.shields.io/badge/Google_OR--Tools-CP--SAT_9.14-EA4335?logo=google&logoColor=white)](https://developers.google.com/optimization)
[![Tests Passing](https://img.shields.io/badge/Pytest-656_Passed-brightgreen)](file:///C:/Users/shubh/Downloads/DIRS/docs/testing/)
[![Academic Capstone](https://img.shields.io/badge/Academic-B.Tech_Capstone_VIT--AP-blue)](file:///C:/Users/shubh/Downloads/DIRS/docs/academic/)

---

## 1. Executive Summary & Abstract

The **Disaster Intelligence and Response System (DIRS)** is an end-to-end, role-aware decision-support ecosystem engineered for multi-agency disaster preparedness, tactical response, and post-disaster infrastructure recovery. 

Bridging the critical gap between affected citizens, on-ground volunteer rescue units, non-governmental relief organizations (NGOs), and government emergency operations centers, DIRS operationalizes a complete 10-stage disaster lifecycle:
$$\text{Detect} \longrightarrow \text{Report} \longrightarrow \text{Verify} \longrightarrow \text{Analyze} \longrightarrow \text{Prioritize} \longrightarrow \text{Allocate} \longrightarrow \text{Respond} \longrightarrow \text{Monitor} \longrightarrow \text{Recover} \longrightarrow \text{Learn}$$

### Core Capstone Innovations (VIT-AP University)
1. **Mathematical Recovery Portfolio Optimization:** Discrete project scheduling using **Google OR-Tools CP-SAT** with non-linear multi-period budget envelopes, material capacity ceilings, and dual financial / Community Care Unit (CCU) ledger reconciliation.
2. **Infrastructure Critical Path Intelligence:** Topological precedence analysis using **NetworkX** implementing the Critical Path Method with Path Length constraints (CPM-PL) and dry-run cycle detection.
3. **Dual-Framework Severity & Priority Engine:** Multi-factor damage scoring combining XGBoost ML models, rule-based heuristics, and OpenCV-based computer vision damage classification with explainable feature attributions ($+ \text{victims}$, $+ \text{infrastructure collapse}$, $+ \text{hazard proximity}$).
4. **Geospatial & Spatio-Temporal Intelligence:** PostgreSQL / PostGIS spatial indexing (`ST_DWithin`, KNN queries), dynamic hazard heatmaps, duplicate report clustering, and emergency shelter routing.
5. **Offline-First Zero-Knowledge Architecture:** Client-side draft resilience backed by **IndexedDB** and encrypted via the **WebCrypto API** using **AES-GCM-256** with multi-user hardware key isolation and server-side idempotency keys.
6. **Disaster Scenario Laboratory & Stress Testing:** Interactive simulation laboratory modeling Ward Vulnerability Indices (WVI), infrastructure cascades, and comparative stress curves under severe demand surges.

---

## 2. System Architecture

```text
+---------------------------------------------------------------------------------------------------+
|                                       DIRS CLIENT TIER                                            |
|  React 18 | TypeScript | Vite | Tailwind CSS | React-Leaflet | Lucide Icons | Recharts | WebCrypto|
+---------------------+-----------------------+----------------------+------------------------------+
|   Citizen Portal    |   Volunteer Portal    |      NGO Portal      |   Command Center (Govt)      |
|  - Incident Report  |  - Rescue Workflow    |  - Shelter Capacity  |  - Real-time GIS Heatmap     |
|  - Media Capture    |  - Incident Claim     |  - Relief Inventory  |  - Critical Path Graph       |
|  - Offline Vault    |  - Field Damage Assmt |  - Aid Distribution  |  - CP-SAT Recovery Optimizer |
|  - AI Safety Advice |  - Status Progression |  - Gap Analytics     |  - Scenario Stress Lab       |
+---------------------+-----------------------+----------------------+------------------------------+
                                          |
                                [ RESTful HTTPS & WebSockets ]
                                [ AES-GCM Auth & Idempotency ]
                                          v
+---------------------------------------------------------------------------------------------------+
|                                   FASTAPI APPLICATION LAYER                                       |
|  ASGI Uvicorn | Pydantic v2 | Starlette | SQLAlchemy 2.0 | Redis Client | Async Request Dispatch  |
+---------------------------------------------------------------------------------------------------+
| Security & Middleware  : JWT Authentication (HS256), RBAC Guard, Rate Limiter, Idempotency Filter  |
| Incident Orchestration : Spatio-temporal Clustering, Duplicate Detection, SOS Priority Queue      |
| Volunteer Coordination : Distributed Claim Lock, Stepwise State Machine, Verification Lifecycle   |
| Relief & Logistics     : Shelter Occupancy Matching, Resource Allocation, Need Calculation        |
+---------------------------------------------------------------------------------------------------+
       |                                   |                                   |
       v                                   v                                   v
+-----------------------+   +-------------------------------+   +-----------------------------------+
|  AI & ML SUBSYSTEMS   |   |   OR-TOOLS CP-SAT OPTIMIZER   |   |    INFRASTRUCTURE GRAPH ENGINE    |
| - XGBoost Severity    |   | - Multi-Period Budget Model   |   | - NetworkX Precedence Graph       |
| - OpenCV Damage CV    |   | - Resource Ceiling Knapsack   |   | - Critical Path Method (CPM-PL)   |
| - RAG SOP Safety Assmt|   | - CCU Solvency Reconciliation |   | - Cycle Detection & Transitive Red|
| - Vulnerability Index |   | - Deterministic Solvers       |   | - Cascade Damage Failure Analysis |
+-----------------------+   +-------------------------------+   +-----------------------------------+
                                          |
                                [ SQL / Spatial Query Engine ]
                                          v
+---------------------------------------------------------------------------------------------------+
|                                 DATA PERSISTENCE & CACHE LAYER                                    |
+--------------------------------------------------+------------------------------------------------+
|  PostgreSQL 15+ & PostGIS Extension              |  Redis In-Memory Cache                         |
|  - Spatial Indices (GIST / ST_DWithin / KNN)     |  - Distributed Atomic Idempotency Cache        |
|  - Dual Financial & Material Ledgers             |  - Real-Time WebSocket Pub/Sub Dispatch        |
|  - GeoAlchemy2 + SQLite Fallback Dialect         |  - Token Blacklist & Active Session State      |
+--------------------------------------------------+------------------------------------------------+
```

---

## 3. Four Role-Based Portals

| Role | Target Users | Key Workflows & Features |
| :--- | :--- | :--- |
| **Citizen** | General Public, Impacted Residents | One-click SOS emergency dispatch, multi-category incident reporting with direct photo evidence upload, offline draft storage with auto-sync upon reconnection, real-time rescue status tracking, and interactive AI-driven disaster safety advice. |
| **Volunteer** | Registered Volunteers, First Responders | Mutual-exclusion incident claiming, real-time rescue pipeline (`ASSIGNED` $\to$ `RESCUE_STARTED` $\to$ `RESCUED` $\to$ `CLOSED`), geo-located field damage inspection reporting, citizen safety verification, and offline field draft vault. |
| **NGO Coordinator** | Relief Agencies, Humanitarian Orgs | Real-time emergency shelter occupancy management, critical relief resource tracking (rations, drinking water, medical kits, blankets), gap analysis across affected wards, and donation distribution logging. |
| **Command Center** | Disaster Authorities, Municipal Admins | Multi-layer PostGIS GIS map with clustering, mathematical CP-SAT infrastructure recovery portfolio optimization, CPM-PL precedence network visualization, Monte Carlo scenario simulation laboratory, and Ward Vulnerability Index monitoring. |

---

## 4. Technology Stack

### Frontend Architecture
- **Framework:** React 18.2.0 with TypeScript 5.2.2 (Strict type checking)
- **Build Tool:** Vite 5.1.6
- **Styling:** Tailwind CSS 3.4.1 with `@tailwindcss/forms`
- **Mapping & GIS:** Leaflet 1.9.4 & React-Leaflet 4.2.1
- **State Management & Caching:** TanStack React Query v5
- **Charts & Analytics:** Recharts 2.12.3
- **Icons:** Lucide React
- **Offline Cryptography:** WebCrypto API (AES-GCM-256) + IndexedDB (`idb`)

### Backend Architecture
- **Runtime:** Python 3.11+
- **API Framework:** FastAPI 0.110.0 with ASGI Uvicorn
- **Data Validation & Settings:** Pydantic v2 (2.6.4) & Pydantic-Settings
- **ORM & Migrations:** SQLAlchemy 2.0.28 (Async/Sync) with Alembic 1.13.1
- **Spatial GIS:** GeoAlchemy2 0.14.7 with PostGIS spatial types (with automatic SQLite dialect fallback)
- **Optimization:** Google OR-Tools 9.14 (CP-SAT Constraint Programming Solver)
- **Graph Analytics:** NetworkX 3.3 (CPM-PL, topological sort, cycle detection)
- **Machine Learning & CV:** Scikit-learn 1.4, XGBoost 2.0, OpenCV 4.9, NumPy 1.26, SciPy 1.12
- **Caching & Messaging:** Redis 5.0.3 (Distributed locks, pub/sub, idempotency storage)
- **Security:** PyJWT / python-jose, Passlib with BCrypt hashing

---

## 5. Repository Layout

```text
DIRS/
├── backend/                        # FastAPI Backend Application
│   ├── alembic/                    # Database migration versions and env configuration
│   ├── app/
│   │   ├── ai/                     # ML Priority, XGBoost Risk, CV Classifier, RAG SOP
│   │   ├── api/v1/endpoints/       # Modular REST API endpoints by domain
│   │   ├── core/                   # Security, JWT, Redis, Idempotency, Middleware
│   │   ├── models/                 # SQLAlchemy ORM models (Incidents, Shelters, Recovery, etc.)
│   │   ├── schemas/                # Pydantic v2 request/response validation schemas
│   │   ├── services/               # Core business logic (CP-SAT, Recovery, Rescue, Monitoring)
│   │   ├── config.py               # Central environment and security configuration
│   │   └── database.py             # Database engine setup and session lifecycle
│   ├── backups/                    # Pre-phase database baseline backups
│   ├── static/uploads/             # Local media file uploads directory
│   ├── requirements.txt            # Python dependencies
│   └── alembic.ini                 # Alembic migration configuration
├── frontend/                       # React 18 + TypeScript Application
│   ├── src/
│   │   ├── components/             # Reusable UI components (Navbar, Modals, Forms, Map)
│   │   ├── context/                # Authentication context and role dispatchers
│   │   ├── pages/                  # Role-based views (Citizen, Volunteer, NGO, Command Center)
│   │   ├── services/               # API clients, offlineDraftStore, cryptoVault, syncEngine
│   │   ├── types/                  # TypeScript interface definitions and DTO contracts
│   │   ├── App.tsx                 # Application router and protected route boundaries
│   │   └── main.tsx                # React DOM entrypoint
│   ├── package.json                # Frontend dependencies and npm scripts
│   ├── tsconfig.json               # TypeScript compiler configuration
│   └── vite.config.ts              # Vite bundler configuration
├── data/                           # Standard datasets, Ward census boundaries, model weights
├── docs/                           # Comprehensive System Documentation
│   ├── academic/                   # Capstone reports, viva guides, and presentation packages
│   ├── api/                        # REST API catalog, contracts, and traceability matrices
│   ├── architecture/               # System architecture, database schema, and mathematical proofs
│   ├── evidence/                   # Independent audit reports, gate sign-offs, and verification logs
│   ├── screenshots/                # Visual asset capture guide and UI screenshots
│   └── testing/                    # Test plans, execution logs, and defect registers
├── infrastructure/                 # Docker Compose, Dockerfiles, and Nginx configurations
├── scripts/                        # Benchmarks, evaluation, model training, and database seeders
├── tests/                          # Automated Test Suites
│   ├── backend/                    # 656 pytest unit, integration, and mathematical solver tests
│   └── e2e/                        # Playwright end-to-end multi-role tests
├── .env.example                    # Template environment variables
├── .gitignore                      # Git ignore specifications
├── demo_dirs.db                    # Reference SQLite demo database
├── dirs_dev.db                     # Playwright/local testing SQLite database
├── docker-compose.yml              # Multi-container orchestration (PostGIS, Redis, API, Web)
├── playwright.config.ts            # E2E test configuration
└── README.md                       # Master project overview and documentation
```

---

## 6. Prerequisites & Installation

### System Requirements
- **Python:** 3.11 or higher
- **Node.js:** 18.x or 20.x LTS (with npm 9+)
- **Database:** PostgreSQL 15+ with PostGIS extension (or SQLite for rapid evaluation)
- **Cache:** Redis 6.0+ (optional for local SQLite development, required for multi-worker production)
- **OS:** Windows 10/11, macOS, or Ubuntu 22.04 LTS

---

## 7. Quick-Start Guide

### Option A: Local Native Setup (Recommended for Development)

#### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment variables
# Copy .env.example to .env and adjust DATABASE_URL if using PostgreSQL
cp .env.example .env

# Run database migrations (if using PostgreSQL)
alembic upgrade head

# Seed initial operational data (Chennai 5-Ward baseline)
python ../scripts/seed_operational_demo.py

# Launch the FastAPI backend server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend API will be available at:* `http://127.0.0.1:8000`  
*Interactive Swagger Documentation:* `http://127.0.0.1:8000/docs`

#### 2. Frontend Setup
```bash
# In a new terminal, navigate to frontend directory
cd frontend

# Install npm dependencies
npm install

# Start the Vite development server
npm run dev
```
*Frontend Application will be available at:* `http://localhost:5173`

---

### Option B: Docker Compose Setup

```bash
# Build and start all services (PostGIS, Redis, FastAPI, React/Nginx)
docker compose up --build -d

# View status
docker compose ps
```

---

## 8. Default Demo Credentials

All test accounts are pre-seeded with standardized demo credentials:

| Role | Username / Email | Password | Assigned Portal Route |
| :--- | :--- | :--- | :--- |
| **Government Admin** | `admin@dirs.gov` | `Admin123!` | `/command-center` |
| **Field Volunteer** | `volunteer@dirs.org` | `Volunteer123!` | `/volunteer` |
| **NGO Representative** | `ngo@dirs.org` | `Ngo123!` | `/ngo` |
| **Citizen** | `citizen@dirs.org` | `Citizen123!` | `/citizen` |

---

## 9. Automated Testing Guide

The system includes comprehensive automated test suites spanning unit tests, mathematical solver proofs, API contract tests, and Playwright end-to-end workflows.

### 1. Backend Pytest Suite (656 Automated Tests)
```bash
# From the project root:
# Windows PowerShell:
$env:PYTHONPATH="C:\Users\shubh\Downloads\DIRS\backend"
python -m pytest tests/backend -v

# Run with concise summary:
python -m pytest tests/backend -q
```
*Expected Result:* `656 passed in ~55s`

### 2. Frontend Production Build & TypeScript Verification
```bash
cd frontend
npm run build
```
*Expected Result:* `tsc` passes with zero type errors, Vite produces production bundle in `frontend/dist/`.

### 3. Playwright E2E Integration Suite
```bash
# Run headless browser end-to-end tests
npx playwright test
```

---

## 10. Documentation Index

The complete technical and academic documentation is cataloged under [`docs/`](file:///C:/Users/shubh/Downloads/DIRS/docs/):

- **Academic & Capstone Presentations:** [`docs/academic/`](file:///C:/Users/shubh/Downloads/DIRS/docs/academic/)
  - [Capstone Master Evidence Dossier](file:///C:/Users/shubh/Downloads/DIRS/docs/academic/capstone_evidence/DIRS_CAPSTONE_MASTER_EVIDENCE.md)
  - [Capstone Viva & Presentation Defense Package](file:///C:/Users/shubh/Downloads/DIRS/docs/academic/DIRS_CAPSTONE_VIVA_AND_PRESENTATION_PACKAGE.md)
  - [Live Demonstration Runbook](file:///C:/Users/shubh/Downloads/DIRS/docs/academic/DIRS_CAPSTONE_DEMO_RUNBOOK.md)
- **System Architecture & Design:** [`docs/architecture/`](file:///C:/Users/shubh/Downloads/DIRS/docs/architecture/)
  - [System Architecture Blueprint](file:///C:/Users/shubh/Downloads/DIRS/docs/architecture/DIRS_FINAL_SYSTEM_ARCHITECTURE.md)
  - [Database Schema & PostGIS Modeling](file:///C:/Users/shubh/Downloads/DIRS/docs/architecture/DIRS_FINAL_DATABASE_SCHEMA_OVERVIEW.md)
  - [CP-SAT Mathematical Formulations](file:///C:/Users/shubh/Downloads/DIRS/docs/architecture/PHASE6_MATHEMATICAL_FORMULATIONS.md)
- **API Catalog & Integration:** [`docs/api/`](file:///C:/Users/shubh/Downloads/DIRS/docs/api/)
  - [Comprehensive API Catalog](file:///C:/Users/shubh/Downloads/DIRS/docs/api/DIRS_FINAL_API_CATALOG.md)
  - [Traceability Matrix](file:///C:/Users/shubh/Downloads/DIRS/docs/api/MANUAL_ACCEPTANCE_API_TRACEABILITY.md)
- **Testing & Verification:** [`docs/testing/`](file:///C:/Users/shubh/Downloads/DIRS/docs/testing/)
  - [System Verification Report](file:///C:/Users/shubh/Downloads/DIRS/docs/testing/DIRS_FINAL_TEST_AND_VERIFICATION_REPORT.md)
  - [E2E Cross-Role Acceptance Report](file:///C:/Users/shubh/Downloads/DIRS/docs/testing/FINAL_CROSS_ROLE_E2E_REPORT.md)
- **Authoritative Forensic Audits:** [`docs/evidence/`](file:///C:/Users/shubh/Downloads/DIRS/docs/evidence/)
  - [Master System Audit Report (Full Pass)](file:///C:/Users/shubh/Downloads/DIRS/docs/evidence/DIRS_COMPLETE_SYSTEM_AUDIT_REPORT.md)
  - [Phase 7 Enterprise Hardening Audit](file:///C:/Users/shubh/Downloads/DIRS/docs/evidence/DIRS_PHASE7_ENTERPRISE_HARDENING_COMPLETION_REPORT.md)
- **Screenshots & Visuals:** [`docs/screenshots/`](file:///C:/Users/shubh/Downloads/DIRS/docs/screenshots/)
  - [Screenshot Registry & Specifications](file:///C:/Users/shubh/Downloads/DIRS/docs/screenshots/README.md)

---

## 11. Academic Attribution & Evaluation Notice

- **Institution:** School of Computer Science and Engineering (SCOPE), **VIT-AP University**, Andhra Pradesh, India.
- **Project Type:** Bachelor of Technology (B.Tech) Capstone Project.
- **Academic Year:** 2026.
- **Calibration Notice:** All disaster incident feeds, damage imagery, ward census boundaries (Chennai Wards 110–114), and financial budgets are calibrated against realistic disaster response standards for safe benchmark simulation and academic evaluation.

---

## 12. License & Governance

This project is licensed under the MIT License. Developed for academic evaluation, disaster intelligence research, and humanitarian emergency response innovation.
