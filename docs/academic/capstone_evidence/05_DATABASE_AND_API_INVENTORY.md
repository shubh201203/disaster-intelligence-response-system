# DIRS — Capstone Evidence Extraction: Database & API Inventory
## Module 05: Complete Relational Schema, PostGIS Tables & REST API Catalog

**Document Identifier:** `DIRS-CAPSTONE-EVIDENCE-05`  
**Classification:** OFFICIAL / ACADEMIC CAPSTONE EVIDENCE  
**Degree Programme:** Bachelor of Technology (B.Tech) in Computer Science & Engineering  
**Institution:** VIT-AP University, Andhra Pradesh, India  
**Target Release:** DIRS v6.0 (Enterprise Hardened)  
**Audit Status:** STRICT READ-ONLY FORENSIC EXTRACTION  
**Evidence Sources:** `DIRS_FINAL_DATABASE_SCHEMA_OVERVIEW.md`, `DIRS_FINAL_API_CATALOG.md`, `backend/app/routers/`  

---

## 1. Database Schema Overview & Migration Invariants

- **Total Relational Tables:** Exactly **40 Relational Tables** in PostgreSQL / PostGIS.
- **Active Migration Framework:** Alembic (SQLAlchemy Database Migrations).
- **Alembic Version Head:** Pinned strictly to `phase6b_recovery_foundation`.
- **Dialect Invariants:** Native PostgreSQL 16 with PostGIS 3.4 spatial extensions; isolated SQLite dialect fallback for in-memory testing.
- **Spatial Geometry Standard:** Spatial coordinates stored as OGC-compliant geometries (`geometry(Point, 4326)` in EPSG:4326 WGS-84 format) with PostGIS R-Tree spatial indexes.

---

## 2. Complete Inventory of the 40 Relational Tables

```
========================================================================================
DIRS PRODUCTION DATABASE SCHEMA: COMPLETE 40-TABLE INVENTORY
========================================================================================
 1. ai_predictions                  21. rag_query_logs
 2. ai_recommendations              22. recommendation_decisions
 3. alembic_version                 23. recovery_assessments
 4. alerts                          24. recovery_needs
 5. audit_logs                      25. recovery_override_logs
 6. citizen_profiles                26. recovery_projects
 7. community_recovery_metrics      27. recovery_resources
 8. cv_damage_assessments           28. rescue_tasks
 9. donations                       29. resource_demand_predictions
10. incident_clusters               30. resource_requests
11. incident_media                  31. resources
12. incident_reports                32. risk_assessments
13. incidents                       33. road_blockages
14. knowledge_chunks                34. shelters
15. knowledge_documents             35. simulation_runs
16. ngo_profiles                    36. simulation_scenarios
17. optimization_override_logs      37. spatial_ref_sys (PostGIS)
18. optimization_recommendations    38. users
19. optimization_runs               39. vehicles
20. project_dependencies            40. volunteer_profiles
========================================================================================
```

---

## 3. Core Database Entities & Key Relational Schemas

### 3.1 `users` & Role Profiles
- **`users`:** Primary principal identity table.
  - Columns: `id` (UUID PK), `email` (Unique, Indexed), `hashed_password` (BCrypt string), `role` (`CITIZEN`, `VOLUNTEER`, `NGO`, `GOVT`, `ADMIN`), `is_active` (Boolean), `created_at`, `updated_at`.
- **`citizen_profiles`:** Linked to `users.id` (1-to-1). Phone, emergency contact, home ward code.
- **`volunteer_profiles`:** Linked to `users.id` (1-to-1). Skills array (JSON), current availability status, mobile number.
- **`ngo_profiles`:** Linked to `users.id` (1-to-1). Organization legal name, registration number, primary depot location.

### 3.2 `incidents` & Emergency Response
- **`incidents`:** Core incident tracking entity.
  - Columns: `id` (UUID PK), `incident_code` (Unique human-readable string, e.g. `INC-2026-0042`), `title`, `description`, `disaster_type` (`FLOOD`, `CYCLONE`, `FIRE`, `LANDSLIDE`, `EARTHQUAKE`), `status` (`REPORTED`, `VERIFIED`, `ASSIGNED`, `RESOLVED`, `REJECTED`), `priority_level` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `priority_score` (Float), `latitude`, `longitude`, `geom` (`geometry(Point, 4326)`), `people_affected`, `injuries`, `reporter_id` (FK $\to$ `users.id`), `created_at`, `updated_at`.
