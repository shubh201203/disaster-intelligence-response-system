# PHASE 5F-A — Forensic Validation Plan & Scenario Test Design

**System:** Disaster Incident Response System (DIRS)  
**Phase:** 5F-A (Shelter & Volunteer Optimization: Research, Audit & Formulation)  
**Component:** Automated Test Suite & Forensic Validation Specifications  
**Classification:** PROSPECTIVE TEST DESIGN SPECIFICATION (PRE-IMPLEMENTATION)  
**Date:** 2026-09-22  

---

## 1. Validation Methodology & Standards

Validation for Phase 5F establishes prospective test specifications following the forensic standards of Phases 5C, 5D, and 5E:
1. **Mathematical Invariant Verification:** Testing conservation laws, physical capacities, and structural exclusions.
2. **Adversarial Scenario Testing:** 8 controlled shelter test designs (S1–S8) and 8 controlled volunteer test designs (V1–V8).
3. **Deterministic Baseline Benchmarking:** Fair comparison against transparent heuristic baselines.
4. **Brute-Force Optimality Proof:** Exhaustive enumeration on minimal instances to prove mathematical optimality.
5. **State & Version Integrity:** Verifying response to Phase 5C road graph blockages and graph version mutations.

> [!IMPORTANT]
> **Pre-Implementation Status Notice:**
> The scenario specifications below represent **prospective test designs and expected behaviors**. No tests have been run or passed yet, as Phase 5F implementation has not begun.

---

## 2. Shelter Assignment Prospective Scenario Matrix (Scenarios S1 to S8)

| Scenario ID | Test Name | Injected Operational Condition | Expected Invariant / Outcome (To be verified post-implementation) |
|---|---|---|---|
| **SCENARIO-S1** | Sufficient Total Capacity | Total shelter remaining capacity $\ge 150\%$ of total displaced population. | $\sum u_i = 0$. 100% of population assigned to closest safe shelters. Status: `FULLY_FEASIBLE`. |
| **SCENARIO-S2** | Severe Capacity Shortfall | Total displaced population exceeds all available regional capacity. | Remaining capacity is 100% utilized. Explicit unassigned count: $\sum u_i = \sum p_i - \sum C_s$. Status: `PARTIALLY_FEASIBLE`. |
| **SCENARIO-S3** | Nearest Shelter Saturated | Nearest shelter has $C_{s1} = 0$ (full), while secondary shelter $S_2$ at $+15\text{ min}$ has capacity. | Evacuees automatically routed to $S_2$. Zero evacuees placed in saturated $S_1$. |
| **SCENARIO-S4** | Shelter Status Closed | Shelter marked `status = "CLOSED"` due to structural inspection failure. | Hard exclusion: $\sum_g x_{isg} \equiv 0$. Solver ignores closed facility completely. |
| **SCENARIO-S5** | Accessibility Compliance | Incident has 30 vulnerable evacuees ($p_{i, \text{ACC}} = 30$). Shelter $S_1$ (close) has $A_{s1} = 0$; $S_2$ (far) has $A_{s2} = 1$. | All 30 vulnerable evacuees assigned to accessible shelter $S_2$. Zero vulnerable placed in non-accessible $S_1$. |
| **SCENARIO-S6** | Incident Priority Competition | Two incidents ($I_{\text{CRITICAL}}$ and $I_{\text{LOW}}$) compete for 100 available shelter slots. | Solver fills $I_{\text{CRITICAL}}$ demand first; $I_{\text{LOW}}$ absorbs remaining slots or is left unassigned. |
| **SCENARIO-S7** | Blocked Road & Unreachable | Direct road to closest shelter is `BLOCKED` (Phase 5C $R_{is} = 0$). | Solver either detours around blockage via open edges or assigns to alternate open shelter. Blocked edge traversed 0 times. |
| **SCENARIO-S8** | Total Regional Infeasibility | All shelters in district are closed, full, or completely unreachable. | Clean, non-crashing termination. Assigned $= 0$, Unassigned $= \sum p_i$. Status: `INFEASIBLE`. |

