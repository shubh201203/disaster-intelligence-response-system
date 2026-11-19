# PHASE 5F-A — Comprehensive Research, Data Audit & Mathematical Formulation Report

**System:** Disaster Incident Response System (DIRS)  
**Phase:** 5F-A (Shelter & Volunteer Optimization: Research, Audit & Formulation)  
**Classification:** MASTER RESEARCH & SPECIFICATION REPORT (PRE-IMPLEMENTATION)  
**Status Gate:** `READY FOR IMPLEMENTATION AUTHORIZATION`  
**Date:** 2026-09-22  

---

## 1. Existing System Architecture

DIRS is an enterprise disaster decision-support system structured into layered, modular optimization engines:
- **Phase 3C / Phase 4:** Disaster ingestion, PostGIS spatial queries, computer vision damage verification, and situational clustering.
- **Phase 5A:** Optimization architecture, objective hierarchy, and operational latency targets.
- **Phase 5B:** Relational schema foundation, registering `OptimizationRun`, `OptimizationRecommendation`, `OptimizationOverrideLog`, and structured resource/vehicle entities.
- **Phase 5C:** Networkx/Dijkstra road graph engine, computing deterministic distance and travel-time matrices with dynamic blockage rerouting.
- **Phase 5D:** Multi-Commodity Resource Allocation Engine (OR-Tools CP-SAT), allocating life-saving supplies from depots to incidents under scarcity.
- **Phase 5E:** Capacitated Vehicle Routing & Dynamic Emergency Dispatch Engine (OR-Tools RoutingModel), sequencing multi-stop delivery tours respecting weight/volume capacities, time windows, and hard road blockages.
- **Phase 5F (Current):** Human-centric emergency operations:
  $$\text{Resource Allocation (5D)} \longrightarrow \text{Vehicle Routing (5E)} \longrightarrow \text{Shelter Assignment (5F-1)} + \text{Volunteer Assignment (5F-2)}$$

---

## 2. Existing Data Model Audit

A comprehensive inspection of backend database models reveals substantial foundational reuse:
1. **`User` & `UserRole` (`app/models/user.py`):**
   - Direct reuse of `UserRole.GOVT` for mandatory Human-in-the-Loop authorization.
   - Direct reuse of `UserRole.VOLUNTEER` for responder candidate pools.
2. **`VolunteerProfile` (`app/models/user.py`):**
   - Reused fields: `skills` (JSON array), `skill_category` (`MEDICAL`, `RESCUE`, `LOGISTICS`, `GENERAL`), `assignment_status` (`UNASSIGNED`, `ASSIGNED`, `ON_MISSION`), `experience_years`, `medical_certified`, `verification_status` (`PENDING`, `VERIFIED`, `REJECTED`), `is_available`, `current_lat`, `current_lng`.
3. **`Incident` (`app/models/incident.py`):**
   - Reused fields: `people_affected` (evacuee count), `vulnerable_count` (accessibility demand), `injuries` (medical demand), `priority_level`, `priority_score`, `severity_level`, `disaster_type`, `latitude`, `longitude`.
4. **`Shelter` (`app/models/shelter.py`):**
   - Reused fields: `total_capacity`, `current_occupancy`, `status` (`OPEN`, `FULL`, `CLOSED`), `has_medical`, `has_food`, `has_water`, `disaster_risk_level`, `latitude`, `longitude`.
5. **`OptimizationRun` & `OptimizationRecommendation` (`app/models/optimization.py`):**
   - Reused enums: `recommendation_type` already defines `SHELTER_EVACUATION` and `VOLUNTEER_ASSIGNMENT`. Foreign keys for `shelter_id` and `volunteer_id` already exist.

---

## 3. Missing Entities & Operational Schema Extensions

To formulate mathematically complete models without modifying frozen database tables, missing attributes are encapsulated into Pydantic / dataclass input transfer schemas:
- **For Shelters:**
  - `accessibility_features`: Boolean flag ($A_s$) for wheelchair ramps and specialized ADA sanitation.
  - `power_available`: Boolean flag for generator/grid backup for medical refrigeration.
  - `sanitation_available`: Boolean flag for compliant toilet-to-occupant ratios.
  - `disaster_compatibility`: List[str] of compatible hazard types (e.g., ground-floor flood susceptibility).
  - `last_verified_at`: DateTime of site inspection freshness.