- **`incident_media`:** Multi-media attachments (photos, videos) linked to `incidents.id` (FK). File paths, upload timestamp, MIME type.
- **`rescue_tasks`:** Operational rescue assignments. Linked to `incidents.id` (FK) and assigned volunteer (`users.id` FK). Columns: `task_status` (`ASSIGNED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`), `urgency_score`.

### 3.3 `resources` & Humanitarian Logistics
- **`resources`:** NGO depot inventory.
  - Columns: `id` (UUID PK), `name` (e.g. `Emergency Water Purification Kits`), `category` (`WATER`, `FOOD`, `MEDICAL`, `SHELTER`, `TRANSPORT`), `quantity` (Integer), `unit` (e.g. `packs`), `owner_id` (FK $\to$ `users.id`), `location_address`, `geom` (`geometry(Point, 4326)`), `updated_at`.
- **`resource_requests`:** Field relief demands. Linked to `incidents.id` (FK) or requesting shelter. Requested quantity, fulfilled quantity, priority.

### 3.4 `recovery_assessments` & Damage Certification
- **`recovery_assessments`:** Field structural damage inspection records.
  - Columns: `id` (UUID PK), `incident_id` (FK $\to$ `incidents.id`), `inspector_id` (FK $\to$ `users.id`), `ward_code`, `structure_type` (`RESIDENTIAL`, `COMMERCIAL`, `BRIDGE_CULVERT`, `ELECTRICAL_SUBSTATION`, `WATER_UTILITY`), `damage_pct` (Float $\in [0, 100]$), `habitability_status` (`HABITABLE`, `LIMITED_HABITABILITY`, `UNINHABITABLE`, `DESTROYED`), `verification_status` (`PENDING_VERIFICATION`, `VERIFIED`, `DISPUTED`, `SUPERSEDED`), `verifier_id` (FK $\to$ `users.id`), `created_at`, `updated_at`.
- **`recovery_override_logs`:** Immutable audit trail for statutory government engineering certifications.
  - Columns: `id` (UUID PK), `assessment_id` (FK), `original_damage_level`, `certified_damage_level`, `reason_code`, `engineer_rationale`, `officer_id` (FK $\to$ `users.id`), `timestamp`.

