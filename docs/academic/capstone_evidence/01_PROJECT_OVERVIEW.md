# DIRS — Capstone Evidence Extraction: Project Identity & Academic Overview
## Module 01: Project Identity, Problem Statement, Scope & Operational Boundaries

**Document Identifier:** `DIRS-CAPSTONE-EVIDENCE-01`  
**Classification:** OFFICIAL / ACADEMIC CAPSTONE EVIDENCE  
**Degree Programme:** Bachelor of Technology (B.Tech) in Computer Science & Engineering  
**Institution:** VIT-AP University, Andhra Pradesh, India  
**Project Title:** Disaster Intelligence and Response System (DIRS)  
**Parent Release:** DIRS v6.0 (Enterprise Hardened)  
**Audit Status:** STRICT READ-ONLY FORENSIC EXTRACTION  
**Evidence Source:** `DIRS_FINAL_SYSTEM_ARCHITECTURE.md`, `DIRS_CAPSTONE_VIVA_AND_PRESENTATION_PACKAGE.md`, `backend/app/config.py`  

---

## 1. Official Project Identity

- **Official Project Title:** Disaster Intelligence and Response System (DIRS)
- **Software Identifier:** `DIRS — Disaster Intelligence and Response System` (Configured in `backend/app/config.py:5`)
- **System Classification:** Multi-Agency Disaster Decision-Support, Field Intelligence & Recovery Optimization Platform
- **Target Release Baseline:** DIRS v6.0 (Enterprise Hardened, Capstone Verified)
- **Academic Context:** Senior Capstone Design Project, School of Computer Science and Engineering (SCOPE), VIT-AP University.

---

## 2. Problem Statement

Catastrophic disaster events—such as intense tropical cyclones, urban flash floods (e.g., the recurring inundations across the South Chennai coastal corridor and the Krishna River basin in Andhra Pradesh), landslides, and earthquakes—inflict devastating humanitarian and economic damage. In these crises, emergency management authorities face five critical systemic failures:

1. **Telecommunications Blackouts & Intake Data Loss:** Frontline citizens and field workers experience cellular packet drops and complete network severance. Conventional web applications lose unsaved form inputs, resulting in missing distress signals and stranded victims.
2. **Fragmented Multi-Agency Coordination:** Citizens, voluntary disaster brigades, non-governmental relief organizations (NGOs), and municipal emergency command operate in data silos without unified situational awareness or role-based access control.
3. **Unvalidated Volunteer Damage Reports:** Crowdsourced damage reports often lack structural validation, leading to misallocated emergency repair teams based on unverified civilian perceptions.
4. **Disregard for Infrastructure Precedence & Critical Paths:** Municipal reconstruction efforts frequently schedule repair projects arbitrarily, neglecting physical interdependencies (e.g., attempting to restore a water treatment plant before its primary electrical substation is energized or access roads are cleared), triggering circular project blockages.
5. **Suboptimal, Uncoordinated Resource & Budget Allocation:** Post-disaster recovery involves hundreds of competing civil repair projects, constrained multi-period fiscal budgets (INR), and scarce municipal civil capability units (CCUs). Manual scheduling fails to optimize socio-economic recovery impact, resulting in stalled reconstruction and financial insolvency.

---

## 3. Motivation

The motivation behind DIRS is to engineer an enterprise-grade, mathematically grounded, and offline-resilient operational platform that addresses both **immediate crisis survival** and **long-term municipal rehabilitation**. Rather than treating disaster response as a simple CRUD ticketing system, DIRS bridges the gap between field operational intake and high-performance operations research by coupling local-first browser persistence with Google OR-Tools discrete constraint programming.

---

## 4. Main Project Objectives

The DIRS architecture was engineered to accomplish six primary technical objectives:

1. **Local-First Offline Resilience:** Provide unbreakable client-side persistence for emergency incident reports and structural damage assessments using browser IndexedDB, reinforced by an authenticated Web Crypto AES-256-GCM vault and idempotent synchronization.
2. **Least-Privilege Multi-Role Governance:** Enforce strict role-based access control (RBAC) across five operational personas: Citizens, Volunteers, NGOs, Government Command, and System Administrators.
3. **Statutory Engineering Verification Gate:** Establish an authoritative certification protocol where volunteer field damage assessments must be reviewed and certified by authorized municipal engineers before altering civil recovery metrics.
4. **Infrastructure Precedence & Critical Path Intelligence:** Model civil infrastructure reconstruction as a directed acyclic graph (DAG), compute early/late schedules and critical paths using Kahn’s topological sort and CPM-PL (Critical Path Method with Project Lag), and validate dependency links using zero-write dry-run cycle detection.
5. **Community Recovery Monitoring & What-If Simulation:** Continuously evaluate ward-level recovery progress through exponential confidence decay, census-reconciled vulnerability rescoring ($\phi \in [0.0, 1.0]$), and non-mutating discrete forward recovery simulation.
6. **Mathematical Recovery Portfolio Optimization:** Formulate post-disaster project scheduling as a multi-period integer programming problem solved via Google OR-Tools CP-SAT, enforcing dual-ledger solvency across periodic financial liquidity (INR) and civil capability units (CCU).