- **For Volunteers:**
  - `max_shift_hours`: Float ceiling (default: $8.0\text{ h}$).
  - `max_travel_time_mins`: Float reachability cutoff (default: $45.0\text{ min}$).
  - `shift_availability`: List[str] of active operational shift IDs.
- **For Incidents:**
  - `required_skills`: Dict[str, int] of required responder roles ($d_{ikt}$).

---

## 4. Shelter Assignment Problem Definition

During major disaster emergencies, displaced populations at active incident locations must be evacuated to safe, equipped emergency shelters.

The problem answers:
> *Given active incidents with displaced populations and specific medical/accessibility needs, and a network of emergency shelters with differing capacities, amenities, and operational statuses, what evacuation assignment minimizes life-safety risk and evacuation travel time while strictly respecting shelter capacities, road reachability, accessibility requirements, and medical compatibility?*

---

## 5. Shelter Assignment Mathematical Formulation

### 5.1 Demographic Partitioning & Conservation
To eliminate demographic double counting, total displaced population $p_i$ is partitioned into mutually exclusive categories:
- $p_{i, \text{MED\_ACC}}$: Evacuees requiring both medical aid and physical accessibility.
- $p_{i, \text{ACC}}$: Evacuees requiring physical accessibility only.
- $p_{i, \text{MED}}$: Evacuees requiring on-site medical aid only.
- $p_{i, \text{GEN}} = p_i - (p_{i, \text{MED\_ACC}} + p_{i, \text{ACC}} + p_{i, \text{MED}})$: General evacuees.

### 5.2 Mathematical Variables & Constraints
- $x_{isg} \in \mathbb{Z}^+$: Evacuees of group $g \in \{\text{GEN}, \text{ACC}, \text{MED}, \text{MED\_ACC}\}$ from incident $i$ assigned to shelter $s$.
- $x_{is} = \sum_{g} x_{isg}$: Total evacuee flow from incident $i$ to shelter $s$.
- $u_{ig} \in \mathbb{Z}^+$: Unassigned evacuee shortfall of group $g$ at incident $i$.
- $u_i = \sum_{g} u_{ig}$: Total unassigned evacuee shortfall at incident $i$.
- $y_s \in \{0, 1\}$: Binary shelter activation indicator.

**Hard Constraints:**
1. **Physical Capacity:** $\sum_{i \in I} \sum_{g \in G} x_{isg} \le C_s \cdot y_s \quad \forall s \in S$, where $C_s = \max(0, K_s - O_s^{\text{curr}})$ if `OPEN`, else $0$.
2. **Exact Demographic Conservation:** $\sum_{s \in S} x_{isg} + u_{ig} = p_{ig} \quad \forall i \in I, \forall g \in G$.
3. **Capability Matching:** $x_{isg} \le p_{ig} \cdot \Omega_{sg} \quad \forall i, s, g$, where $\Omega_{sg}$ enforces accessibility ($A_s$) and medical aid ($M_s$).
4. **Road Reachability:** $x_{isg} \le p_{ig} \cdot R_{is} \quad \forall i, s, g$ ($R_{is} = 0$ on impassable roads).
5. **Activation Bounds:** $x_{is} \le C_s \cdot y_s \quad \forall i, s$ and $y_s \le \sum_i x_{is} \quad \forall s$.

---

## 6. Shelter Assignment Objective Function

$$\min Z_{\text{shelter}} = \sum_{i \in I} \omega_i P_i \cdot \gamma_1 u_{i, \text{GEN}} + \sum_{i \in I} \omega_i P_i \left( \gamma_2 u_{i, \text{ACC}} + \gamma_3 u_{i, \text{MED}} + \gamma_4 u_{i, \text{MED\_ACC}} \right) + \sum_{i \in I} \sum_{s \in S} \left( \gamma_5 t_{is} + \gamma_6 d_{is} \right) x_{is} + \gamma_7 \sum_{s \in S} y_s$$

