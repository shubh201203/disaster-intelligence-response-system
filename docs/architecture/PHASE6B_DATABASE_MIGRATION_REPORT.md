# DIRS Phase 6B — Database Migration Report
## Schema Extension & Migration Lifecycle Verification

**Status:** VERIFIED AND LOCKED  
**Date:** November 16, 2026  
**Auditor:** Principal Database Architect & Systems Forensic Auditor  
**System:** Disaster Intelligence and Response System (DIRS)  
**Database Engine:** PostgreSQL 18.6 (PostGIS 3.6.2) on x86_64-windows  
**Alembic Target Revision:** `phase6b_recovery_foundation`  
**Down Revision:** `phase5f_schema_ext`  

---

## 1. Pre-Migration Baseline Audit & Alembic Revision Stamping

Prior to any migration activity, a non-destructive audit of the live database was conducted:
- **Database Name:** `dirs_db`
- **Host / Port:** `localhost:5432`
- **User Role:** `dirs_user` (verified `NOSUPERUSER`)
- **Initial Table Count:** 34 physical tables (31 application tables + `spatial_ref_sys` PostGIS table + views).
- **Physical Schema Verification against `phase5f_schema_ext`:** An exhaustive query of `information_schema.columns` and `pg_indexes` verified that all columns introduced by `phase5f_schema_extensions.py` (`shelters.accessibility_features`, `volunteer_profiles.max_shift_hours`, `incidents.required_skills`, `optimization_runs.graph_version`, `optimization_recommendations.transit_distance_km`, etc.) and all prerequisite `phase5b_schema_extensions.py` tables (`vehicles`, `optimization_runs`, `optimization_recommendations`, `optimization_override_logs`) physically existed in `dirs_db`.
- **Alembic Revision Stamping Justification:** Because the database had been constructed and evolved across Phases 1–5F without a persisted `alembic_version` tracking table, `alembic stamp phase5f_schema_ext` was executed to synchronize Alembic's state tracking with the verified physical schema reality. No schema modifications or data wipes occurred during this synchronization.
- **Pre-Migration Physical Backup:** Created via `pg_dump` to:
  `C:\Users\shubh\Downloads\DIRS\backend\backups\dirs_db_pre_phase6b_backup.sql`  
  *Size:* 540,071 bytes (527.4 KB)  
  *Integrity:* Complete SQL script with COPY statements, sequence states, and PostGIS geometries intact.
- **Disposable Schema Restoration Audit:** The physical backup file was successfully restored into an isolated disposable test schema (`disposable_test_restore`) in PostgreSQL. All 31 tables, 38 foreign keys, 2 unique constraints, and PostGIS geometries were verified and reconstructed with 100% fidelity before teardown.

### Baseline Row Count Inventory (34 Existing Tables)
- `users`: 11 rows
- `incidents`: 18 rows
- `shelters`: 14 rows
- `resources`: 15 rows
- `tasks`: 15 rows
- `routes`: 14 rows
- `dispatches`: 11 rows
- `evacuation_routes`: 11 rows
- `shelter_allocations`: 11 rows
- `audit_logs`: 18 rows
- All other pre-existing lookup and association tables verified intact.

---

## 2. Migration Architecture: `phase6b_recovery_data_foundation.py`

The migration was implemented in `backend/alembic/versions/phase6b_recovery_data_foundation.py` following strict forward and backward idempotence.

### 2.1 Table Definitions & Relational Structure