### 3.5 `recovery_projects` & Precedence DAG
- **`recovery_projects`:** Municipal reconstruction projects.
  - Columns: `id` (UUID PK), `project_code` (Unique, e.g. `PRJ-BRIDGE-04`), `name`, `sector` (`TRANSPORT`, `POWER`, `WATER`, `HEALTH`, `EDUCATION`), `estimated_cost_inr` (Numeric/Decimal string), `ccu_demand` (Integer), `duration_periods` (Integer $\ge 1$), `ward_code`, `status` (`PROPOSED`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`).
- **`project_dependencies`:** Precedence graph edges ($G = (V, E)$).
  - Columns: `id` (UUID PK), `predecessor_id` (FK $\to$ `recovery_projects.id`), `successor_id` (FK $\to$ `recovery_projects.id`), `lag_periods` (Integer $\ge 0$). Unique constraint on `(predecessor_id, successor_id)`.

### 3.6 `community_recovery_metrics` & Simulation
- **`community_recovery_metrics`:** Ward-level aggregated indicators.
  - Columns: `id` (UUID PK), `ward_code` (Indexed), `sector` (`HOUSING`, `HEALTHCARE`, `POWER_GRID`, `POTABLE_WATER`), `recovery_pct` (Float $\in [0, 100]$), `vulnerability_score` (Float $\phi \in [0.0, 1.0]$), `confidence_score` (Float $\in [0.0, 1.0]$), `assessed_date`, `updated_at`.

---

## 4. REST API Endpoint Catalog

The DIRS backend exposes **85 verified REST API endpoints** across 16 modular routers plus 1 real-time WebSocket endpoint:

### 4.1 Authentication & User Management
| Method | Endpoint | Role Guard | Request / Response Purpose |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/auth/login` | Public | Authenticates credentials; returns JWT access token and user metadata. |
| `POST` | `/api/v1/auth/register` | Public | Registers a new user account with specified role. |
| `GET` | `/api/v1/users/me` | Authenticated | Retrieves current authenticated user profile and role. |
| `GET` | `/api/v1/users` | `ADMIN` | Lists all registered platform users. |

### 4.2 Incidents & Emergency SOS
| Method | Endpoint | Role Guard | Request / Response Purpose |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/incidents` | Authenticated | Creates a new emergency incident report (supports `Idempotency-Key`). |
| `POST` | `/api/v1/incidents/sos` | Authenticated | Triggers high-priority SOS emergency distress beacon. |
| `GET` | `/api/v1/incidents` | Authenticated | Lists incidents with optional spatial, disaster type, and status filters. |
| `GET` | `/api/v1/incidents/{id}` | Authenticated | Retrieves detailed incident data including photos and verification status. |
| `POST` | `/api/v1/incidents/{id}/verify`| `GOVT`, `ADMIN` | Authorizes or rejects reported civilian incident; dispatches rescue task. |
| `POST` | `/api/v1/incidents/merge` | `GOVT`, `ADMIN` | Merges duplicate incidents reported in identical spatial vicinity. |

### 4.3 Volunteer Operations
| Method | Endpoint | Role Guard | Request / Response Purpose |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/v1/volunteers/my-tasks`| `VOLUNTEER` | Retrieves tasks assigned to the calling volunteer. |
| `POST` | `/api/v1/volunteers/tasks/{id}/status`| `VOLUNTEER` | Updates task pipeline state (`ASSIGNED` $\to$ `IN_PROGRESS` $\to$ `COMPLETED`). |
| `GET` | `/api/v1/volunteers/roster` | `GOVT`, `ADMIN` | Lists registered volunteers and current deployment statuses. |

### 4.4 Humanitarian Inventory & Logistics
| Method | Endpoint | Role Guard | Request / Response Purpose |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/v1/resources` | Authenticated | Queries relief depot supplies across all hubs or specific organization. |
| `POST` | `/api/v1/resources` | `NGO`, `ADMIN` | Registers new relief inventory stock at a specified depot. |
| `GET` | `/api/v1/resources/requests`| Authenticated | Lists civilian and shelter relief demand orders. |
| `POST` | `/api/v1/resources/{id}/dispatch`| `NGO`, `ADMIN` | Concurrency-safe dispatch decrementing stock via row-level locks. |

### 4.5 Emergency Shelters & Spatial GIS
| Method | Endpoint | Role Guard | Request / Response Purpose |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/v1/shelters/nearby` | Authenticated | PostGIS spatial radius query returning nearest available shelters. |
| `GET` | `/api/v1/shelters` | Authenticated | Lists all emergency evacuation shelters and occupancy metrics. |
| `GET` | `/api/v1/gis/incidents-spatial`| Authenticated | Returns GeoJSON FeatureCollection of active emergency incidents. |

### 4.6 Damage Assessments & Precedence DAG
| Method | Endpoint | Role Guard | Request / Response Purpose |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/recovery/damage-assessments/field-inspection`| `VOLUNTEER`, `GOVT` | Submits field structural damage inspection (supports `Idempotency-Key`). |
| `GET` | `/api/v1/recovery/assessments` | `GOVT`, `ADMIN` | Lists pending and verified damage inspection records. |
| `POST` | `/api/v1/recovery/damage-assessments/{id}/verify`| `GOVT` | Statutory engineering certification gate committing damage level and log. |
| `GET` | `/api/v1/recovery/dependencies/graph`| `GOVT`, `ADMIN` | Extracts precedence DAG, Kahn topological sort, and CPM-PL critical path. |
| `POST` | `/api/v1/recovery/dependencies/validate-edge`| `GOVT`, `ADMIN` | Zero-write dry-run cycle validator detecting loops on candidate edges. |

### 4.7 Community Recovery Monitoring & Simulation
| Method | Endpoint | Role Guard | Request / Response Purpose |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/v1/recovery/monitoring/community-metrics/summary`| Authenticated | Aggregates ward-level recovery, confidence, and vulnerability indicators. |
| `POST` | `/api/v1/recovery/monitoring/vulnerability-rescore`| `GOVT`, `ADMIN` | Computes updated vulnerability score ($\phi \in [0, 1]$) with audit delta. |
| `POST` | `/api/v1/recovery/simulation/what-if`| `GOVT`, `ADMIN` | Non-mutating forward simulation evaluating recovery trajectory under budgets. |

### 4.8 Recovery Portfolio Optimization
| Method | Endpoint | Role Guard | Request / Response Purpose |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/recovery/optimization/evaluate`| `ADMIN`, `GOVT` | Dispatches Google OR-Tools CP-SAT multi-period portfolio solver. |
| `GET` | `/api/v1/recovery/optimization/templates`| `ADMIN`, `GOVT` | Retrieves benchmark scenario templates (Rapid, Medium, Heavy). |

### 4.9 Real-Time WebSocket Endpoint
| Protocol | Endpoint | Role Guard | Purpose |
| :--- | :--- | :---: | :--- |
| `WebSocket`| `/ws/feed` | Authenticated | Bidirectional real-time stream broadcasting `INCIDENT_CREATED`, `TASK_ASSIGNED`, and `ALERT_ISSUED` events to connected command dashboards. |