- **Calibrated Coefficients:** $\gamma_1 = 1,000$, $\gamma_2 = 2,000$, $\gamma_3 = 2,500$, $\gamma_4 = 4,000$, $\gamma_5 = 10$, $\gamma_6 = 1$, $\gamma_7 = 500$.
- **Dominance Proof:** Unassigned penalty for 1 evacuee at a critical incident ($400,000$) dominates maximum 60-min transit cost ($630$) by $> 635 : 1$, mathematically guaranteeing coverage over travel convenience.

---

## 7. Shelter Assignment Baselines

- **Baseline A (Nearest-Feasible Heuristic):** Greedily places evacuees in the closest open shelter with $C_s > 0$.
- **Baseline B (Largest-Remaining-Capacity Heuristic):** Greedily places evacuees in the largest regional shelter to minimize facility count.
- **Baseline C (Priority-First Nearest-Feasible):** Processes incidents in priority score descending order, assigning to nearest feasible shelter.

---

## 8. Volunteer Assignment Problem Definition

During emergency response operations, citizen volunteers and NGO personnel with specialized competencies (first aid, rescue, logistics) mobilize to support ground response.

The problem answers:
> *Given active disaster incidents requiring specific responder skills, and a pool of registered, verified volunteers with varying locations, competencies, and availability, what assignment matches qualified personnel to urgent incident tasks that minimizes response delay and unfilled critical needs while strictly preventing overwork, double-booking, and skill mismatches?*

---

## 9. Volunteer Assignment Mathematical Formulation

### 9.1 Sets, Variables & Parameters
- $v \in V$: Volunteers; $i \in I$: Incidents; $k \in K$: Skills; $t \in T$: Shifts.
- $d_{ikt}$: Demand for skill $k$ at incident $i$ during shift $t$.
- $S_{vk} \in \{0, 1\}$: Verified skill matrix; $E_v \in \{0, 1\}$: Verification status (`VERIFIED`).
- $A_{vt} \in \{0, 1\}$: Shift availability; $W_v^{\max}$: Workload ceiling (default: $8.0\text{ h}$).
- $\tau_{vi}, \delta_{vi}$: Network transit time (min) and distance (km) from Phase 5C.
- Decision variables:
  - $y_{vikt} \in \{0, 1\}$: Binary assignment of volunteer $v$ to task $(i, k)$ in shift $t$.
  - $u_{ikt} \in \mathbb{Z}^+$: Shortfall count of unfilled responder demands.
  - $z_{vt} \in \{0, 1\}$: Binary deployment indicator for volunteer $v$ in shift $t$.

### 9.2 Hard Constraints
1. **Skill Qualification & Verification:** $y_{vikt} \le S_{vk} \cdot E_v \quad \forall v, i, k, t$
2. **Shift Availability:** $y_{vikt} \le A_{vt} \quad \forall v, i, k, t$
3. **No Double-Booking:** $\sum_{i \in I} \sum_{k \in K} y_{vikt} \le 1 \quad \forall v \in V, \forall t \in T$
4. **Reachability & Transit Feasibility:** $y_{vikt} \le R_{vi}$ and $y_{vikt} = 0 \text{ if } \tau_{vi} > \tau_v^{\max}$
5. **Workload Ceiling:** $\sum_{i, k} h_{ikt} \cdot y_{vikt} \le W_v^{\max} \quad \forall v, t$
6. **Task Balance Conservation:** $\sum_{v \in V} y_{vikt} + u_{ikt} = d_{ikt} \quad \forall i, k, t$
7. **Deployment Reification:** $y_{vikt} \le z_{vt}$ and $z_{vt} \le \sum_{i, k} y_{vikt}$.

---

## 10. Volunteer Assignment Objective Function

$$\min Z_{\text{volunteer}} = \sum_{i, k, t} \omega_i P_i \cdot \lambda_1 u_{ikt} + \sum_{i, t} \omega_i P_i \cdot \lambda_2 u_{i, \text{MED}, t} + \sum_{v, i, k, t} (\lambda_3 \tau_{vi} + \lambda_4 \delta_{vi}) y_{vikt} + \lambda_5 \sum_{v, t} z_{vt}$$