#### 1. `recovery_assessments`
- **Purpose:** Tracks field structural assessments and damage evaluations across sectors.
- **Columns:**
  - `id` (VARCHAR(36), PK)
  - `assessment_code` (VARCHAR(30), NOT NULL, UNIQUE, Indexed)
  - `incident_id` (VARCHAR(36), FK $\rightarrow$ `incidents.id` ON DELETE CASCADE, Indexed)
  - `inspector_id` (VARCHAR(36), FK $\rightarrow$ `users.id` ON DELETE RESTRICT, Indexed)
  - `sector` (VARCHAR(50), NOT NULL, Indexed) — *HOUSING, HEALTH, EDUCATION, TRANSPORT, WATER_SANITATION, POWER, TELECOM, AGRICULTURE*
  - `facility_name` (VARCHAR(255), NOT NULL)
  - `damage_level` (VARCHAR(30), NOT NULL) — *NONE, MINOR, MODERATE, SEVERE, TOTAL_COLLAPSE*
  - `is_operational` (BOOLEAN, DEFAULT False)
  - `estimated_reconstruction_cost` (DOUBLE PRECISION, DEFAULT 0.0)
  - `structural_notes` (TEXT, Nullable)
  - `evidence_media_urls` (JSONB / JSON, DEFAULT [])
  - `cv_assessment_id` (VARCHAR(36), Nullable)
  - `latitude` (DOUBLE PRECISION, NOT NULL)
  - `longitude` (DOUBLE PRECISION, NOT NULL)
  - `geom` (GEOMETRY(POINT, 4326), Nullable)
  - `assessment_version` (INTEGER, DEFAULT 1, NOT NULL)
  - `is_current_version` (BOOLEAN, DEFAULT True, NOT NULL, Indexed)
  - `supersedes_assessment_id` (VARCHAR(36), FK $\rightarrow$ `recovery_assessments.id` ON DELETE SET NULL, Nullable)
  - `deduplication_cluster_id` (VARCHAR(36), Nullable, Indexed)
  - `verification_status` (VARCHAR(30), DEFAULT 'UNVERIFIED', NOT NULL) — *UNVERIFIED, VERIFIED, DISPUTED, REJECTED*
  - `verified_by_id` (VARCHAR(36), FK $\rightarrow$ `users.id` ON DELETE SET NULL, Nullable)
  - `verified_at` (TIMESTAMP, Nullable)
  - `created_at` (TIMESTAMP, DEFAULT UTC NOW)
  - `updated_at` (TIMESTAMP, DEFAULT UTC NOW)
- **Indices:**
  - `idx_recovery_assessments_geom` (GIST on `geom`)
  - `idx_recovery_assessments_sector_current` (`sector`, `is_current_version`)

#### 2. `recovery_needs`
- **Purpose:** Household and community recovery needs with PII protection.
- **Columns:**
  - `id` (VARCHAR(36), PK)
  - `need_code` (VARCHAR(30), NOT NULL, UNIQUE, Indexed)
  - `incident_id` (VARCHAR(36), FK $\rightarrow$ `incidents.id` ON DELETE CASCADE, Indexed)
  - `assessment_id` (VARCHAR(36), FK $\rightarrow$ `recovery_assessments.id` ON DELETE SET NULL, Nullable, Indexed)
  - `sector` (VARCHAR(50), NOT NULL, Indexed)
  - `target_beneficiary_group` (VARCHAR(100), NOT NULL)
  - `household_head_name_masked` (VARCHAR(100), Nullable)
  - `beneficiary_id_hash` (VARCHAR(64), Nullable, Indexed)
  - `vulnerability_score` (DOUBLE PRECISION, DEFAULT 0.0)
  - `estimated_cost` (DOUBLE PRECISION, NOT NULL)
  - `urgency_tier` (VARCHAR(20), DEFAULT 'MEDIUM') — *CRITICAL_TIER1, HIGH_TIER2, MEDIUM_TIER3, LOW_TIER4*
  - `status` (VARCHAR(30), DEFAULT 'IDENTIFIED') — *IDENTIFIED, VALIDATED, SOURCED, COMMITTED, FULFILLED*
  - `ward_code` (VARCHAR(50), Nullable, Indexed)
  - `district` (VARCHAR(100), Nullable)
  - `demographic_breakdown` (JSONB / JSON, DEFAULT {})
  - `created_at` (TIMESTAMP, DEFAULT UTC NOW)

