# DIRS Phase 5B — Optimization Layer Data Model & Schema Design Specification

## Executive Summary

Phase 5B establishes the database schema extensions and persistent data foundation required for the DIRS Phase 5 Optimization Layer. 

In strict adherence to Phase 5A approval guidelines:
- **Zero optimization algorithms, OR-Tools solvers, or routing engines are implemented in 5B.**
- Existing Phase 3C and Phase 4 capabilities, API contracts, and database models remain **100% backward compatible and unchanged in behavior**.
- All foreign key references align with existing primary key data types (`String(36)` UUID format).

---

## 1. Complete Schema Entity Architecture

```
┌───────────────────────────────────────────────────────────┐
│ EXISTING ENTITIES                                         │
│ User (id, role: GOVT/VOLUNTEER/NGO/CITIZEN)              │
│ Incident (id, severity_level, priority_score, geom)       │
│ Resource (id, category, available_quantity, location_lat) │
│ Shelter (id, total_capacity, current_occupancy, geom)     │
│ AuditLog (id, action, user_id, target_entity, details)   │
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ NEW PHASE 5B ENTITIES                                     │
├───────────────────────────────────────────────────────────┤
│ Vehicle                                                   │
│ - id, vehicle_code, vehicle_type, owner_type, owner_id    │
│ - capacity_weight_kg, capacity_volume_m3                  │
│ - current_location_lat, current_location_lng, depot_id    │
│ - status (AVAILABLE, ASSIGNED, IN_TRANSIT, UNAVAILABLE)   │
├───────────────────────────────────────────────────────────┤
│ OptimizationRun                                           │
│ - id, status (PROPOSED, APPROVED, REJECTED, MODIFIED)     │
│ - requesting_user_id, objective_config_json               │
│ - input_snapshot_json, solver_metadata_json, runtime_ms   │
├───────────────────────────────────────────────────────────┤
│ OptimizationRecommendation                                │
│ - id, run_id, recommendation_type, incident_id, depot_id  │
│ - vehicle_id, shelter_id, volunteer_id, commodity        │
│ - allocated_quantity, proposed_route_json, status         │
├───────────────────────────────────────────────────────────┤
│ OptimizationOverrideLog                                   │
│ - id, run_id, user_id (GOVT role mandatory), action       │
│ - original_value_json, overridden_value_json              │
│ - justification_reason, audit_log_id                      │
└───────────────────────────────────────────────────────────┘
```

---

## 2. New & Modified Schema Details

### 2.1 New Table: `vehicles` (`Vehicle` model in `backend/app/models/vehicle.py`)

Stores physical emergency transport assets with multi-dimensional payload capacities (weight & volume), depot locations, and operational availability states.

| Column Name | SQL Data Type | Constraints & Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key | UUID v4 string identifier |
| `vehicle_code` | `VARCHAR(50)` | Unique, Indexed, Non-Null | Unique vehicle identifier (e.g. `VEH-TRK-001`) |
| `vehicle_type` | `VARCHAR(50)` | Non-Null, Indexed | Transport class (`TRUCK`, `AMBULANCE`, `BOAT`, `VAN`) |
| `owner_type` | `VARCHAR(50)` | Default `'GOVT'` | Owner category (`GOVT`, `NGO`, `VOLUNTEER`) |
| `owner_id` | `VARCHAR(36)` | FK `users.id`, Nullable | Owning user or organization user ID |
| `capacity_weight_kg`| `FLOAT` | Default `0.0` | Maximum payload weight limit ($kg$) |
| `capacity_volume_m3`| `FLOAT` | Default `0.0` | Maximum payload volume limit ($m^3$) |
| `current_location_lat`| `FLOAT` | Nullable | Current WGS84 latitude coordinate |
| `current_location_lng`| `FLOAT` | Nullable | Current WGS84 longitude coordinate |
| `depot_id` | `VARCHAR(36)` | FK `resources.id`, Nullable | Home depot / warehouse reference |
| `status` | `VARCHAR(50)` | Default `'AVAILABLE'`, Indexed | State: `AVAILABLE`, `ASSIGNED`, `IN_TRANSIT`, `UNAVAILABLE`, `MAINTENANCE` |
| `is_active` | `BOOLEAN` | Default `True` | Active operational status flag |
| `operational_constraints`| `JSON` | Default `{}` | Operational bounds (e.g. flood capability, max speed) |
| `created_at` | `DATETIME` | Default `utc_now()` | Record creation timestamp |
| `updated_at` | `DATETIME` | Default `utc_now()`, OnUpdate | Record modification timestamp |