- **Calibrated Coefficients:** $\lambda_1 = 1,000$ (baseline unfilled task penalty), $\lambda_2 = 1,500$ (**medical-task unmet penalty**), $\lambda_3 = 10$ (transit minute penalty), $\lambda_4 = 1$ (distance km penalty), $\lambda_5 = 50$ (mobilization setup cost).
- **Hierarchical Weighting Decision:** Unfilled medical tasks are intentionally included in both terms ($\lambda_1 + \lambda_2 = 2,500$), establishing an effective $2.5\times$ life-safety penalty surcharge that strictly prevents prioritizing non-medical tasks over trauma response.
- **Dominance Proof:** Unfilled medical task penalty at a high-priority incident ($562,500$) dominates 45-min transit cost ($470$) by $> 1,190 : 1$.

---

## 11. Volunteer Assignment Baselines

- **Baseline A (Nearest Qualified Available):** Greedily assigns each task to the closest verified qualified volunteer.
- **Baseline B (First-Come First-Served Qualified):** Matches tasks to qualified volunteers ordered by registration timestamp.

---

## 12. Joint vs. Sequential vs. Independent Optimization Analysis

We evaluated three candidate architectures:
1. **Option A (Independent Parallel Solvers):** Shelter engine and volunteer engine run as standalone decoupled modules.
2. **Option B (Sequential Coordinated Pipeline):** Shelter assignment runs first; activated shelters generate secondary on-site volunteer staffing demands, feeding the volunteer assignment engine.
3. **Option C (Joint Monolithic Program):** Single solver program optimizing both simultaneously.

**Technical Recommendation:**
- **Selected: Option B with Option A Fallback.** Provides operational alignment with NDMA protocols, clear modular explainability, and standalone resilience during partial communications outages.
- **Analysis of Option C:** Joint optimization introduces a cross-product of shelter, incident, volunteer, skill, and temporal decision variables, increasing model size and potentially reducing scalability, interpretability, and ease of human override. It is therefore treated as a future research extension rather than part of the initial implementation.

---

## 13. Solver Selection Rationale

- **OR-Tools RoutingModel (`pywrapcp`):** **REJECTED.** Sequence-dependent CVRPTW solver inappropriate for assignment/flow problems without vehicle tours.
- **Pure Min-Cost Network Flow:** **REJECTED.** Inability to natively enforce side constraints (demographic matching, binary facility activation).
- **Hungarian / Kuhn-Munkres:** **REJECTED.** Rigid 1-to-1 assumption fails for generalized task demands ($d_{ikt} > 1$).
- **OR-Tools CP-SAT (`ortools.sat.python.cp_model`):** **SELECTED FOR BOTH MODULES.** Native integer programming, exact Boolean reification for side constraints, and deterministic CDCL search. Proposed performance target: $< 100\text{ ms}$ at standard operational scales ($N \le 25$), to be experimentally validated after implementation.

---

## 14. Phase 5C Graph Engine Integration

- Solvers consume `DistanceTimeMatrix` generated from Phase 5C Dijkstra paths.
- Network integrity is enforced via `graph_version` binding.
- Dynamic road blockages set $R_{is} = 0$ and $R_{vi} = 0$, structurally forbidding transit across impassable edges.

---

## 15. Phase 5E Vehicle Routing Integration

- Shelter assignments generate downstream **Evacuation Transport Requests** ($(i, s, x_{is})$) representing passenger evacuation loads to be executed by municipal bus fleets via Phase 5E.
- Shelter activations generate relief supply demands (food, water) feeding Phase 5D resource distribution and Phase 5E vehicle routing.

---

## 16. Human-In-The-Loop (HITL) Governance & RBAC

- Enforces strict RBAC: Only `UserRole.GOVT` can approve, modify, or reject plans.
- Non-government callers receive `ValueError` / `HTTP 403`.
- Any manual override requires a mandatory `justification_reason` ($\ge 10$ chars) and generates immutable, linked entries in `OptimizationOverrideLog` and `AuditLog`.