---

## 3. Volunteer Assignment Prospective Scenario Matrix (Scenarios V1 to V8)

| Scenario ID | Test Name | Injected Operational Condition | Expected Invariant / Outcome (To be verified post-implementation) |
|---|---|---|---|
| **SCENARIO-V1** | Full Roster Fulfillment | Pool of qualified volunteers exceeds task requirements across all categories. | $\sum u_{ikt} = 0$. All incident tasks filled by nearest qualified responders. Status: `FULLY_FEASIBLE`. |
| **SCENARIO-V2** | Severe Volunteer Scarcity | 5 tasks requested, only 2 volunteers available. | 2 highest-priority tasks filled (e.g. MEDICAL at CRITICAL incident); 3 tasks flagged as explicit unassigned $u_{ikt}$. |
| **SCENARIO-V3** | Strict Skill Compatibility | Incident requires `MEDICAL` task; only `GENERAL` and `LOGISTICS` volunteers in range. | Zero assignment to `MEDICAL` task ($u_{i, \text{MED}, t} = 1$). Unqualified volunteers are strictly excluded. |
| **SCENARIO-V4** | Verification Enforcement | Highly skilled volunteer has `verification_status = "PENDING"`. | Hard exclusion: Volunteer ignored by solver until verified by admin. |
| **SCENARIO-V5** | Availability Filtering | Volunteer marked `is_available = False` for the current operational shift. | Excluded from candidate pool; zero assignments generated. |
| **SCENARIO-V6** | Workload Ceiling Cap | Task requires $10\text{ hours}$; volunteer maximum shift is $8.0\text{ hours}$. | Assignment rejected or capped at max allowable workload limit. |
| **SCENARIO-V7** | Double-Booking Prevention | Volunteer $V_1$ is candidate for Incident $I_1$ and Incident $I_2$ in the same shift. | $\sum_{i, k} y_{vikt} \le 1$ enforced. $V_1$ assigned to at most one incident. |
| **SCENARIO-V8** | Transit Radius Cutoff | Incident is $90\text{ minutes}$ transit time away; volunteer maximum transit limit is $45\text{ minutes}$. | Candidate excluded due to transit feasibility threshold. |

---

## 4. Deterministic Baseline Specifications

To scientifically demonstrate the efficacy of mathematical programming over conventional heuristics:

### 4.1 Shelter Baselines
- **Baseline A (Nearest-Feasible Heuristic):** Iterates over incidents in arrival order, greedily placing evacuees in the nearest shelter with $C_s > 0$.
- **Baseline B (Largest-Remaining-Capacity Heuristic):** Greedily assigns evacuees to the largest available shelter, minimizing fragmentation but incurring severe travel time penalties.
- **Baseline C (Priority-First Nearest-Feasible):** Sorts incidents by `priority_score` descending, then greedily assigns to nearest feasible shelter.

### 4.2 Volunteer Baselines
- **Baseline A (Nearest Qualified Available):** Greedily matches each task to the closest qualified volunteer currently unassigned.
- **Baseline B (First-Come First-Served Qualified):** Matches tasks based on registration timestamp of verified volunteers.

---

## 5. Brute-Force Exhaustive Permutation Validation

To mathematically prove that OR-Tools CP-SAT finds the true global optimum:
1. **Shelter Minimal Instance:** 2 Incidents ($p_1=40, p_2=30$) and 2 Shelters ($C_1=50, C_2=50$). Total assignment combinations $= 51 \times 51 = 2,601$. Evaluate objective across all feasible points; assert that CP-SAT matches the exact minimum objective value.
2. **Volunteer Minimal Instance:** 2 Incidents, 2 Tasks, 3 Qualified Volunteers. Total permutations $= 3 \times 2 = 6$. Assert CP-SAT matches exhaustive permutation evaluation.