### 2.2 Modified Table: `road_blockages` (`RoadBlockage` model in `backend/app/models/rescue.py`)

Extends existing `road_blockages` table with dynamic network accessibility fields consumed by the future graph engine.

| Added Column Name | SQL Data Type | Constraints & Default | Description |
| :--- | :--- | :--- | :--- |
| `blockage_status` | `VARCHAR(50)` | Default `'IMPASSABLE'`, Indexed | State: `IMPASSABLE`, `DELAYED`, `CLEARING`, `RESOLVED` |
| `effective_at` | `DATETIME` | Default `utc_now()` | Timestamp when blockage became effective |
| `expiry_at` | `DATETIME` | Nullable | Estimated timestamp when blockage clears |
| `delay_penalty_mins`| `FLOAT` | Default `0.0` | Travel time penalty in minutes for `DELAYED` state |
| `source` | `VARCHAR(100)`| Default `'FIELD_REPORT'`| Reporting source (`FIELD_REPORT`, `SATELLITE`, `GOVT`) |
| `created_by_id` | `VARCHAR(36)` | FK `users.id`, Nullable | User ID of reporting agent |

### 2.3 New Table: `optimization_runs` (`OptimizationRun` model in `backend/app/models/optimization.py`)

Persists the execution metadata, input snapshot, objective weights, and status of an optimization calculation.

| Column Name | SQL Data Type | Constraints & Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key | UUID v4 string identifier |
| `status` | `VARCHAR(50)` | Default `'PROPOSED'`, Indexed | Lifecycle: `PROPOSED`, `APPROVED`, `REJECTED`, `MODIFIED` |
| `run_timestamp` | `DATETIME` | Default `utc_now()`, Indexed | Execution invocation timestamp |
| `requesting_user_id`| `VARCHAR(36)` | FK `users.id`, Non-Null | User ID invoking optimization |
| `objective_config_json`| `JSON` | Default `{}` | Objective function weights ($\alpha_1..4$) & version |
| `input_snapshot_json`| `JSON` | Default `{}` | Frozen snapshot of incidents, inventory, vehicles, blockages |
| `solver_metadata_json`| `JSON` | Default `{}` | Solver version, parameters, configuration flags |
| `runtime_ms` | `FLOAT` | Nullable | Measured optimization wall-clock execution latency |
| `optimality_gap` | `FLOAT` | Nullable | Solution optimality gap percentage |
| `feasibility_status`| `VARCHAR(50)` | Default `'FEASIBLE'` | Solver output: `FEASIBLE`, `RELAXED`, `INFEASIBLE` |
| `created_at` | `DATETIME` | Default `utc_now()` | Record creation timestamp |

### 2.4 New Table: `optimization_recommendations` (`OptimizationRecommendation` model in `backend/app/models/optimization.py`)

Persists specific assignment or routing recommendation items computed by an optimization run.

| Column Name | SQL Data Type | Constraints & Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key | UUID v4 string identifier |
| `run_id` | `VARCHAR(36)` | FK `optimization_runs.id`, Non-Null, Index | Parent optimization run reference |
| `recommendation_type`| `VARCHAR(50)`| Non-Null, Indexed | Type: `RESOURCE_DISPATCH`, `VEHICLE_ROUTE`, `SHELTER_EVACUATION`, `VOLUNTEER_ASSIGNMENT` |
| `incident_id` | `VARCHAR(36)` | FK `incidents.id`, Nullable | Targeted incident reference |
| `depot_id` | `VARCHAR(36)` | FK `resources.id`, Nullable | Source depot / warehouse reference |
| `vehicle_id` | `VARCHAR(36)` | FK `vehicles.id`, Nullable | Dispatched vehicle reference |
| `shelter_id` | `VARCHAR(36)` | FK `shelters.id`, Nullable | Allocated shelter reference |
| `volunteer_id` | `VARCHAR(36)` | FK `users.id`, Nullable | Assigned volunteer reference |
| `commodity_category`| `VARCHAR(50)`| Nullable | Resource commodity type |
| `allocated_quantity`| `FLOAT` | Default `0.0` | Allocated quantity of commodity / personnel |
| `proposed_route_json`| `JSON` | Default `{}` | Waypoints, GeoJSON geometries, node sequence |
| `objective_contribution`| `FLOAT` | Default `0.0` | Contribution to total cost function $Z$ |
| `explanation` | `TEXT` | Nullable | Human-readable AI decision rationale |
| `status` | `VARCHAR(50)` | Default `'PROPOSED'`, Indexed | Item state: `PROPOSED`, `APPROVED`, `REJECTED`, `MODIFIED` |
| `created_at` | `DATETIME` | Default `utc_now()` | Record creation timestamp |