---

## 17. Data Provenance & Claim Hygiene

- **Classification:** Strictly **SYNTHETIC-CALIBRATED BENCHMARK DATASET** seeded deterministically (`seed=42`).
- Graph foundation: synthetic-calibrated Chennai/Tamil Nadu disaster-corridor graph using WGS-84 coordinates from Phase 5C.
- Demographic ratios calibrated against SPHERE humanitarian standards and NDMA guidelines.
- **Claim Boundaries:** No live government volunteer tracking, no live municipal GIS integration, no real personal data, and no official municipal deployment claimed.

---

## 18. Adversarial Validation Scenarios (Prospective Test Designs)

The 16 scenarios are prospective test specifications to be verified post-implementation:
- **Shelter Scenarios (S1–S8):** S1 (Sufficient capacity, $\sum u_i = 0$), S2 (Capacity shortfall, explicit unmet), S3 (Nearest shelter full, detour taken), S4 (Closed shelter exclusion), S5 (Accessibility compliance), S6 (Priority competition), S7 (Road blockage rerouting), S8 (Total regional infeasibility).
- **Volunteer Scenarios (V1–V8):** V1 (Full fulfillment), V2 (Severe scarcity, priority tasks filled first), V3 (Skill mismatch exclusion), V4 (Pending verification exclusion), V5 (Availability filtering), V6 (Workload ceiling), V7 (Double-booking prevention), V8 (Transit radius cutoff).

---

## 19. Planned Implementation Benchmark Design

The benchmark configurations are prospective specifications:
- **Shelter Tiers:** `DIRS-SHELTER-10` (10/5), `DIRS-SHELTER-25` (25/10), `DIRS-SHELTER-50` (50/20), `DIRS-SHELTER-100` (100/50).
- **Volunteer Tiers:** `DIRS-VOL-10` (10/25), `DIRS-VOL-25` (25/50), `DIRS-VOL-50` (50/100), `DIRS-VOL-100` (100/250).
- **Timing Decomposition Protocol:**
  $$\text{Total Latency} = \text{Matrix Build} + \text{Model Construction} + \text{Solver Search} + \text{Solution Extraction} + \text{Orchestration Overhead}$$

---

## 20. Operational Risks & Mitigations

1. **Volunteer Last-Minute Dropouts:** Mitigated via `PARTIALLY_FEASIBLE` status, explicit shortfall quantification, and dynamic re-solve triggers upon check-in updates.
2. **Dynamic Shelter Capacity Fluctuations:** Modeled via effective remaining capacity ($C_s = K_s - O_s^{\text{curr}}$) refreshed prior to each run.
3. **Explainability Transparency:** Mitigated via structured explainability payloads (`primary_rationale`, `alternatives_considered`, `unmet_warning`).
4. **Disaster Law Compliance:** Mitigated via strict Government HITL authorization (`UserRole.GOVT` required) and immutable dual-table override auditing.

---

## 21. Phased Implementation Sequence (Pending Authorization)

1. Input Transfer Schemas (`app/schemas/optimization_shelter.py`, `optimization_volunteer.py`).
2. Core CP-SAT Solver Engines (`app/ai/optimization/shelter.py`, `volunteer.py`).
3. Deterministic Benchmark Dataset Generators (`app/ai/optimization/shelter_benchmark_dataset.py`, `volunteer_benchmark_dataset.py`).
4. Government HITL Services & Override Logging (`app/ai/optimization/shelter_service.py`, `volunteer_service.py`).
5. Automated Test Suites (`tests/backend/test_phase5f_shelter.py`, `test_phase5f_volunteer.py`).
6. Forensic Audit Script & Benchmark Execution (`scripts/forensic_phase5f_audit.py`, `scripts/benchmark_phase5f.py`).

---

## 22. Validation Gate Status

### READY FOR IMPLEMENTATION AUTHORIZATION

*Phase 5F-A research, mathematical formulation, data audit, and validation architecture are complete, reconciled, and statically verified. No production code, algorithms, or database migrations will be created until explicit human authorization is granted.*
