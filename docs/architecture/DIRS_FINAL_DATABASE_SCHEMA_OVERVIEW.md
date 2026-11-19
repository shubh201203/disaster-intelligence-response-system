# DIRS — Definitive Final Database Schema Overview
## Disaster Intelligence and Response System (DIRS)

**Document Identifier:** `DIRS-CAPSTONE-SCHEMA-004`  
**Classification:** OFFICIAL / DATABASE SPECIFICATION  
**Target Release:** DIRS v5.2 (Capstone Release)  
**Parent Programme:** Phase 6G / Accelerated Work Package 4 (Capstone Packaging & Verification)  
**Publication Date:** November 18, 2026  
**Status:** Certified / Complete  

---

## 1. Schema Invariants & Migration State

* **Total Database Tables:** Exactly **40 Relational Tables**.
* **Active Migration Tool:** Alembic.
* **Alembic Version Head:** `phase6b_recovery_foundation`.
* **Migration Scripts in History:**
  1. `phase5b_schema_extensions.py` (Phase 5B)
  2. `phase5f_schema_extensions.py` (Phase 5F)
  3. `phase6b_recovery_data_foundation.py` (Phase 6B)
* **New Migrations in WP1, WP2, WP3, WP4:** **EXACTLY ZERO (0).**
* **Schema Boundary Rule:** No modifications to table columns, indexes, foreign keys, or database constraints were introduced.

---

## 2. Complete Inventory of the 40 Database Tables

```
========================================================================================
DIRS PRODUCTION RELATIONAL SCHEMA (40 TABLES)
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

## 3. Domain Entity Deep-Dives

### 3.1 Identity, Users & Roles
* **`users`:**
  - `id` (VARCHAR PK)
  - `email` (VARCHAR UNIQUE, indexed)
  - `hashed_password` (VARCHAR)
  - `full_name` (VARCHAR)
  - `role` (VARCHAR: `CITIZEN`, `VOLUNTEER`, `NGO`, `GOVT`, `ADMIN`)
  - `phone` (VARCHAR)
  - `is_active` (BOOLEAN)
  - `created_at`, `updated_at` (TIMESTAMP)
* **`citizen_profiles`:**
  - `id` (VARCHAR PK), `user_id` (VARCHAR FK $\to$ `users.id`)
  - `emergency_contact_name`, `emergency_contact_phone`
  - `address`, `latitude`, `longitude` (FLOAT)
* **`volunteer_profiles`:**
  - `id` (VARCHAR PK), `user_id` (VARCHAR FK $\to$ `users.id`)
  - `category` (VARCHAR: `RESCUE`, `MEDICAL`, `LOGISTICS`, `GENERAL`)
  - `skills` (JSON / ARRAY)
  - `medical_certification` (BOOLEAN)
  - `experience_years` (INTEGER)
  - `current_latitude`, `current_longitude` (FLOAT)
  - `is_available` (BOOLEAN)
* **`ngo_profiles`:**
  - `id` (VARCHAR PK), `user_id` (VARCHAR FK $\to$ `users.id`)
  - `org_name` (VARCHAR)
  - `registration_no` (VARCHAR)
  - `contact_person`, `address`
  - `verified` (BOOLEAN)

### 3.2 Disaster Incidents & Field Telemetry
* **`incidents`:**
  - `id` (VARCHAR PK)
  - `code` (VARCHAR UNIQUE: `INC-20261118-XXXX`)
  - `title`, `description` (TEXT)
  - `disaster_type` (VARCHAR: `FLOOD`, `CYCLONE`, `FIRE`, `EARTHQUAKE`, `LANDSLIDE`)
  - `severity` (INTEGER: 1 to 5)
  - `status` (VARCHAR: `REPORTED`, `VERIFIED`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`)
  - `latitude`, `longitude` (FLOAT), `address` (VARCHAR)
  - `casualties`, `injured`, `trapped_people` (INTEGER)
  - `needs_evacuation` (BOOLEAN)
  - `reporter_id` (VARCHAR FK $\to$ `users.id`)
  - `verified_by_id` (VARCHAR FK $\to$ `users.id`)
  - `cluster_id` (VARCHAR FK $\to$ `incident_clusters.id`)
* **`incident_reports`:**
  - `id` (VARCHAR PK), `incident_id` (VARCHAR FK $\to$ `incidents.id`)
  - Observational sub-reports submitted by citizens or responders.
* **`incident_clusters`:**
  - Geospatially grouped incident centroids (500m radius threshold).

### 3.3 Humanitarian Resources & Demands
* **`resources`:**
  - `id` (VARCHAR PK)
  - `name` (VARCHAR), `category` (VARCHAR: `FOOD`, `WATER`, `MEDICAL`, `SHELTER`, `EQUIPMENT`)
  - `quantity_available`, `total_quantity` (INTEGER)
  - `unit` (VARCHAR: `kits`, `liters`, `boxes`, `units`)
  - `owner_id` (VARCHAR FK $\to$ `users.id`)
  - `owner_type` (VARCHAR: `NGO`, `GOVT`, `COMMUNITY`)
  - `latitude`, `longitude`, `depot_location` (VARCHAR)
  - `status` (VARCHAR: `AVAILABLE`, `DISPATCHED`, `DEPLETED`)