### 2.5 New Table: `optimization_override_logs` (`OptimizationOverrideLog` model in `backend/app/models/optimization.py`)

Immutable audit log of all Government Command Center approvals, modifications, and rejections.

| Column Name | SQL Data Type | Constraints & Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | Primary Key | UUID v4 string identifier |
| `run_id` | `VARCHAR(36)` | FK `optimization_runs.id`, Non-Null, Index | Target optimization run reference |
| `user_id` | `VARCHAR(36)` | FK `users.id`, Non-Null | Government user performing override (Must have `GOVT` role) |
| `action` | `VARCHAR(50)` | Non-Null | Override action: `APPROVE`, `MODIFY`, `REJECT` |
| `original_value_json`| `JSON` | Default `{}` | Original recommendation state before action |
| `overridden_value_json`| `JSON` | Default `{}` | Modified state approved by government official |
| `justification_reason`| `TEXT` | Non-Null | Mandatory government official operational reason |
| `audit_log_id` | `VARCHAR(36)` | FK `audit_logs.id`, Nullable | Linked system `AuditLog` entry ID |
| `created_at` | `DATETIME` | Default `utc_now()` | Record creation timestamp |

### 2.6 Modified Table: `volunteer_profiles` (`VolunteerProfile` model in `backend/app/models/user.py`)

Extends volunteer profile with structured skill categories and real-time assignment status while preserving original `skills` JSON list.

| Added Column Name | SQL Data Type | Constraints & Default | Description |
| :--- | :--- | :--- | :--- |
| `skill_category` | `VARCHAR(50)` | Default `'GENERAL'`, Indexed | Category: `MEDICAL`, `RESCUE`, `LOGISTICS`, `GENERAL` |
| `assignment_status` | `VARCHAR(50)` | Default `'UNASSIGNED'`, Indexed | State: `UNASSIGNED`, `ASSIGNED`, `ON_MISSION` |

---

## 3. Relationships & Foreign Key Matrix

- `Vehicle.owner_id` $\rightarrow$ `User.id`
- `Vehicle.depot_id` $\rightarrow$ `Resource.id`
- `RoadBlockage.created_by_id` $\rightarrow$ `User.id`
- `OptimizationRun.requesting_user_id` $\rightarrow$ `User.id`
- `OptimizationRecommendation.run_id` $\rightarrow$ `OptimizationRun.id`
- `OptimizationRecommendation.incident_id` $\rightarrow$ `Incident.id`
- `OptimizationRecommendation.depot_id` $\rightarrow$ `Resource.id`
- `OptimizationRecommendation.vehicle_id` $\rightarrow$ `Vehicle.id`
- `OptimizationRecommendation.shelter_id` $\rightarrow$ `Shelter.id`
- `OptimizationRecommendation.volunteer_id` $\rightarrow$ `User.id`
- `OptimizationOverrideLog.run_id` $\rightarrow$ `OptimizationRun.id`
- `OptimizationOverrideLog.user_id` $\rightarrow$ `User.id`
- `OptimizationOverrideLog.audit_log_id` $\rightarrow$ `AuditLog.id`

---

## 4. Local Environment & PostGIS Limitation Disclosure

> [!NOTE]
> **LOCAL ENVIRONMENT LIMITATION DISCLOSURE:**  
> - In PostgreSQL production environments with PostGIS extension enabled, spatial points use GeoAlchemy2 `Geometry(geometry_type='POINT', srid=4326)`.
> - In local development / `pytest` environments using SQLite (`sqlite:///./test_dirs.db`), GeoAlchemy2 DDL event listeners are bypassed, and `Geometry` columns compile as SQL `TEXT` storing EWKT string geometries.
> - Schema migrations and models support both PostgreSQL/PostGIS and SQLite dialects natively without breaking existing test suites.
