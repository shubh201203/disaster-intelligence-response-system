# DIRS — Phase 5F-B Shelter & Volunteer Optimization
## Schema & Data Foundation Implementation Report

**Implementation Phase:** Phase 5F-B ONLY  
**System Component:** Data Model, Pydantic Schemas, Alembic Migration, Validation Suite  
**Status:** `IMPLEMENTED — AWAITING FORENSIC AUDIT`  
*(Phase 4, Phase 5A, Phase 5B, Phase 5C, Phase 5D, Phase 5E are FROZEN AND APPROVED)*

---

## A. Scope Implemented

This phase implements the database and schema foundation required for the approved Phase 5F Shelter and Volunteer Optimization formulation. In strict adherence to authorization boundaries:
- **No optimization algorithms or solvers were implemented** (CP-SAT formulations for shelter assignment and volunteer dispatch belong exclusively to Phase 5F-C/D).
- **Frozen phases (5C, 5D, 5E) were NOT modified.**
- **Phase 5G was NOT implemented.**
- **No real-world datasets or deployment claims are made.**

### Files Modified & Created
1. **Research & Objective Alignment:**
   - [`docs/PHASE5F_OBJECTIVE_DESIGN.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE5F_OBJECTIVE_DESIGN.md): Clarified volunteer objective formulation regarding $\lambda_1 / \lambda_2$ additive hierarchical surcharge for medical unmet tasks ($2.5\times$ base penalty).
   - [`docs/PHASE5F_RESEARCH_REPORT.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE5F_RESEARCH_REPORT.md): Reconciled Section 10 with the hierarchical medical surcharge formulation.
2. **SQLAlchemy Data Models:**
   - [`backend/app/models/shelter.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/shelter.py): Extended `Shelter` model with physical and operational attributes.
   - [`backend/app/models/user.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/user.py): Extended `VolunteerProfile` model with fatigue and transit constraints.
   - [`backend/app/models/incident.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/incident.py): Extended `Incident` model with demographic breakdown and skill requirements.
   - [`backend/app/models/optimization.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/models/optimization.py): Extended `OptimizationRun` and `OptimizationRecommendation` with Phase 5F dispatch tracking fields.
3. **Pydantic Validation & API Schemas:**
   - [`backend/app/schemas/shelter.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/schemas/shelter.py): Added Phase 5F fields to `ShelterCreate` and `ShelterResponse`. Added dynamic property `remaining_capacity`.
   - [`backend/app/schemas/user.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/schemas/user.py): Added `max_shift_hours`, `max_travel_time_mins`, `shift_availability` to `VolunteerProfileResponse`.
   - [`backend/app/schemas/incident.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/schemas/incident.py): Added `required_skills` and `evacuation_demographics` to `IncidentCreate` and `IncidentResponse`.
   - [`backend/app/schemas/optimization.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/schemas/optimization.py): Extended `OptimizationRecommendationBase` and `OptimizationRunResponse` with Phase 5F fields.
4. **Database Migrations:**
   - [`backend/alembic/versions/phase5f_schema_extensions.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/alembic/versions/phase5f_schema_extensions.py): Added revision `phase5f_schema_ext` chained to `phase5b_schema_ext`.
   - [`backend/alembic.ini`](file:///c:/Users/shubh/Downloads/DIRS/backend/alembic.ini): Fixed logger configuration syntax.
   - [`backend/alembic/env.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/alembic/env.py): Configured SQLAlchemy URL override compatibility.
