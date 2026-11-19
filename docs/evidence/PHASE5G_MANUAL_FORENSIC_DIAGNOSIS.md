# DIRS — PHASE 5G: FORENSIC DIAGNOSIS REPORT
## MANUAL ACCEPTANCE TESTING EVALUATION (GATE 6 ACCEPTANCE AUDIT)

**Document Version:** 1.0.0  
**Date:** September 2026  
**Auditor:** Antigravity Autonomous Verification & Forensic Diagnostic Engine  
**Scope:** Phase 5G Advanced GIS / Disaster Simulation / Response Intelligence  
**Mode:** FORENSIC DIAGNOSTIC ONLY — NO CODE OR DATA MODIFIED  
**Final Gate Recommendation:** **NOT READY (REMEDIATION REQUIRED BEFORE RE-TEST)**  

---

## 1. EXECUTIVE SUMMARY

During manual black-box acceptance testing of Phase 5G, 10 distinct operational behaviors and potential anomalies were observed across scenarios 6E through 6K. This forensic investigation conducted a read-only, end-to-end data-flow trace through the simulation router, scenario engine, response simulator, comparison engine, and the underlying frozen Phase 5F-E optimization stack.

### Key Conclusions:
1. **Confirmed Bug 1 (P1 — Major Defect): Demographic Multiplier Rounding Invariant Violation in Scenario Engine.**  
   In [`backend/app/ai/simulation/scenario_engine.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/scenario_engine.py#L410-L425), when `severity_multiplier != 1.0` (in Gate 6I and 6K, `severity_multiplier = 1.2`), `apply_scenario()` scales `people_affected` and demographic subgroups (`GEN`, `ACC`, `MED`) independently using `math.ceil()`. This breaks the demographic sum invariant $\sum_g \text{demo}[g] = \text{people\_affected}$ (e.g. $78 + 15 + 10 = 103 > 102$). The Phase 5F-C CP-SAT shelter solver correctly detects this inconsistency and raises an exception. The orchestrator returns early in $0.12\text{ ms}$ with `overall_status = "VALIDATION_FAILED"`, leaving all module outputs `None`, which `ResponseSimulator.compute_response_delta()` converts to zeroes across all metrics.
2. **Confirmed Bug 2 (P2 — Correctness Defect): Route Disruption Key Comparison on Ephemeral UUIDs.**  
   In [`backend/app/ai/simulation/response_simulator.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/response_simulator.py#L312-L317), `compute_response_delta()` checks for disrupted routes by indexing `base.routing_result.routes` by `route_id`. However, in frozen Phase 5E ([`routing.py:650`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/optimization/routing.py#L650)), each route is assigned an ephemeral random UUID (`route_id = str(uuid.uuid4())`). Because random UUIDs never match across separate solver runs, the lookup `r_id not in scen_route_stops` unconditionally evaluates to `True`, falsely reporting all baseline routes (2 in DIRS-10) as "disrupted by scenario blockages" on every scenario where the routing solver completes.
3. **Findings 3, 4, 5, 7, and 8 Are Proven EXPECTED BEHAVIORS (NOT Bugs):**  
   - In Finding 3 & 4, `VEH_INT_001` was already an unassigned, idle spare vehicle in the baseline plan (DIRS-10 only requires `VEH_INT_002` and `VEH_INT_006`); disabling an unused vehicle correctly produces zero operational delta.
   - In Finding 5, `DIRS-10` has 3,300 total shelter capacity for 1,695 evacuees (1,605 spare capacity); capping `SHELTER_INT_002` at 10 evacuees caused the CP-SAT solver to strictly restrict it to 10 and reallocate the remaining 490 evacuees to Shelters 1, 4, and 5 with zero unmet evacuees.
   - In Finding 7, road closure `(NODE_0012, NODE_0020)` rerouted 28 evacuees in Phase 5F-C, which dynamically shifted downstream commodity demands in Phase 5D (+2.0 allocation) and enabled 1 additional volunteer assignment in Phase 5F-D (-1 unmet task), verifying cross-module integration.
   - In Finding 8, Depots 2 & 3 had over 68,000 L of water surplus; cutting Depot 1 water to 5,000 L was completely absorbed by Depot 3 (+18,885 L) with zero unmet demand.
4. **State Immutability (Finding 10) Is 100% Preserved:**  
   `base_state_hash` remained identical (`2244f325d25a4799f62a2e8364f9cb00c8cda53bc85a8929339f34304f66ae93`) across all 12 manual acceptance runs.

---

## 2. MANUAL TEST EVIDENCE RECORD

The empirical evidence captured from the database table `simulation_runs` and live execution records is summarized below:

| Run ID | Scenario ID | Scenario Name | Status | Feasibility | Scenario Opt Time | Delta Sheltered | Delta Allocated | Delta Vehicles | Delta Volunteers | Disrupted Routes |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `SIM_840119ea` | `SCEN_2e98fa3f` | Gate 6I - New Incident Surge | `PROPOSED` | `INFEASIBLE` | **0.78 ms** | -1695 (to 0) | -30050.0 (to 0) | -2 (to 0) | -25 (to 0) | 0 |
| `SIM_478bc56b` | `SCEN_58e0a915` | Gate 6K - Combined Cascading | `PROPOSED` | `INFEASIBLE` | **0.54 ms** | -1695 (to 0) | -30050.0 (to 0) | -2 (to 0) | -25 (to 0) | 0 |
| `SIM_58fce25f` | `SCEN_3a099eef` | Gate 6G - Vehicle Loss | `PROPOSED` | `PARTIALLY_FEASIBLE` | 125.01 ms | 0 | 0.0 | 0 | 0 | **2** |
| `SIM_d010f605` | `SCEN_edd7e600` | Gate 6J - Vehicle + Volunteer | `PROPOSED` | `PARTIALLY_FEASIBLE` | 115.37 ms | 0 | 0.0 | 0 | -1 | **2** |
| `SIM_ccc2683a` | `SCEN_4139a1d1` | Gate 6H - Volunteer Shortfall | `PROPOSED` | `PARTIALLY_FEASIBLE` | 117.96 ms | 0 | 0.0 | 0 | -1 | **2** |
| `SIM_5ac3d4d4` | `SCEN_05356067` | Gate 6E - Road Closure | `PROPOSED` | `PARTIALLY_FEASIBLE` | 134.12 ms | 0 | **+2.0** | 0 | **-1** | **2** |
| `SIM_77b31122` | `SCEN_64da5f46` | Gate 6F - Depot Supply Reduction | `PROPOSED` | `PARTIALLY_FEASIBLE` | 128.45 ms | 0 | 0.0 | 0 | 0 | **2** |
| `SIM_e13a9681` | `SCEN_f89d5df4` | Gate 6D - Shelter Capacity Stress | `PROPOSED` | `PARTIALLY_FEASIBLE` | 131.02 ms | 0 | 0.0 | 0 | 0 | **2** |

---

## 3. FINDING-BY-FINDING ANALYSIS

### FINDING 1: Gate 6I (New Incident Surge) Total Metric Collapse
- **Observation:** Scenario with one additional incident resulted in `sheltered: 1695 -> 0`, `resources: 30050 -> 0`, `vehicles: 2 -> 0`, `volunteers: 25 -> 0`, and `scenario optimization time: 0.78 ms`.
- **Classification:** **CONFIRMED BUG (P1)**
- **Trace & Proof:**
  1. In `SCEN_2e98fa3f`, `severity_multiplier = 1.2` was passed.
  2. [`scenario_engine.py:410-425`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/scenario_engine.py#L410-L425) executes:
     ```python
     if scenario.severity_multiplier != 1.0:
         for inc in scenario_state.incidents:
             inc.people_affected = int(math.ceil((inc.people_affected or 50) * scenario.severity_multiplier))
             inc.vulnerable_count = int(math.ceil((inc.vulnerable_count or 10) * scenario.severity_multiplier))
             inc.injuries = int(math.ceil((inc.injuries or 5) * scenario.severity_multiplier))
             if getattr(inc, 'evacuation_demographics', None):
                 for g in inc.evacuation_demographics:
                     inc.evacuation_demographics[g] = int(
                         math.ceil(inc.evacuation_demographics[g] * scenario.severity_multiplier)
                     )
     ```
  3. For incident `INC_INT_001`, base values are `people_affected = 85`, `GEN = 65`, `ACC = 12`, `MED = 8`.
     - Scaled `people_affected` = $\lceil 85 \times 1.2 \rceil = 102$.
     - Scaled `GEN` = $\lceil 65 \times 1.2 \rceil = 78$.
     - Scaled `ACC` = $\lceil 12 \times 1.2 \rceil = 15$.
     - Scaled `MED` = $\lceil 8 \times 1.2 \rceil = 10$.
     - Sum of scaled demographics = $78 + 15 + 10 = \mathbf{103}$.
  4. The sum ($103$) exceeds `people_affected` ($102$) by 1.
  5. In Step 2 of the pipeline ([`orchestrator.py:570-589`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/optimization/orchestrator.py#L570-L589)), Phase 5F-C CP-SAT solver verifies demographic consistency and immediately aborts:
     `SHELTER_OPTIMIZATION_FAILED: Inconsistent demographic total for incident INC_INT_001: sum (103) exceeds people_affected (102)`
  6. The orchestrator returns in $0.12\text{ ms}$ with `overall_status = "VALIDATION_FAILED"` and all result structures `None`.
  7. In [`response_simulator.py:270-300`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/response_simulator.py#L270-L300), null results default to `0`, producing deltas of `-1695`, `-30050.0`, `-2`, `-25`.
- **Verdict:** The incident collection was NOT replaced or lost. The new incident was correctly appended, but the demographic ceiling math broke Phase 5F-C solver input validation.

---

### FINDING 2: Gate 6K (Combined Cascading Crisis) Optimization Collapse
- **Observation:** Scenario 6K also collapsed all metrics to 0 in $0.54\text{ ms}$ despite graph version updating.
- **Classification:** **CONFIRMED BUG (P1)**
- **Trace & Proof:**
  1. `SCEN_58e0a915` contained the exact same `severity_multiplier = 1.2`.
  2. The graph blockage was correctly applied (`apply_blockage` updated graph version from `4baeb6502b565708` to `621cf0a47a5d3099`).
  3. However, before routing or network analysis could evaluate the blockage, Step 2 (Shelter Optimization) crashed on the same demographic ceiling mismatch for `INC_INT_001` (`103 > 102`).
  4. The pipeline aborted at Step 2 in $0.54\text{ ms}$.

---

### FINDING 3: Gate 6G (Vehicle Loss) Vehicle Count Invariance
- **Observation:** `vehicle_availability_changes: ["VEH_INT_001"]` resulted in `vehicles: 2 -> 2`, `distance: 98.58 -> 98.58`, `unrouted: 2 -> 2`.
- **Classification:** **EXPECTED BEHAVIOR (NOT A BUG)**
- **Trace & Proof:**
  1. In `DIRS-10`, there are 10 vehicles (`VEH_INT_001` through `VEH_INT_010`) stationed across 3 depots.
  2. The base allocation creates 4 delivery shipments. The OR-Tools vehicle routing solver in Phase 5E uses the objective $\min Z = \beta_1 \cdot \text{late} + \beta_2 \cdot \text{time} + \beta_3 \cdot \text{dist} + \beta_4 \cdot \text{vehicles}$ ($\beta_4 = 100$).
  3. The optimal baseline solution selects exactly **2 vehicles**:
     - `VEH_INT_002` (DISP-002 from Depot 2): 1 stop, $54.14\text{ km}$
     - `VEH_INT_006` (DISP-006 from Depot 3): 1 stop, $44.44\text{ km}$
  4. `VEH_INT_001` is stationed at Depot 1 and is **IDLE / UNASSIGNED** in the baseline solution.
  5. [`scenario_engine.py:516-527`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/scenario_engine.py#L516-L527) correctly marks `VEH_INT_001.status = 'UNAVAILABLE'`.
  6. [`routing.py:359`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/optimization/routing.py#L359) filters `eligible_vehicles = [v for v in vehicles if v.status == "AVAILABLE"]`.
  7. `VEH_INT_001` is excluded from the eligible pool. The remaining 9 available vehicles still include `VEH_INT_002` and `VEH_INT_006`.
  8. The solver produces the exact same optimal route dispatch using `VEH_INT_002` and `VEH_INT_006`.
  9. **Verification Experiment:** When an active vehicle (`VEH_INT_002`) is disabled, the solver immediately adapts:
     `Base vehicles: 2 -> Scen vehicles: 1; Base dist: 98.58 -> Scen dist: 44.44 km`.
  10. Removing an unused vehicle having zero effect is mathematically optimal and correct.

---

### FINDING 4: Gate 6J (Vehicle + Volunteer Combined) Hash Identity
- **Observation:** Scenario 6J (`VEH_INT_001` + `VOL_INT_0002`) produced result hash `fadda37c74f16418...`, identical to Scenario 6H (`VOL_INT_0002` only).
- **Classification:** **EXPECTED BEHAVIOR (NOT A BUG)**
- **Trace & Proof:**
  1. As proven in Finding 3, removing `VEH_INT_001` produces $\Delta \text{Vehicles} = 0, \Delta \text{Distance} = 0, \Delta \text{Response} = 0, \Delta \text{Unrouted} = 0$.
  2. The volunteer loss of `VOL_INT_0002` is active, producing $\Delta \text{Deployed} = -1, \Delta \text{Unmet} = +1, \Delta \text{Medical} = +1$.
  3. The resulting metric delta vector for Scenario 6J is bit-for-bit identical to Scenario 6H.
  4. The result hash is computed deterministically via `ResponseSimulator._compute_result_hash(delta, graph_version)`.
  5. Because the inputs to the hash function (the response deltas and graph version) are identical, the SHA-256 result hash is identical.

---

### FINDING 5: Gate 6D (Shelter Capacity Reduction) Evacuees Invariance
- **Observation:** Reducing `SHELTER_INT_002` capacity to 10 resulted in `sheltered: 1695 -> 1695, unmet: 0 -> 0`.
- **Classification:** **EXPECTED BEHAVIOR (NOT A BUG)**
- **Trace & Proof:**
  1. In `DIRS-10`, the 5 shelters have total capacity:
     `SHELTER_INT_001` (800) + `SHELTER_INT_002` (500) + `SHELTER_INT_003` (500) + `SHELTER_INT_004` (1200) + `SHELTER_INT_005` (300) = **3,300 total capacity**.
  2. Total evacuee demand across all 10 incidents is **1,695**.
  3. There is **1,605 units of excess shelter capacity** across the network.
  4. In the baseline plan:
     - `SHELTER_INT_002`: cap=500, hosted=500, remaining=0
     - `SHELTER_INT_004`: cap=1200, hosted=759, remaining=**441**
     - `SHELTER_INT_005`: cap=300, hosted=259, remaining=**41**
     - `SHELTER_INT_001`: cap=800, hosted=177, remaining=**623**
     - `SHELTER_INT_003`: cap=500, hosted=0, remaining=**500**
  5. In [`scenario_engine.py:475-484`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/scenario_engine.py#L475-L484), passing `10.0` (> 1.0) sets `s.total_capacity = 10`.
  6. In the scenario run, the CP-SAT shelter solver strictly respects the new cap:
     - `SHELTER_INT_002`: **cap=10, assigned=10, remaining=0** (Capacity restriction fully enforced).
     - `SHELTER_INT_004`: assigned increased from 759 to **1200** (+441).
     - `SHELTER_INT_005`: assigned increased from 259 to **300** (+41).
     - `SHELTER_INT_001`: assigned increased from 177 to **185** (+8).
  7. All 490 displaced evacuees were absorbed by Shelters 4, 5, and 1.
  8. Total sheltered remains 1,695 with 0 unmet.

---

### FINDING 6: Repeated False Route-Blockage Reporting
- **Observation:** Scenarios 6F, 6G, 6H, and 6J (which had ZERO road blockages) all reported `"2 delivery route(s) were disrupted by scenario blockages."` Meanwhile, Scenarios 6I and 6K reported `[]`.
- **Classification:** **CONFIRMED BUG (P2)**
- **Trace & Proof:**
  1. In [`backend/app/ai/simulation/response_simulator.py:311-317`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/response_simulator.py#L311-L317):
     ```python
     disrupted_routes = []
     if base.routing_result and scenario.routing_result:
         base_route_stops = {r.route_id: [s.incident_id for s in r.stops] for r in base.routing_result.routes}
         scen_route_stops = {r.route_id: [s.incident_id for s in r.stops] for r in scenario.routing_result.routes}
         for r_id, stops in base_route_stops.items():
             if r_id not in scen_route_stops or scen_route_stops[r_id] != stops:
                 disrupted_routes.append(r_id)
     ```
  2. In frozen Phase 5E [`backend/app/ai/optimization/routing.py:650`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/optimization/routing.py#L650):
     ```python
     routes.append(VehicleRoute(
         route_id=str(uuid.uuid4()),
         vehicle_id=vehicle.vehicle_id,
         ...
     ))
     ```
  3. Every execution of `routing_engine.solve()` creates fresh random UUIDs for `route_id`.
  4. The base response has route IDs e.g. `['d7018dbe-...', 'a6a44fd1-...']`.
  5. The scenario response has route IDs e.g. `['bd0e89e6-...', 'f8e82e6c-...']`.
  6. The test `if r_id not in scen_route_stops` unconditionally succeeds for every route in the baseline plan!
  7. Because `DIRS-10` generates 2 routes, `disrupted_routes` always contains exactly 2 route IDs.
  8. In [`comparison_engine.py:34`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/comparison_engine.py#L34):
     `if delta.new_disrupted_routes: observations.append(f"{len(delta.new_disrupted_routes)} delivery route(s) were disrupted by scenario blockages.")`
     This produces the false alert banner.
  9. Why did Scenarios 6I and 6K report `[]`? Because their shelter optimization crashed (Finding 1), leaving `scenario.routing_result = None`, causing `if base.routing_result and scenario.routing_result:` to evaluate to `False` and skip route evaluation entirely.

---

### FINDING 7: Gate 6E (Road Closure) Secondary Downstream Propagation
- **Observation:** Road closure on `(NODE_0012, NODE_0020)` did not change vehicle routing distance (98.58 km), but caused `resource_allocated: +2.0` and `volunteer_unmet: -1`.
- **Classification:** **EXPECTED BEHAVIOR (NOT A BUG)**
- **Trace & Proof:**
  1. Edge `(NODE_0012, NODE_0020)` is an open road segment of length $3.94\text{ km}$ ($5.25\text{ min}$).
  2. Marking it `IMPASSABLE` updates the graph version to `621cf0a47a5d3099`.
  3. In Step 2 (Phase 5F-C Shelter Evacuation CP-SAT), travel times between incidents and shelters change due to network path re-computation.
  4. As a result, 28 evacuees who evacuated to `SHELTER_INT_005` in the baseline plan were rerouted to `SHELTER_INT_004` (Shelter 4 hosted: $759 \to 787$, Shelter 5 hosted: $259 \to 231$).
  5. In Step 3, `convert_shelter_output_to_resource_demands()` computes commodity demands at shelters based on hosted population.
  6. In Step 4, the Phase 5D HiGHS LP solver allocates commodities from the 3 depots to meet the new shelter demand distribution. Because transportation distance/cost trade-offs changed, total allocated resource quantity shifted by $+2.0$ units ($30,050.0 \to 30,052.0$).
  7. In Step 6, the Phase 5F-D CP-SAT volunteer solver matches volunteers to tasks. The shifted task distribution allowed 1 additional volunteer to be matched, reducing `unmet_tasks` from 62 to 61 ($-1$).
  8. In Step 5, the 4 delivery shipments happened not to traverse `(NODE_0012, NODE_0020)`, so route distance remained $98.58\text{ km}$.
  9. This confirms true end-to-end multi-module coupling.

---

### FINDING 8: Gate 6F (Depot Supply Reduction) Inventory Shift
- **Observation:** Reducing `DEPOT_INT_001` supplies (Water: 5000, Medical Kits: 100) resulted in resources remaining at 30,050.0.
- **Classification:** **EXPECTED BEHAVIOR (NOT A BUG)**
- **Trace & Proof:**
  1. In the baseline solution:
     - `DEPOT_INT_001` supplied 18,885.0 L of Water and 135 Medical Kits.
     - `DEPOT_INT_002` supplied 3,885.0 L of Water.
     - `DEPOT_INT_003` supplied 2,655.0 L of Water.
     Total Water demanded = $25,425.0\text{ L}$.
  2. `DEPOT_INT_002` has $28,630.0\text{ L}$ in stock, and `DEPOT_INT_003` has $39,954.0\text{ L}$ in stock.
  3. When `DEPOT_INT_001` was restricted to 5,000 L, the Phase 5D LP solver shifted the remaining 13,885 L demand to `DEPOT_INT_003`:
     - Water from `DEPOT_INT_003` jumped from $2,655.0 \to \mathbf{21,540.0\text{ L}}$.
     - Food from `DEPOT_INT_003` jumped from $443.0 \to \mathbf{3,591.0\text{ units}}$.
     - Medical kits from `DEPOT_INT_003` jumped from $29.0 \to \mathbf{164.0\text{ kits}}$.
  4. Total demand was 100% fulfilled without deficit.
  5. The reported "2 disrupted routes" was solely due to the Finding 6 UUID bug.

---

### FINDING 9: Gate 6 API Contract (`name` Required)
- **Observation:** Omitting `name` on `POST /api/v1/simulation/run` returned `422 Field required: name`.
- **Classification:** **EXPECTED CONTRACT (NOT A BUG)**
- **Trace & Proof:**
  1. [`backend/app/schemas/simulation.py:8`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/schemas/simulation.py#L8) defines:
     `name: str = Field(..., min_length=3, max_length=100)`
  2. In Pydantic V2, `Field(...)` designates an obligatory field.
  3. OpenAPI schema generated at `/openapi.json` explicitly lists `required: ['name']`.
  4. All simulation scenarios must be named for audit logging in `simulation_scenarios.name` and UI presentation.

---

### FINDING 10: Non-Mutation & State Immutability
- **Observation:** `base_state_hash` remained `2244f325d25a4799f62a2e8364f9cb00c8cda53bc85a8929339f34304f66ae93` across all 12 manual runs.
- **Classification:** **CONFIRMED WORKING AS DESIGNED**
- **Trace & Proof:**
  1. Base state is constructed via `_load_base_state()` from deterministic benchmark factories.
  2. Prior to perturbation, `ScenarioEngine.clone_base_state()` executes `copy.deepcopy()` across incidents, shelters, depots, vehicles, volunteers, and the NetworkX graph.
  3. Perturbations are applied exclusively to the cloned instance.
  4. No write operations occur on core operational tables (`incidents`, `shelters`, etc.).
  5. SHA-256 state invariance is 100% maintained.

---

## 4. EXACT DATA FLOW TRACES

### Flow 1: Demographic Multiplier Invariant Violation (Finding 1 & 2)
```
User Request: POST /api/v1/simulation/scenarios { severity_multiplier: 1.2, new_incidents: [...] }
  │
  ▼
[1] backend/app/routers/simulation.py: create_scenario()
    └── Persists SimulationScenario with severity_multiplier = 1.2
  │
  ▼
[2] backend/app/routers/simulation.py: run_simulation()
    └── Instantiates DisasterScenario(severity_multiplier=1.2, ...)
  │
  ▼
[3] backend/app/ai/simulation/scenario_engine.py: apply_scenario() [Line 410]
    ├── inc.people_affected = math.ceil(85 * 1.2) = 102
    ├── inc.evacuation_demographics['GEN'] = math.ceil(65 * 1.2) = 78
    ├── inc.evacuation_demographics['ACC'] = math.ceil(12 * 1.2) = 15
    ├── inc.evacuation_demographics['MED'] = math.ceil(8 * 1.2)  = 10
    └── Invariant Violated: 78 + 15 + 10 = 103 != 102  <--- ROOT CAUSE
  │
  ▼
[4] backend/app/ai/optimization/orchestrator.py: run_pipeline() [Line 571]
    └── Calls self.shelter_engine.solve(incidents=shelter_inputs, ...)
  │
  ▼
[5] backend/app/ai/optimization/shelter.py: solve()
    └── Checks: sum(demo.values()) <= inc.people_affected
        └── RAISES ValueError("Inconsistent demographic total for incident INC_INT_001: sum (103) exceeds people_affected (102)")
  │
  ▼
[6] backend/app/ai/optimization/orchestrator.py: [Line 580]
    └── Catches Exception -> Returns IntegratedOptimizationResult(overall_status="VALIDATION_FAILED", shelter_result=None, ...)
  │
  ▼
[7] backend/app/ai/simulation/response_simulator.py: compute_response_delta() [Line 270]
    └── Null results default to 0 -> Delta evaluates to -1695, -30050.0, -2, -25
```

### Flow 2: Ephemeral UUID Route Disruption Anomaly (Finding 6)
```
[1] Base Pipeline Execution:
    └── routing_engine.solve() [routing.py:650]
        └── VehicleRoute(route_id = str(uuid.uuid4()))  --> Generates UUID_A, UUID_B

[2] Scenario Pipeline Execution:
    └── routing_engine.solve() [routing.py:650]
        └── VehicleRoute(route_id = str(uuid.uuid4()))  --> Generates UUID_C, UUID_D

[3] Delta Evaluation in response_simulator.py: [Line 312]
    ├── base_route_stops = { UUID_A: [...], UUID_B: [...] }
    ├── scen_route_stops = { UUID_C: [...], UUID_D: [...] }
    └── for r_id in [UUID_A, UUID_B]:
            if r_id not in scen_route_stops:  <--- ALWAYS TRUE (UUID_A is never in [UUID_C, UUID_D])
                disrupted_routes.append(r_id)  <--- ROOT CAUSE

[4] Comparison & Alerting in comparison_engine.py: [Line 34]
    └── Emits: "2 delivery route(s) were disrupted by scenario blockages." (even with zero blockages!)
```

---

## 5. ROOT CAUSE FOR EACH CONFIRMED FINDING

| Finding # | Category | Responsible File & Line | Exact Root Cause |
| :---: | :---: | :--- | :--- |
| **Finding 1** | **CONFIRMED BUG** | [`backend/app/ai/simulation/scenario_engine.py:410-425`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/scenario_engine.py#L410-L425) | Independent `math.ceil()` scaling on `people_affected` and each demographic bucket breaks the mathematical partition invariant $\sum_g \text{demo}[g] = \text{people\_affected}$. Phase 5F-C CP-SAT input validation rejects the input, aborting the pipeline in Step 2. |
| **Finding 2** | **CONFIRMED BUG** | [`backend/app/ai/simulation/scenario_engine.py:410-425`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/scenario_engine.py#L410-L425) | Identical root cause to Finding 1. Scenario 6K also set `severity_multiplier = 1.2`, triggering the same demographic sum error and aborting before evaluating road blockages or fleet loss. |
| **Finding 6** | **CONFIRMED BUG** | [`backend/app/ai/simulation/response_simulator.py:313-317`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/response_simulator.py#L313-L317) | Compares base routes against scenario routes using ephemeral random `route_id = str(uuid.uuid4())` generated on every run by frozen Phase 5E (`routing.py:650`), making `r_id not in scen_route_stops` unconditionally evaluate to `True`. |

---

## 6. FINDINGS THAT ARE PROVEN EXPECTED BEHAVIORS

| Finding # | Observed Phenomenon | Proof of Correctness |
| :---: | :--- | :--- |
| **Finding 3** | Vehicle loss of `VEH_INT_001` caused zero delta | In `DIRS-10`, the base routing plan only requires 2 vehicles (`VEH_INT_002` and `VEH_INT_006`). `VEH_INT_001` was already idle in the baseline solution. Removing an idle vehicle correctly leaves the optimal dispatch of the 2 active vehicles unchanged. Disabling active vehicle `VEH_INT_002` immediately drops vehicle count from 2 to 1 and distance from 98.58 to 44.44 km. |
| **Finding 4** | Vehicle + Volunteer had same hash as Volunteer-only | Because `VEH_INT_001` was idle, the vehicle dimension had zero delta. The only effective perturbation was `VOL_INT_0002`. The resulting delta metric vector was identical to Scenario 6H, so the deterministic SHA-256 result hash was identical. |
| **Finding 5** | Capping `SHELTER_INT_002` at 10 did not increase unmet evacuees | `DIRS-10` total shelter capacity (3,300) exceeds total demand (1,695) by 1,605. When Shelter 2 was restricted to 10 evacuees, the CP-SAT solver strictly capped Shelter 2 at 10/10 and reallocated the remaining 490 evacuees to Shelters 1, 4, and 5 with zero unmet evacuees. |
| **Finding 7** | Road closure caused resource +2.0 and volunteer unmet -1 | Road closure `(NODE_0012, NODE_0020)` changed network travel times, causing Phase 5F-C to reroute 28 evacuees from Shelter 5 to Shelter 4. The shifted shelter demands altered the Phase 5D LP commodity allocation (+2.0) and allowed Phase 5F-D CP-SAT to match 1 additional volunteer (-1 unmet task). |
| **Finding 8** | Depot 1 supply cut caused zero unmet resources | Depots 2 & 3 had 68,584 L of surplus water against total demand of 25,425 L. The Phase 5D LP solver shifted 18,885 L from Depot 1 to Depot 3 without deficit. |
| **Finding 9** | 422 error when `name` omitted | `ScenarioCreateRequest.name` is declared as an obligatory field (`Field(..., min_length=3)`). Rejecting requests without a human-readable name is expected Pydantic V2 validation contract. |
| **Finding 10** | Non-mutation of base state | `base_state_hash` remained `2244f325d25a4799f62a2e8364f9cb00c8cda53bc85a8929339f34304f66ae93` across all 12 runs, proving zero mutation of base/live operational data. |

---

## 7. SEVERITY CLASSIFICATION

- **P1 (Major Functional Defect):**  
  **Finding 1 & Finding 2 — Inconsistent Demographic Partition Multiplier Scaling.**  
  *Impact:* Any what-if scenario executed with a `severity_multiplier != 1.0` crashes the CP-SAT shelter solver input validation, rendering Scenarios A and G completely inoperable through the API.
- **P2 (Correctness / Usability Defect):**  
  **Finding 6 — False Route Disruption Alerts.**  
  *Impact:* Spurious alert banners and incorrect `new_disrupted_routes` metrics displayed on every scenario with active routing, misinforming disaster directors that road blockages occurred when none were present.

---

## 8. FROZEN MODULE INTEGRITY ASSESSMENT

- `backend/app/ai/optimization/graph.py` (Phase 5C): **FROZEN & UNTOUCHED**
- `backend/app/ai/optimization/allocation.py` (Phase 5D): **FROZEN & UNTOUCHED**
- `backend/app/ai/optimization/routing.py` (Phase 5E): **FROZEN & UNTOUCHED**
- `backend/app/ai/optimization/shelter.py` (Phase 5F-C): **FROZEN & UNTOUCHED**
- `backend/app/ai/optimization/volunteer.py` (Phase 5F-D): **FROZEN & UNTOUCHED**
- `backend/app/ai/optimization/orchestrator.py` (Phase 5F-E): **FROZEN & UNTOUCHED**

*Audit Confirmation:* All observed issues reside entirely in Phase 5G code (`scenario_engine.py` and `response_simulator.py`). The frozen mathematical formulations and solvers are functioning with 100% mathematical integrity and require zero alterations.

---

## 9. RECOMMENDED REMEDIATION

*(Descriptive only — per strict instructions, no code has been modified)*

1. **Remedy for Bug 1 & 2 ([`scenario_engine.py:410-425`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/scenario_engine.py#L410-L425)):**  
   Scale demographics proportionally using largest-remainder apportionment (or calculate `GEN = people_affected - ACC - MED - MED_ACC`) to strictly preserve $\sum_g \text{demo}[g] = \text{people\_affected}$ after ceiling `people_affected`:
   ```python
   inc.people_affected = int(math.ceil((inc.people_affected or 50) * scenario.severity_multiplier))
   inc.vulnerable_count = min(inc.people_affected, int(math.ceil((inc.vulnerable_count or 10) * scenario.severity_multiplier)))
   inc.injuries = min(inc.people_affected - inc.vulnerable_count, int(math.ceil((inc.injuries or 5) * scenario.severity_multiplier)))
   if getattr(inc, 'evacuation_demographics', None):
       inc.evacuation_demographics['ACC'] = inc.vulnerable_count
       inc.evacuation_demographics['MED'] = inc.injuries
       inc.evacuation_demographics['MED_ACC'] = 0
       inc.evacuation_demographics['GEN'] = max(0, inc.people_affected - inc.vulnerable_count - inc.injuries)
   ```
2. **Remedy for Bug 2 ([`response_simulator.py:313-317`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/response_simulator.py#L313-L317)):**  
   Compare routes by `vehicle_id` (which is stable across runs) and check whether their stop sequences or travel paths differ, rather than indexing by ephemeral `r.route_id`:
   ```python
   base_routes_by_veh = {r.vehicle_id: [s.incident_id for s in r.stops] for r in base.routing_result.routes}
   scen_routes_by_veh = {r.vehicle_id: [s.incident_id for s in r.stops] for r in scenario.routing_result.routes}
   for v_id, base_stops in base_routes_by_veh.items():
       # Only flag as disrupted if road blockages actually exist AND the vehicle route changed or was canceled
       if scenario.additional_blockages and (v_id not in scen_routes_by_veh or scen_routes_by_veh[v_id] != base_stops):
           disrupted_routes.append(v_id)
   ```
3. **Manual Acceptance Test Payload Guidance:**  
   When testing vehicle loss on `DIRS-10`, select an active dispatched vehicle (`VEH_INT_002` or `VEH_INT_006`) rather than idle spare vehicle `VEH_INT_001` to observe fleet reallocation.

---

## 10. REQUIRED RETEST CASES

Once remediation is authorized and implemented, the following test cases must be executed:
1. `RETEST-5G-01`: Scenario A with `severity_multiplier = 1.2` against `DIRS-10` verifying non-zero optimization result and exact demographic sum equality.
2. `RETEST-5G-02`: Scenario G (Combined Cascading) with `severity_multiplier = 1.2` verifying successful completion of all 4 pipeline stages.
3. `RETEST-5G-03`: Scenarios 6F, 6G, 6H, and 6J (zero road blockages) verifying `new_disrupted_routes == []` and zero false route disruption alert banners.
4. `RETEST-5G-04`: Scenario 6E (Road Closure) verifying `new_disrupted_routes` correctly identifies affected routes traversing blocked links.
5. `RETEST-5G-05`: Vehicle loss of `VEH_INT_002` verifying vehicle reduction ($2 \to 1$) and distance reduction ($98.58 \to 44.44\text{ km}$).

---

## 11. FINAL GATE RECOMMENDATION

**FORENSIC VERDICT:** **NOT READY**

Phase 5G cannot be certified for human acceptance sign-off until the two confirmed bugs (P1 Demographic Scaling Invariant and P2 Ephemeral UUID Route Comparison) are remediated. The remaining 8 findings are verified as mathematically sound, expected behaviors under the Phase 5F-E optimization contracts.