#### 3. `recovery_projects`
- **Purpose:** Public reconstruction, restoration, and redevelopment projects.
- **Columns:**
  - `id` (VARCHAR(36), PK)
  - `project_code` (VARCHAR(30), NOT NULL, UNIQUE, Indexed)
  - `need_id` (VARCHAR(36), FK $\rightarrow$ `recovery_needs.id` ON DELETE SET NULL, Nullable, Indexed)
  - `title` (VARCHAR(255), NOT NULL)
  - `description` (TEXT, Nullable)
  - `sector` (VARCHAR(50), NOT NULL, Indexed)
  - `priority_tier` (VARCHAR(20), NOT NULL, Indexed)
  - `priority_score` (DOUBLE PRECISION, DEFAULT 0.0)
  - `status` (VARCHAR(30), DEFAULT 'PROPOSED', Indexed)
  - `estimated_cost` (DOUBLE PRECISION, NOT NULL)
  - `actual_expenditure` (DOUBLE PRECISION, DEFAULT 0.0)
  - `funding_source` (VARCHAR(100), Nullable)
  - `time_indexed_cost_profile` (JSONB / JSON, DEFAULT [])
  - `estimated_duration_days` (INTEGER, NOT NULL)
  - `planned_start_date` (TIMESTAMP, Nullable)
  - `planned_completion_date` (TIMESTAMP, Nullable)
  - `actual_start_date` (TIMESTAMP, Nullable)
  - `actual_completion_date` (TIMESTAMP, Nullable)
  - `lead_agency` (VARCHAR(100), Nullable)
  - `contractor_name` (VARCHAR(100), Nullable)
  - `assigned_manager_id` (VARCHAR(36), FK $\rightarrow$ `users.id` ON DELETE SET NULL, Nullable)
  - `latitude` (DOUBLE PRECISION, Nullable)
  - `longitude` (DOUBLE PRECISION, Nullable)
  - `geom` (GEOMETRY(GEOMETRY, 4326), Nullable)
  - `approval_status` (VARCHAR(30), DEFAULT 'PENDING_APPROVAL', Indexed)
  - `approved_by_id` (VARCHAR(36), FK $\rightarrow$ `users.id` ON DELETE SET NULL, Nullable)
  - `approved_at` (TIMESTAMP, Nullable)
  - `approval_notes` (TEXT, Nullable)
  - `created_at` (TIMESTAMP, DEFAULT UTC NOW)
  - `updated_at` (TIMESTAMP, DEFAULT UTC NOW)
- **Indices:**
  - `idx_recovery_projects_geom` (GIST on `geom`)

#### 4. `project_dependencies`
- **Purpose:** Precedence constraints forming the directed project network DAG.
- **Columns:**
  - `id` (VARCHAR(36), PK)
  - `predecessor_id` (VARCHAR(36), FK $\rightarrow$ `recovery_projects.id` ON DELETE CASCADE, NOT NULL, Indexed)
  - `successor_id` (VARCHAR(36), FK $\rightarrow$ `recovery_projects.id` ON DELETE CASCADE, NOT NULL, Indexed)
  - `dependency_type` (VARCHAR(20), DEFAULT 'FINISH_TO_START') — *FINISH_TO_START, START_TO_START, FINISH_TO_FINISH*
  - `lag_days` (INTEGER, DEFAULT 0)
  - `is_mandatory` (BOOLEAN, DEFAULT True)
  - `created_at` (TIMESTAMP, DEFAULT UTC NOW)
- **Constraints:**
  - `uq_pred_succ`: UNIQUE(`predecessor_id`, `successor_id`)

#### 5. `recovery_resources`
- **Purpose:** Resource allocations and Bill of Materials assigned to recovery projects.
- **Columns:**
  - `id` (VARCHAR(36), PK)
  - `project_id` (VARCHAR(36), FK $\rightarrow$ `recovery_projects.id` ON DELETE CASCADE, NOT NULL, Indexed)
  - `resource_category` (VARCHAR(50), NOT NULL) — *EQUIPMENT, MATERIAL, LABOR_SKILLED, LABOR_UNSKILLED, SPECIALIST*
  - `resource_name` (VARCHAR(100), NOT NULL)
  - `quantity_required` (DOUBLE PRECISION, NOT NULL)
  - `quantity_allocated` (DOUBLE PRECISION, DEFAULT 0.0)
  - `unit_of_measure` (VARCHAR(30), NOT NULL)
  - `unit_cost_estimate` (DOUBLE PRECISION, NOT NULL)
  - `actual_unit_cost` (DOUBLE PRECISION, DEFAULT 0.0)
  - `supplier_info` (VARCHAR(255), Nullable)
  - `delivery_status` (VARCHAR(30), DEFAULT 'ORDERED')
  - `created_at` (TIMESTAMP, DEFAULT UTC NOW)