* **`resource_requests`:**
  - `id` (VARCHAR PK)
  - `incident_id` (VARCHAR FK $\to$ `incidents.id`)
  - `requested_by_id` (VARCHAR FK $\to$ `users.id`)
  - `resource_type`, `quantity_needed`
  - `urgency` (VARCHAR: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
  - `status` (VARCHAR: `PENDING`, `ALLOCATED`, `FULFILLED`, `CANCELLED`)

### 3.4 Recovery Infrastructure & Precedence Dependencies
* **`recovery_projects`:**
  - `id` (VARCHAR PK)
  - `code` (VARCHAR UNIQUE: `REC-PRJ-XXXX`)
  - `name`, `description` (TEXT)
  - `sector` (VARCHAR: `POWER`, `WATER`, `HEALTH`, `TRANSPORT`, `HOUSING`, `EDUCATION`)
  - `estimated_cost` (NUMERIC / DECIMAL)
  - `duration_days` (INTEGER)
  - `priority` (VARCHAR: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
  - `status` (VARCHAR: `PROPOSED`, `APPROVED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`)
  - `ward`, `latitude`, `longitude`
* **`project_dependencies`:**
  - `id` (VARCHAR PK)
  - `predecessor_project_id` (VARCHAR FK $\to$ `recovery_projects.id`)
  - `successor_project_id` (VARCHAR FK $\to$ `recovery_projects.id`)
  - `dependency_type` (VARCHAR: `FINISH_TO_START`, `START_TO_START`)
  - `lag_days` (INTEGER)
* **`recovery_assessments`:**
  - `id` (VARCHAR PK)
  - `incident_id` (VARCHAR FK $\to$ `incidents.id`, nullable)
  - `facility_name`, `sector`, `ward`
  - `observed_damage_level` (VARCHAR: `NONE`, `LIGHT`, `MODERATE`, `HEAVY`, `TOTAL_COLLAPSE`)
  - `verified_damage_level` (VARCHAR, nullable)
  - `assessor_id` (VARCHAR FK $\to$ `users.id`)
  - `verifier_id` (VARCHAR FK $\to$ `users.id`, nullable)
  - `verification_status` (VARCHAR: `PENDING_VERIFICATION`, `VERIFIED`, `DISPUTED`, `REJECTED`)
  - `structural_notes`, `immediate_hazard`, `engineering_notes` (TEXT)
  - `assessor_confidence` (FLOAT: 0.0 to 1.0)
* **`community_recovery_metrics`:**
  - `id` (VARCHAR PK)
  - `ward` (VARCHAR, indexed)
  - `recovery_score` (FLOAT: 0.0 to 100.0)
  - `power_restoration_pct`, `water_restoration_pct`, `health_access_pct`, `schools_open_pct`, `livelihoods_active_pct` (FLOAT)
  - `active_shelter_count`, `remaining_displaced_persons` (INTEGER)
  - `vulnerability_index` (FLOAT: 0.0 to 1.0)
  - `assessed_at` (TIMESTAMP)

### 3.5 Recovery Portfolio Optimization
* **`optimization_runs`:**
  - `id` (VARCHAR PK)
  - `horizon_periods` (INTEGER: 1 to 120)
  - `solver_status` (VARCHAR: `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `MODEL_INVALID`, `UNKNOWN`)
  - `objective_value` (FLOAT, nullable)
  - `execution_duration_ms` (INTEGER)
  - `sha256_input_fingerprint` (VARCHAR: 64-char hex)
  - `dispatched_by_id` (VARCHAR FK $\to$ `users.id`)
* **`optimization_recommendations`:**
  - `id` (VARCHAR PK)
  - `run_id` (VARCHAR FK $\to$ `optimization_runs.id`)
  - `project_id` (VARCHAR FK $\to$ `recovery_projects.id`)
  - `scheduled_start_period`, `scheduled_completion_period` (INTEGER)
  - `allocated_budget` (NUMERIC)
  - `funding_source` (VARCHAR)
* **`optimization_override_logs`:**
  - `id` (VARCHAR PK)
  - `run_id` (VARCHAR FK $\to$ `optimization_runs.id`)
  - `overridden_by_id` (VARCHAR FK $\to$ `users.id`)
  - `justification` (TEXT)

---

## 4. Entity Ownership & Multi-Tenancy Patterns

1. **User Principal Separation:**
   All personal and organizational records are strictly bound by `user_id` or `owner_id`. Cross-user mutation is blocked at service and database query levels.
2. **NGO Ownership Demarcation:**
   `Resource` entities explicitly store `owner_id = user.id`. The frontend "My Org Only" filter queries by this key.
3. **Absence of Unsupported Schema Hacks:**
   No attempts were made to store NGO pledges, contractor bonds, or unauthorized metadata into freeform fields like `supplier_info` or `contact_person`. All data access respects declared SQLAlchemy schemas.