---

## 5. Target User Personas & Core Use Cases

| Persona | Operational Context | Primary Use Cases | Interface Route |
| :--- | :--- | :--- | :--- |
| **CITIZEN** | Affected civilians, local residents, evacuees | Emergency SOS distress beacon; public incident reporting; offline draft intake; nearby emergency shelter discovery; municipal recovery metric tracking; grounded safety assistant (RAG). | `/citizen`, `/citizen/report`, `/shelters` |
| **VOLUNTEER** | Registered community responders, rescue workers | Assigned rescue mission execution; real-time task pipeline status updates; standardized field structural damage inspections; offline inspection draft staging. | `/volunteer` |
| **NGO** | Humanitarian relief agencies, charity logistics hubs | Relief inventory depot management; organization-scoped supply views; real-time field relief demand tracking; concurrency-safe medical/ration kit dispatching. | `/ngo` |
| **GOVERNMENT** | Municipal disaster commissioners, civil engineers | Live incident GIS command center; statutory engineering verification gate for damage certification; infrastructure precedence DAG visualizer; dry-run cycle validation; ward recovery monitoring; what-if recovery simulation. | `/admin` (Command Center), `/admin/simulation` |
| **ADMIN** | Recovery optimization planners, system directors | OR-Tools CP-SAT recovery optimization console; multi-period budget and resource matrix configuration; 1-based periodic Gantt schedule generation; dual-ledger solvency verification; 4-tier infeasibility diagnostic core. | `/admin/recovery-optimization` |

---

## 6. Disaster Management Lifecycle Coverage

DIRS spans all three canonical phases of the National Disaster Management Authority (NDMA) lifecycle:

```
[Phase 1: Preparedness & Mitigation]
  - Geospatial emergency shelter registry with capacity and spatial proximity indexing.
  - Relief resource inventory depot tracking across humanitarian NGOs.
  - Baseline census demographic mapping and municipal ward profile cataloging.
                     |
                     v
[Phase 2: Immediate Emergency Response]
  - Instantaneous SOS distress beacon broadcast via WebSockets.
  - Local-first offline incident reporting with client-side idempotency keys.
  - Real-time volunteer rescue task allocation and mission status pipelines.
  - Concurrency-safe humanitarian relief dispatch with row-level database locking.
                     |
                     v
[Phase 3: Reconstruction, Recovery & Rehabilitation]
  - Government engineering verification gate for field damage assessments.
  - Infrastructure restoration precedence DAG extraction and CPM-PL critical path analysis.
  - Community recovery metric tracking with exponential confidence decay.
  - Multi-sector vulnerability rescoring ($\phi$) and forward What-If recovery simulation.
  - CP-SAT multi-period integer optimization of reconstruction projects under dual INR/CCU ledgers.
```

---

## 7. Project Scope, Boundaries & Exclusions

To preserve strict academic and engineering rigor, the operational boundaries of the DIRS implementation are explicitly defined:

### In-Scope & Verified Capabilities
- Full-stack TypeScript (React 18) and Python (FastAPI) web platform.
- 40 relational database tables managed under PostgreSQL/PostGIS (with SQLite test fallback).
- 85 verified REST API endpoints + real-time WebSocket `/ws/feed`.
- Pure topological sorting (Kahn's algorithm) and CPM-PL project scheduling.
- Google OR-Tools CP-SAT discrete constraint optimization solver.
- Client-side IndexedDB persistence with native Web Crypto AES-256-GCM vaulting.
- Process-local idempotency caching with SHA-256 payload fingerprinting.
- 827 passing automated tests (656 backend, 120 frontend contracts, 51 browser E2E).

### Exclusions & Project Boundaries
1. **No External Paid Cloud Infrastructure:** The project is verified in local and staging environments. Live AWS/GCP cloud provisioning, Kubernetes cluster orchestration, and managed CDN TLS termination are documented designs, not active deployments.
2. **No Hardware Telecommunications Integration:** Emergency SOS distress signals broadcast via WebSocket to the command center; physical GSM cellular SMS gateways, automated satellite transmitters, and LoRaWAN field transceivers are excluded.
3. **No Financial Payment Gateways:** NGO inventory tracking reflects physical donations and dispatch logistics; live banking payment processing or monetary donations are out of scope.
4. **No Drone Hardware Robotics:** Computer vision damage tags (`cv_damage_assessments`) accept uploaded screening telemetry; autonomous physical drone flight control is excluded.
5. **Multi-Worker Idempotency Limitation:** The server-side idempotency service is certified **Process-Local Only**. Distributed deduplication across multiple server worker processes requires an external Redis cache.