#### 6. `community_recovery_metrics`
- **Purpose:** Longitudinal community health and infrastructure recovery tracking.
- **Columns:**
  - `id` (VARCHAR(36), PK)
  - `ward_code` (VARCHAR(50), NOT NULL, Indexed)
  - `district` (VARCHAR(100), NOT NULL)
  - `metric_date` (TIMESTAMP, NOT NULL, Indexed)
  - `active_shelter_count` (INTEGER, DEFAULT 0)
  - `remaining_displaced_persons` (INTEGER, DEFAULT 0)
  - `power_grid_restoration_pct` (DOUBLE PRECISION, DEFAULT 0.0)
  - `potable_water_access_pct` (DOUBLE PRECISION, DEFAULT 0.0)
  - `healthcare_facility_operational_pct` (DOUBLE PRECISION, DEFAULT 0.0)
  - `schools_open_pct` (DOUBLE PRECISION, DEFAULT 0.0)
  - `livelihoods_resumed_pct` (DOUBLE PRECISION, DEFAULT 0.0)
  - `overall_recovery_score` (DOUBLE PRECISION, DEFAULT 0.0)
  - `data_confidence` (DOUBLE PRECISION, DEFAULT 100.0)
  - `freshness_status` (VARCHAR(20), DEFAULT 'FRESH') — *FRESH, MODERATE, STALE_AMBER, EXPIRED_RED*
  - `last_verified_at` (TIMESTAMP, DEFAULT UTC NOW)
  - `verified_by_id` (VARCHAR(36), FK $\rightarrow$ `users.id` ON DELETE SET NULL, Nullable)
- **Constraints:**
  - `uq_ward_metric_date`: UNIQUE(`ward_code`, `metric_date`)

#### 7. `recovery_override_logs`
- **Purpose:** Immutable audit trail of human-in-the-loop decisions, approvals, and budget overrides.
- **Columns:**
  - `id` (VARCHAR(36), PK)
  - `project_id` (VARCHAR(36), FK $\rightarrow$ `recovery_projects.id` ON DELETE CASCADE, Nullable, Indexed)
  - `user_id` (VARCHAR(36), FK $\rightarrow$ `users.id` ON DELETE RESTRICT, NOT NULL, Indexed)
  - `action` (VARCHAR(50), NOT NULL) — *PROJECT_APPROVE, BUDGET_OVERRIDE, WEIGHT_ADJUSTMENT, DEPENDENCY_BYPASS, ASSESSMENT_SUPERSEDE*
  - `original_value` (JSONB / JSON, DEFAULT {})
  - `new_value` (JSONB / JSON, DEFAULT {})
  - `justification_reason` (TEXT, NOT NULL)
  - `ip_address` (VARCHAR(50), Nullable)
  - `timestamp` (TIMESTAMP, DEFAULT UTC NOW, Indexed)

---

## 3. Migration Lifecycle Verification

The migration was subjected to a rigorous bidirectional test cycle on PostgreSQL:

```bash
# 1. Forward Migration:
python -m alembic upgrade head
# Result: Applied phase6b_recovery_foundation cleanly.
# Database table count increased from 34 to 41.

# 2. Rollback Verification (Downgrade):
python -m alembic downgrade -1
# Result: Reverted to phase5f_schema_ext.
# All 7 recovery tables dropped cleanly with zero residual constraints or orphans.
# Table count returned to exactly 34.

# 3. Re-Upgrade to Current Head:
python -m alembic upgrade head
# Result: Applied phase6b_recovery_foundation cleanly.
# All 7 tables and 2 spatial GIST indices recreated successfully.
# Table count established at 41.
```

### Table Count Verification Query
```sql
SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';
-- Returned: 41
```

---

## 4. Referential & Constraint Integrity Verdict

- **Orphan Prevention:** All foreign keys referencing incidents or projects employ `ON DELETE CASCADE`, ensuring cleanup of associated assessments, needs, and project dependencies upon parent deletion.
- **Audit Preservation:** User references on audit and override logs employ `ON DELETE RESTRICT`, preventing accidental removal of historical accountability actors.
- **Spatial Compatibility:** Both Point (`recovery_assessments`) and Geometry (`recovery_projects`) use SRID 4326 and function transparently across PostgreSQL/PostGIS and SQLite in-memory test harnesses.

**Database Migration Status:** **CLEAN, NON-DESTRUCTIVE & APPROVED**
