# DIRS Phase 5G: Authorized Forensic Remediation Report

**Date:** 2026-09-24  
**Author:** Antigravity AI Engineering Assistant  
**Classification:** SYNTHETIC CALIBRATED SIMULATION / DECISION SUPPORT  
**Status:** COMPLETE — REMEDIATION VERIFIED  
**Final Gate Verdict:** **PASS — READY FOR MANUAL RETEST** *(Phase 5G is NOT frozen; awaiting manual user re-verification)*

---

## 1. Executive Summary

Following the comprehensive read-only forensic diagnosis ([`docs/PHASE5G_MANUAL_FORENSIC_DIAGNOSIS.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE5G_MANUAL_FORENSIC_DIAGNOSIS.md)), authorized remediation was executed targeting **EXACTLY TWO CONFIRMED BUGS**:

1. **BUG 1 (P1) — Demographic Scaling Invariant Violation:**
   - **File:** [`backend/app/ai/simulation/scenario_engine.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/scenario_engine.py) & [`backend/app/routers/simulation.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/routers/simulation.py)
   - **Root Cause:** When `severity_multiplier != 1.0` (such as $1.2\times$ in Gate 6I / 6K), independent `math.ceil()` operations on population and demographic subgroups (`GEN`, `ACC`, `MED`) caused $\sum \text{demo} > \text{people\_affected}$ ($72 + 21 + 10 = 103 > 102$). Downstream Phase 5F-C CP-SAT input validation crashed with `ValueError`, causing the orchestrator to abort in $0.12\text{ ms}$ and output zeroes across all scenario metrics.
   - **Remediation:** Implemented proportional discrete allocation via the **Largest Remainder Method (Hare-Niemeyer)** in `scale_demographics_proportionally()`, guaranteeing $\sum_{g} \text{demo}[g] = \text{people\_affected}$ strictly for all positive integer scales.

2. **BUG 2 (P2) — Ephemeral Route UUID Comparison:**
   - **File:** [`backend/app/ai/simulation/response_simulator.py`](file:///c:/Users/shubh/Downloads/DIRS/backend/app/ai/simulation/response_simulator.py)
   - **Root Cause:** Phase 5E generates an ephemeral random UUID (`route_id = str(uuid.uuid4())`) on every solver execution. `compute_response_delta()` indexed routes by `r.route_id`, guaranteeing lookup failures across runs and falsely flagging all baseline routes as "disrupted by scenario blockages" on scenarios with zero blockages (Gates 6A, 6B, 6C, 6D, 6F, 6H, 6J) or off-route blockages (Gate 6E).
   - **Remediation:** Replaced ephemeral UUID lookup with stable `vehicle_id` tracking and spatial road network path tracing. When no road blockages or disabled vehicles exist, `new_disrupted_routes` is strictly empty (`[]`). When blockages exist, the path between waypoints is checked against actual scenario blocked edges and unreachable nodes.

---

## 2. Strict Boundary Compliance

As mandated by system governance and architectural constraints:

| Component | Status | Modification Made |
| :--- | :--- | :--- |
| **Phase 5C: RoadGraphEngine** (`graph.py`) | **FROZEN** | **NONE** (0 lines modified) |
| **Phase 5D: MultiCommodityAllocationEngine** (`allocation.py`) | **FROZEN** | **NONE** (0 lines modified) |
| **Phase 5E: VehicleRoutingEngine** (`routing.py`) | **FROZEN** | **NONE** (0 lines modified) |
| **Phase 5F-B: Shelter / Volunteer Schemas** | **FROZEN** | **NONE** (0 lines modified) |
| **Phase 5F-C: ShelterEvacuationEngine** (`shelter.py`) | **FROZEN** | **NONE** (0 lines modified) |
| **Phase 5F-D: VolunteerAssignmentEngine** (`volunteer.py`) | **FROZEN** | **NONE** (0 lines modified) |
| **Phase 5F-E: IntegratedResponseOrchestrator** (`orchestrator.py`) | **FROZEN** | **NONE** (0 lines modified) |
| **Phase 5G: Scenario Engine** (`scenario_engine.py`) | **EDITED** | Added `scale_demographics_proportionally()`, updated `apply_scenario()` |
| **Phase 5G: Response Simulator** (`response_simulator.py`) | **EDITED** | Updated `compute_response_delta()` with spatial blockage tracing |
| **Phase 5G: Simulation Router** (`routers/simulation.py`) | **EDITED** | Updated `_to_incident_input()` to guarantee demographic partition sum |

Zero solver constraints, weights, or objective formulations were altered.

---

## 3. Detailed Forensic Remediation

### 3.1 Bug 1: Demographic Scaling Invariant (P1)

#### Mathematical Invariant
$$\sum_{g \in \{\text{GEN}, \text{ACC}, \text{MED}, \text{MED\_ACC}\}} \text{demo}[g] = \text{people\_affected}$$

#### Hare-Niemeyer Largest Remainder Allocation
To avoid integer ceil inflation when scaling by multiplier $m$:
1. $P_{\text{new}} = \max(0, \lceil P_{\text{orig}} \times m \rceil)$
2. Quota per group: $q_g = \frac{C_g}{\sum C_k} \times P_{\text{new}}$
3. Integer floor: $f_g = \lfloor q_g \rfloor$
4. Remainder: $r_g = q_g - f_g$
5. Remainder units $U = P_{\text{new}} - \sum f_g$ are distributed 1 by 1 to groups in descending order of remainder $r_g$, tie-broken deterministically by clinical priority (`MED_ACC` > `MED` > `ACC` > `GEN`).

#### Validation Results
- **Gate 6I Reproduction:**
  - Base Sheltered: 1,695
  - Scenario Sheltered: 2,038 ($\Delta = +343$)
  - Status: `PROPOSED` (Clean CP-SAT solve, $0$ unmet evacuees)
  - Allocations: 36,131.0 L resources allocated

---

### 3.2 Bug 2: Stable Route Disruption Detection (P2)

#### Behavioral Invariant
- If $\text{additional\_blockages} = \emptyset$, $\text{vehicle\_availability\_changes} = \emptyset$, and $\text{unreachable\_nodes} = \emptyset \implies \text{new\_disrupted\_routes} = []$.
- If a road blockage $(u, v)$ is impassable, a baseline route $r$ is flagged if and only if the shortest-path node sequence of any leg of $r$ traverses $(u, v)$ or $(v, u)$, or if the assigned vehicle is marked unavailable.

#### Validation Results
- **Gate 6A, 6B, 6C, 6D, 6F, 6H, 6J (Zero Blockages):** `new_disrupted_routes = []` (Zero false alerts).
- **Gate 6E (Road Closure `NODE_0012` - `NODE_0020` off-route):** `new_disrupted_routes = []` (Zero false alerts).
- **Direct Blockage Test (`NODE_0028` - `NODE_0029` on `VEH_INT_002` route):** Correctly flags `VEH_INT_002` route ID in `new_disrupted_routes`.
- **Disabled Active Vehicle Test (`VEH_INT_002`):** Correctly flags `VEH_INT_002` route ID in `new_disrupted_routes`.
- **Disabled Inactive Vehicle Test (`VEH_INT_001`):** `new_disrupted_routes = []`.

---

## 4. Verification and Regression Suite

### 4.1 Dedicated Regression Suite (`test_phase5g_remediation_regression.py`)
| Test Case | Scenario / Condition | Result |
| :--- | :--- | :--- |
| `test_retest_bug1_largest_remainder_method_conservation` | 8 diverse demographic distributions & edge cases | **PASSED** |
| `test_retest_bug1_gate_6i_monsoonal_inundation_reproduction` | Gate 6I 1.2x scale on DIRS-GIS-10 | **PASSED** |
| `test_retest_bug1_various_multipliers_preserve_demographic_invariant` | Scales 0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x | **PASSED** |
| `test_retest_bug1_injected_incidents_normalization` | Injected raw dictionary incident normalization | **PASSED** |
| `test_retest_bug2_zero_blockages_yields_zero_disrupted_routes` | Scenario with zero road blockages | **PASSED** |
| `test_retest_bug2_gate_6e_off_route_blockage` | Gate 6E off-route road closure | **PASSED** |
| `test_retest_bug2_on_route_blockage_detected` | Direct blockage on active vehicle route | **PASSED** |
| `test_retest_bug2_disabled_vehicle_detected` | Active vehicle marked unavailable | **PASSED** |
| `test_retest_bug2_inactive_vehicle_disabled_yields_zero_disruptions` | Inactive vehicle marked unavailable | **PASSED** |

### 4.2 Comprehensive System Suite
- **Phase 5G Unit/Integration Suite:** 64 passed in 5.04s.
- **Full Backend Suite:** 348 passed, 0 failed in 33.23s.
- **Frontend TypeScript / Vite Build:** Passed with 0 errors (`dist/index.html` built cleanly).

---

## 5. Gate Recommendation

Both confirmed bugs have been remediated with mathematical precision and zero side effects on the frozen Phase 5 core.

**Final Gate Verdict:**
$$\mathbf{PASS — READY\ FOR\ MANUAL\ RETEST}$$