5. **Validation Test Suite:**
   - [`tests/backend/test_phase5f_schema.py`](file:///c:/Users/shubh/Downloads/DIRS/tests/backend/test_phase5f_schema.py): 12 comprehensive unit and integration tests covering models, Pydantic validation, serialization, defaults, and migration graph integrity.

---

## B. Database Changes

### 1. `shelters` Table
- `accessibility_features`: `Boolean`, default=`False`, nullable=`False`. Indicates wheelchair ramps, ADA compliance, and accessible facilities.
- `power_available`: `Boolean`, default=`True`, nullable=`False`. Indicates operational electrical grid or generator backup.
- `sanitation_available`: `Boolean`, default=`True`, nullable=`False`. Indicates operational water and sanitation infrastructure.
- `disaster_compatibility`: `JSON`, default=`list`, nullable=`False`. List of compatible disaster types (e.g. `["FLOOD", "CYCLONE"]`).
- `last_verified_at`: `DateTime`, nullable=`True`. Timestamp of last ground-truth facility inspection.

### 2. `volunteer_profiles` Table
- `max_shift_hours`: `Float`, default=`8.0`, nullable=`False`. Maximum shift length before fatigue restrictions apply ($W_v^{\max}$).
- `max_travel_time_mins`: `Float`, default=`45.0`, nullable=`False`. Maximum acceptable one-way transit time ($\tau_v^{\max}$).
- `shift_availability`: `JSON`, default=`list`, nullable=`False`. Array of available shift identifier strings (e.g. `["SHIFT_MORNING", "SHIFT_EVENING"]`).

### 3. `incidents` Table
- `required_skills`: `JSON`, default=`dict`, nullable=`False`. Dictionary mapping skill categories to integer personnel requirements ($d_{ikt}$).
- `evacuation_demographics`: `JSON`, default=`dict`, nullable=`False`. Breakdown of evacuee populations by demographic group ($p_{ig}$): `GEN`, `ACC`, `MED`, `MED_ACC`.

### 4. `optimization_runs` Table
- `graph_version`: `String(64)`, nullable=`True`. Version tag or hash of the road network graph used for transit calculation.

### 5. `optimization_recommendations` Table
- `demographic_group`: `String(50)`, nullable=`True`, indexed. Demographic group classification for shelter assignments.
- `skill_category`: `String(50)`, nullable=`True`, indexed. Skill category classification for volunteer deployments.
- `shift_id`: `String(50)`, nullable=`True`. Operational shift window identifier.
- `transit_time_minutes`: `Float`, nullable=`True`. Estimated transit duration from graph matrix.
- `transit_distance_km`: `Float`, nullable=`True`. Estimated transit distance from graph matrix.

---

## C. Formulation Mapping

| Table / Model | Field | Formulation Variable / Parameter | Constraint / Purpose |
|---|---|---|---|
| `shelters` | `accessibility_features` | $A_s \in \{0, 1\}$ | Disability accessibility compatibility: $\sum_i (x_{i, s, \text{ACC}} + x_{i, s, \text{MED\_ACC}}) \le C_s \cdot A_s$ |
| `shelters` | `power_available` | $P_s \in \{0, 1\}$ | Medical evacuee compatibility: $\sum_i (x_{i, s, \text{MED}} + x_{i, s, \text{MED\_ACC}}) \le C_s \cdot P_s \cdot M_s$ |
| `shelters` | `sanitation_available` | $S_s \in \{0, 1\}$ | Habitability verification; minimum sanitation threshold |
| `shelters` | `disaster_compatibility` | $\Delta_s \subseteq \mathcal{D}$ | Flood/cyclone hazard safety: $x_{is} = 0$ if disaster type $D_i \notin \Delta_s$ |
| `shelters` | `last_verified_at` | $T^{\text{audit}}_s$ | Information freshness validation for human-in-the-loop audit |
| `volunteer_profiles` | `max_shift_hours` | $W_v^{\max}$ | Volunteer fatigue constraint: $\sum_{k, t} w_k \cdot y_{vkt} \le W_v^{\max}$ |
| `volunteer_profiles` | `max_travel_time_mins` | $\tau_v^{\max}$ | Volunteer transit boundary constraint: $\tau_{vi} \le \tau_v^{\max}$ |
| `volunteer_profiles` | `shift_availability` | $A_{vt} \in \{0, 1\}$ | Availability restriction: $y_{vkt} \le A_{vt}$ |
| `incidents` | `required_skills` | $d_{ikt} \ge 0$ | Skill coverage demand by incident, skill category, and shift |
| `incidents` | `evacuation_demographics` | $p_{ig} \ge 0$ | Evacuee population by demographic category ($g \in \{\text{GEN}, \text{ACC}, \text{MED}, \text{MED\_ACC}\}$) |
| `optimization_runs` | `graph_version` | $\mathcal{G}_{\text{ver}}$ | Lineage tracking connecting optimization run to specific graph snapshot |
| `optimization_recommendations` | `demographic_group` | $g$ | Records demographic assignment granularity ($x_{isg}$) |
| `optimization_recommendations` | `skill_category` | $k$ | Records skill category matching ($y_{vikt}$) |
| `optimization_recommendations` | `shift_id` | $t$ | Records operational shift period |
| `optimization_recommendations` | `transit_time_minutes` | $\tau_{vi}, \tau_{is}$ | Records estimated route transit duration |
| `optimization_recommendations` | `transit_distance_km` | $dist(v, i), dist(i, s)$ | Records estimated route transit distance |

---

## D. Medical-Task Penalty Decision ($\lambda_1 / \lambda_2$)

During Phase 5F-A formulation review, an ambiguity was identified in the volunteer optimization objective function:

$$\min \quad \dots + \lambda_1 \sum_{i, k, t} u_{ikt} + \lambda_2 \sum_{i, t} u_{i, \text{MEDICAL}, t} + \dots$$

Specifically, whether medical unmet tasks should be:
- **Case A (Disjoint):** Excluded from the first term ($\sum_{k \ne \text{MEDICAL}} u_{ikt}$) so that $\lambda_1 = 1,000$ applies to general tasks and $\lambda_2 = 1,500$ applies to medical tasks.
- **Case B (Additive / Hierarchical Surcharge):** Included in both terms ($\lambda_1 \sum_{\text{all } k} u_{ikt} + \lambda_2 \sum_{k=\text{MEDICAL}} u_{ikt}$) so that medical tasks incur an effective penalty of $\lambda_1 + \lambda_2 = 1,000 + 1,500 = 2,500$.

### Decision & Rationale:
**Case B (Additive Hierarchical Surcharge) is the approved design.**
1. **Operational Rationale:** In life-safety emergency response, uncovered medical tasks have catastrophic implications relative to administrative or logistics tasks. An effective penalty of $2,500$ establishes a $2.5\times$ penalty dominance over general unmet tasks ($1,000$).
2. **Formulation Elegance:** Summing across all $k \in \mathcal{K}$ for the base unmet demand term maintains structural symmetry with the capacity constraints, while the second term serves as an explicit priority surcharge:
   $$\text{Penalty}_{\text{unmet}} = \sum_{i, k, t} \lambda(k) \cdot u_{ikt}, \quad \text{where } \lambda(k) = \begin{cases} \lambda_1 + \lambda_2 = 2,500 & \text{if } k \in \mathcal{K}_{\text{MEDICAL}} \\ \lambda_1 = 1,000 & \text{if } k \notin \mathcal{K}_{\text{MEDICAL}} \end{cases}$$
3. **Documentation Alignment:** Both `docs/PHASE5F_OBJECTIVE_DESIGN.md` (Section 3.3) and `docs/PHASE5F_RESEARCH_REPORT.md` (Section 10) have been updated to explicitly specify this additive hierarchical formulation.

---

## E. Migration Verification

### Alembic Migration Architecture
- **Script:** `backend/alembic/versions/phase5f_schema_extensions.py`
- **Revision Identifier:** `phase5f_schema_ext`
- **Down Revision:** `phase5b_schema_ext`
- **Operations:**
  - Upgrades `shelters`: adds `accessibility_features`, `power_available`, `sanitation_available`, `disaster_compatibility`, `last_verified_at`.
  - Upgrades `volunteer_profiles`: adds `max_shift_hours`, `max_travel_time_mins`, `shift_availability`.
  - Upgrades `incidents`: adds `required_skills`, `evacuation_demographics`.
  - Upgrades `optimization_runs`: adds `graph_version`.
  - Upgrades `optimization_recommendations`: adds `demographic_group`, `skill_category`, `shift_id`, `transit_time_minutes`, `transit_distance_km` with indexes on `demographic_group` and `skill_category`.
  - Downgrades: Drops all added columns and indexes in reverse topological order.

### SQLite & Test Environment Compatibility
- Unit and integration tests run against an in-memory SQLite database (`sqlite:///:memory:`).
- SQLite does not natively support Postgres JSONB, Enums, or certain `ALTER TABLE` operations. The SQLAlchemy model definitions use standard `sa.JSON` and `sa.Boolean`, which compile to SQLite `TEXT` (JSON-encoded) and `INTEGER (0/1)` cleanly.
- Test `test_5f_12_alembic_migration_graph` verifies the Alembic revision script, down_revision chain, and callable functions programmatically without relying on SQLite DDL alter limitations.

---

## F. Test Results

### 1. Phase 5F-B Dedicated Schema Test Suite
Command: `pytest tests/backend/test_phase5f_schema.py -q`
- `test_5f_01_shelter_model_extensions`: **PASSED** (all 5 new columns, defaults, nullable constraints)
- `test_5f_02_volunteer_profile_model_extensions`: **PASSED** (fatigue and transit columns, JSON list defaults)
- `test_5f_03_incident_model_extensions`: **PASSED** (skill requirements and demographic breakdown columns)
- `test_5f_04_optimization_model_extensions`: **PASSED** (graph version, demographic/skill/shift columns)
- `test_5f_05_shelter_pydantic_schemas`: **PASSED** (validation, serialization, remaining_capacity property)
- `test_5f_06_volunteer_pydantic_schemas`: **PASSED** (response validation and defaults)
- `test_5f_07_incident_pydantic_schemas`: **PASSED** (demographic group structure and skill demand validation)
- `test_5f_08_optimization_pydantic_schemas`: **PASSED** (recommendation and run schema validation)
- `test_5f_09_database_crud_shelter_lifecycle`: **PASSED** (full DB insert, query, update lifecycle)
- `test_5f_10_database_crud_volunteer_lifecycle`: **PASSED** (full DB profile lifecycle)
- `test_5f_11_database_crud_incident_demographics`: **PASSED** (JSON persistence and extraction)
- `test_5f_12_alembic_migration_graph`: **PASSED** (migration metadata, revision chain, upgrade/downgrade callables)
**Total Phase 5F-B Tests: 12 / 12 PASSED (100%)**

### 2. Regression Test Results
- Phase 5C Graph Engine (`tests/backend/test_phase5c_graph.py`): **12 / 12 PASSED**
- Phase 5D Multi-Commodity Allocation (`tests/backend/test_phase5d_allocation.py`): **18 / 18 PASSED**
- Phase 5E Vehicle Routing Engine (`tests/backend/test_phase5e_routing.py`): **19 / 19 PASSED**
**Subtotal Frozen Optimization Suite: 49 / 49 PASSED (100%)**

### 3. Full Backend Test Suite
Command: `pytest tests/backend/ -q`
- Total Tests Executed: **156**
- Total Tests Passed: **156** (144 existing + 12 new)
- Total Tests Failed: **0**
- Test Execution Status: **100% PASS**

---

## G. Regression Status

Phase 4, Phase 5A, Phase 5B, Phase 5C, Phase 5D, and Phase 5E behavior is **100% UNCHANGED**.
- All Phase 5C Dijkstra/A* graph distance matrices compute identical edge weights.
- All Phase 5D multi-commodity allocation CP-SAT solves yield identical objective values and allocations.
- All Phase 5E OR-Tools routing vehicle schedules and impassable-arc exclusions function identically.
- No existing API endpoints or models suffered backward-incompatible changes; all new columns are nullable or have sensible default values.

---

## H. Known Limitations

1. **Synthetic Validation Data Only:** All test fixtures utilize synthetic benchmark disaster scenarios and simulated Chennai coordinates. No live emergency management data or operational dispatch data is used.
2. **Schema Foundation Only:** This phase provides exclusively the database models, Pydantic schemas, and data structures. No solver logic, shelter assignment math, or volunteer assignment CP-SAT models are active in this phase.
3. **SQLite Test Environment:** In-memory SQLite tests serialize JSON columns as JSON strings. Full production deployment will use PostgreSQL JSONB columns with GIN indexes as configured in Alembic.

---

## I. Implementation Status

**Status:** `IMPLEMENTED — AWAITING FORENSIC AUDIT`

*(Notice: Phase 5F-B is NOT marked as APPROVED or FROZEN. Work stops here awaiting external forensic audit and explicit human authorization before Phase 5F-C optimization engine implementation).*
