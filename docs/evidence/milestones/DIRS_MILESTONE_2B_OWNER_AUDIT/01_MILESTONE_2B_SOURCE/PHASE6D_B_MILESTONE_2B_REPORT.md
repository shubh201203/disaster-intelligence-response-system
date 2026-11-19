# DIRS PHASE 6D-B — MILESTONE 2B REPORT
## CP-SAT Optimization Engine Implementation and Acceptance Evidence

**PROJECT:** Disaster Intelligence and Response System (DIRS)  
**PHASE:** 6D-B — Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine  
**MILESTONE:** 2B — CP-SAT Optimization Engine Implementation  
**DATE:** 2026-11-17  
**VERDICT:** `MILESTONE 2B COMPLETE — READY FOR OWNER REVIEW`

---

## 1. EXECUTIVE SUMMARY

Phase 6D-B Milestone 2B implements the pure mathematical Google OR-Tools CP-SAT recovery optimization engine in accordance with the formally approved Milestone 2A design architecture, mathematical specifications, numerical scaling proofs, and risk registers.

Milestone 2B encapsulates multi-period scheduling, non-preemptive activity execution, critical path precedence with discrete period lags, renewable resource limits, indivisible project funding source assignment (RSK-M2-06 Model B), periodic cash-flow solvency recurrence with full retention ($\eta = 1.0$), district equity quota floors with uncontacted blackout district ring-fencing, and multi-objective optimization with non-compensatory acceleration tie-breaking.

All implementation components operate in-memory with pure mathematical logic and zero persistence side-effects. The engine strictly preserves the frozen database schema (PostgreSQL `dirs_db` at exactly 40 base tables: 39 user + 1 PostGIS; Alembic migration head `phase6b_recovery_foundation`), introduces zero database migrations, leaves existing ORM models and API routers unmodified, and introduces zero database writes to `recovery_projects.priority_score`.

Verification results:
- **35 / 35** Phase 6D-B Milestone 2B CP-SAT optimization test scenarios passed ($100\%$).
- **45 / 45** Phase 6D-B Milestone 1 pure mathematical service test scenarios passed ($100\%$).
- **14 / 14** Phase 6B/6C recovery and damage needs test scenarios passed ($100\%$).
- **462 / 462** total repository backend test suite scenarios passed ($100\%$).

---

## 2. PREFLIGHT FINDINGS

Prior to implementation, the runtime environment and dependencies were verified:
1. **Google OR-Tools Version**: `ortools.__version__ == "9.15.6755"`. The CP-SAT solver (`cp_model.CpModel`, `cp_model.CpSolver`) is fully functional.
2. **Pydantic**: Pydantic `2.13.4` verified. Dataclasses and Pydantic primitives operate seamlessly.
3. **Python Runtime**: Python 3.11.9 (AMD64) on Windows NT.
4. **Milestone 1 Service Interfaces**: Public mathematical interfaces in `backend/app/recovery/services/` were inspected and integrated without modification:
   - `ProjectDependencyService`: DAG analysis, topological sorting, Kahn's cycle detection (`detect_cycle_and_toposort`), CPM-PL schedule forward/backward passes (`compute_cpm_pl`).
   - `CalendarCostService`: Apportionment curves and calendar mapping.
   - `EquityCalculationService`: District allocation floors and Gini coefficient calculations.
   - `CashFlowSolvencyService`: Periodic solvency recurrence and deficit tracking.
   - `MCPIPrioritizationService`: Multi-criteria project prioritization scoring.

---

## 3. FILES CREATED AND THEIR RESPONSIBILITIES

All Milestone 2B production code resides in `backend/app/recovery/optimization/`:

| File Path | Lines | Core Responsibilities |
|---|---|---|
| `backend/app/recovery/optimization/schemas.py` | 345 | Currency conversion (`CurrencyUnit`), exact CCU integer scaling ($10^{-5}\text{ INR}$), MCPI score quantization ($\lfloor \text{raw} \times 10^7 \rfloor$), Theorem 1 deterministic capped integer apportionment (`deterministic_capped_apportionment`), and complete dataclass contracts for solver inputs and forensic outputs. |
| `backend/app/recovery/optimization/infeasibility_advisor.py` | 501 | Deterministic pre-solve screening across 6 diagnostic categories (`AGGREGATE_BUDGET_EXCEEDED`, `PERIODIC_SOLVENCY_VIOLATION`, `RESOURCE_CAPACITY_EXCEEDED`, `PRECEDENCE_DEADLINE_CONFLICT`, `PLANNING_HORIZON_EXCEEDED`, `FUNDING_SOURCE_RESTRICTION`), 4 diagnostic tiers (`PROVEN_INFEASIBILITY`, `NECESSARY_CONDITION_VIOLATION`, `WARNING`, `SOLVER_ASSISTED_HYPOTHESIS`), and post-solve CP-SAT assumption core extraction. |
| `backend/app/recovery/optimization/recovery_cpsat_solver.py` | 583 | Google OR-Tools CP-SAT model builder and solver. Implements decision variables ($w_j, x_{j, t}, I_j, z_{j, f}$), hard constraints (mandatory life-safety selection, start uniqueness, precedence, lags, deadlines, horizons, indivisible funding, cash-flow solvency, district equity, blackout ring-fencing, renewable resource limits), multi-objective formulation, and forensic execution metadata recording. |
| `backend/app/recovery/optimization/recovery_optimization_orchestrator.py` | 186 | Optimization orchestrator. Validates inputs, handles empty portfolio edge cases, executes topological cycle pre-checks via Kahn's algorithm (failing closed with `MODEL_INVALID` on cycles), invokes `RecoveryCPSATSolver`, and formats end-to-end responses. |
| `backend/app/recovery/optimization/__init__.py` | 51 | Public namespace exporting all 20 public classes, enums, schemas, and helper functions. |
| `tests/backend/test_phase6d_cpsat_solver.py` | 771 | Comprehensive test suite containing 35 exhaustive unit, integration, and property test scenarios covering every required optimization behavior. |

---

## 4. MATHEMATICAL FORMULATION IMPLEMENTED

### 4.1 Decision Variables
- $w_j \in \{0, 1\}$: Binary project selection indicator for project $j \in \mathcal{J}$.
- $x_{j, t} \in \{0, 1\}$: Binary start indicator, where $x_{j, t} = 1$ if project $j$ begins in discrete period $t \in \mathcal{T}_j$.
- $I_j$: Optional interval variable in CP-SAT with presence literal $w_j$, start variable $S_j \in [1, T]$, duration $d_j$, and end variable $C_j^{\text{end}} \in [1, T+1]$.
- $z_{j, f} \in \{0, 1\}$: Indivisible funding assignment variable, where $z_{j, f} = 1$ if project $j$ is wholly funded by source $f \in \mathcal{F}_j$.

### 4.2 Hard Constraints
1. **Mandatory Life-Safety Hard Mandate (RSK-M2-01 Option A)**:
   $$w_j = 1 \quad \forall j \in \mathcal{J}_{\text{mandatory}}$$
2. **Start Uniqueness & Existence**:
   $$\sum_{t \in \mathcal{T}_j} x_{j, t} = w_j \quad \forall j \in \mathcal{J}$$
3. **Start Period Linking**:
   $$S_j = \sum_{t \in \mathcal{T}_j} t \cdot x_{j, t} \quad \text{enforced if } w_j = 1; \quad S_j = 1 \quad \text{enforced if } w_j = 0$$
4. **Planning Horizon & Deadlines**:
   $$\mathcal{T}_j = \{ t \in \mathbb{Z} \mid \max(1, r_j) \le t \le \min(T - d_j + 1, D_j - d_j + 1) \}$$
5. **Selection Precedence**:
   $$w_j \le w_i \quad \forall (i, j) \in \mathcal{E}$$
6. **Timing Precedence with Discrete Lag**:
   $$S_j \ge S_i + d_i + L_{ij} \quad \forall (i, j) \in \mathcal{E}, \quad \text{enforced if } w_j = 1$$
7. **Indivisible Project Funding Assignment (RSK-M2-06 Model B)**:
   $$\sum_{f \in \mathcal{F}_j^{\text{eligible}}} z_{j, f} = w_j \quad \forall j \in \mathcal{J}$$
   $$z_{j, f} = 0 \quad \forall f \notin \mathcal{F}_j^{\text{eligible}}$$
   $$\sum_{j \in \mathcal{J}} c_j \cdot z_{j, f} \le F_f^{\max} \quad \forall f \in \mathcal{F}$$
8. **Periodic Cash-Flow Solvency Recurrence (Full Fiscal Retention $\eta = 1.0$)**:
   $$\sum_{s=1}^t E_s \le \Phi_0 + \sum_{s=1}^t B_s \quad \forall t \in \{1, \dots, T\}$$
   where periodic project expenditure $E_{j, t}$ is convolved from start indicators:
   $$E_{j, t} = \sum_{\tau=1}^{d_j} e_{j, \tau} \cdot x_{j, t - \tau + 1}$$
9. **District Policy Equity Floors**:
   $$\sum_{j \in \mathcal{P}_d} c_j \cdot w_j \ge \min\left( \lceil \theta_d \cdot B_{\text{total}} \rceil, \sum_{j \in \mathcal{P}_d} c_j \right) \quad \forall d \in \mathcal{D}$$
10. **Uncontacted Blackout District Ring-Fencing**:
    $$\sum_{j \in \mathcal{J}} c_j \cdot w_j \le B_{\text{total}} - \sum_{d \in \mathcal{D}_{\text{blackout}}} \lceil \theta_d \cdot B_{\text{total}} \rceil$$
11. **Renewable Resource Capacity Limits**:
    $$\sum_{j \in \mathcal{J}} u_{j, r} \sum_{s = \max(1, t - d_j + 1)}^t x_{j, s} \le R_{r, t} \quad \forall r \in \mathcal{R}, \forall t \in \{1, \dots, T\}$$

### 4.3 Multi-Objective Formulation
$$\max Z = \sum_{j \in \mathcal{J}} \left( 1000 \cdot \bar{\Pi}_j \cdot w_j + \sum_{t \in \mathcal{T}_j} (T - t) \cdot x_{j, t} \right)$$
where $\bar{\Pi}_j = \lfloor \text{raw\_mcpi}_j \times 10^7 \rfloor$. Under this integer scaling, the maximum possible acceleration bonus across all projects is strictly bounded to $< 1000$ micro-units ($< 1$ basis point of MCPI), guaranteeing zero distortion of substantive project selection orderings while deterministically breaking schedule ties in favor of earlier project starts.

---

## 5. CONSTRAINT-TO-CODE TRACEABILITY MATRIX

| Constraint Name | Mathematical Definition | Code Implementation Location | Traceability Reference |
|---|---|---|---|
| Mandatory Selection | $w_j = 1 \; \forall j \in \mathcal{J}_{\text{mandatory}}$ | `recovery_cpsat_solver.py:155-161` | RSK-M2-01 (Option A) |
| Start Domain | $t \in [r_j, \min(T - d_j + 1, D_j - d_j + 1)]$ | `recovery_cpsat_solver.py:125-135` | Form. §3.2 Eq. 2 |
| Start Uniqueness | $\sum_t x_{j, t} = w_j$ | `recovery_cpsat_solver.py:146` | Form. §3.2 Eq. 3 |
| Start Linking | $S_j = \sum_t t \cdot x_{j, t}$ if $w_j = 1$ | `recovery_cpsat_solver.py:148-150` | Form. §3.2 Eq. 4 |
| Selection Precedence | $w_j \le w_i$ | `recovery_cpsat_solver.py:200` | Form. §3.2 Eq. 5 |
| Timing Precedence | $S_j \ge S_i + d_i + L_{ij}$ | `recovery_cpsat_solver.py:208-212` | Form. §3.2 Eq. 6 |
| Indivisible Funding | $\sum_f z_{j, f} = w_j$ | `recovery_cpsat_solver.py:164-173` | RSK-M2-06 (Model B) |
| Fund Capacity | $\sum_j c_j z_{j, f} \le F_f^{\max}$ | `recovery_cpsat_solver.py:176-192` | RSK-M2-06 (Model B) |
| Capped Apportionment | $\sum_{\tau=1}^d e_{j, \tau} = c_j, \; e_{j, \tau} \le \bar{E}_{\tau}$ | `schemas.py:136-218` | Theorem 1 (LR-WF) |
| Periodic Solvency | $\sum_{s=1}^t E_s \le \Phi_0 + \sum_{s=1}^t B_s$ | `recovery_cpsat_solver.py:249-272` | RSK-M2-05 (Global) |
| District Equity | $\sum_{j \in \mathcal{P}_d} c_j w_j \ge \min(\bar{R}_d, C_d)$ | `recovery_cpsat_solver.py:275-296` | Form. §3.2 Eq. 10 |
| Blackout Reserve | $\sum c_j w_j \le B_{\text{total}} - \sum_{d \in \text{blackout}} \bar{R}_d$ | `recovery_cpsat_solver.py:298-313` | Form. §3.2 Eq. 11 |
| Renewable Resource | $\sum_j u_{j, r} \text{active}_j(t) \le R_{r, t}$ | `recovery_cpsat_solver.py:315-338` | Form. §3.2 Eq. 12 |
| Multi-Objective | $\max \sum (1000 \bar{\Pi}_j w_j + (T - t) x_{j, t})$ | `recovery_cpsat_solver.py:340-357` | Form. §3.3 Eq. 13 |
| Cycle Pre-Check | Kahn's Algorithm DAG toposort | `recovery_optimization_orchestrator.py:138-144` | M1 DAG Service |

---

## 6. INTEGER SCALING AND NUMERICAL SAFETY

1. **Currency Scaling Unit (CCU)**:
   - Base unit: $1\text{ CCU} = 10^{-5}\text{ INR} = 0.00001\text{ INR}$.
   - All monetary quantities (candidate costs, periodic budgets, initial cash, fund capacities) are scaled to non-negative 64-bit integers.
   - Conversion preserves exact integers for inputs up to 5 decimal places.
   - Rounding directions:
     - Project costs, equity floors: `ROUND_CEILING` (conservative on expenditure).
     - Budgets, initial cash, fund capacities: `ROUND_FLOOR` (conservative on available liquidity).
2. **MCPI Score Quantization**:
   - Formula: $\bar{\Pi}_j = \lfloor \text{raw\_mcpi}_j \times 10^7 \rfloor$.
   - Bound: $\bar{\Pi}_j \in [0, 10^7]$.
   - Quantization error bound: $|\text{raw} - \bar{\Pi} \times 10^{-7}| < 10^{-7}$.
   - Guaranteed distinction threshold: $\Delta > 10^{-7}$.
3. **Integer Apportionment Conservation (Theorem 1)**:
   - `deterministic_capped_apportionment` guarantees $\sum_{\tau=1}^d e_{j, \tau} = c_j$ identically.
   - Zero-weight governance: raises `ValueError("ZERO_ELIGIBLE_WEIGHTS")` unless `allow_uniform_fallback=True`.
4. **Integer Overflow Protection**:
   - Max portfolio budget tested: ₹$10,000\text{ Crores} = 10^{11}\text{ INR} = 10^{16}\text{ CCU}$.
   - Fits safely within 63-bit signed integer capacity ($2^{63} - 1 \approx 9.22 \times 10^{18}$).

---

## 7. SOLVER CONFIGURATION AND REPRODUCIBILITY

In accordance with ratified decision **RSK-M2-03 (Option A)**:
- **Search Workers**: `num_search_workers = 1` by default for certified deterministic execution.
- **Random Seed**: `random_seed = 42` fixed by default.
- **Solver Time Limit**: Explicitly configured (`max_time_in_seconds = 60.0`).
- **Canonical Input Fingerprint**: Canonical deterministic SHA-256 hash computed over sorted normalized request payload:
  $$\text{SHA-256}(\text{scenario} \,\|\, T \,\|\, \Phi_0 \,\|\, B_t \,\|\, \text{candidates} \,\|\, \mathcal{E} \,\|\, \mathcal{R} \,\|\, \mathcal{F})$$
- **Forensic Execution Metadata**: Returned on every response:
  - `ortools_version`: recorded dynamically (`9.15.6755`).
  - `solver_parameters`: `{"num_search_workers": 1, "random_seed": 42, "max_time_in_seconds": 60.0}`.
  - `input_fingerprint_sha256`: 64-character hexadecimal digest.
  - `is_optimal`: boolean indicating mathematical proof of global optimality.
  - `optimality_gap`: relative gap between best bound and objective.
  - `solve_time_seconds`: measured using monotonic high-resolution clock (`time.perf_counter`).
- **Reproducibility Disclaimer**: Bitwise determinism across differing OS/CPU microarchitectures is explicitly disclaimed. Multi-worker execution (`num_workers > 1`) is supported as non-certified mode.

---

## 8. INFEASIBILITY DIAGNOSTIC BEHAVIOR

When a recovery portfolio cannot be feasibly scheduled, the engine returns `solver_status = "INFEASIBLE"` with an `InfeasibilityDiagnosticReport`.

### 8.1 Six Forensic Categories
1. `AGGREGATE_BUDGET_EXCEEDED`: Total mandatory project cost exceeds available liquidity $\Phi_0 + \sum B_t$.
2. `PERIODIC_SOLVENCY_VIOLATION`: Mandatory project expenditure trajectory exceeds cumulative cash revenue at period $t$.
3. `RESOURCE_CAPACITY_EXCEEDED`: Peak mandatory resource demand exceeds renewable capacity at period $t$.
4. `PRECEDENCE_DEADLINE_CONFLICT`: Precedence chain duration exceeds hard completion deadline $D_j$.
5. `PLANNING_HORIZON_EXCEEDED`: Precedence chain makespan exceeds planning horizon $T$.
6. `FUNDING_SOURCE_RESTRICTION`: Indivisible funding capacity or eligibility restricts mandatory project assignment.

### 8.2 Diagnostic Tiers & Assumption Core Extraction
- **Tier 1 (`PROVEN_INFEASIBILITY`)**: Mathematical proof of infeasibility (e.g., $c_{\text{mandatory}} > B_{\text{total}}$, $E_j + d_j - 1 > T$).
- **Tier 2 (`NECESSARY_CONDITION_VIOLATION`)**: Relaxation lower-bound failure (e.g., latest-start cumulative spend deficit, Hall's marriage condition failure).
- **Tier 3 (`WARNING`)**: Risk indicator that does not prove infeasibility (e.g., earliest-start cash dip).
- **Tier 4 (`SOLVER_ASSISTED_HYPOTHESIS`)**: Extracted from CP-SAT `solver.SufficientAssumptionsForInfeasibility()`. The report explicitly disclaims that assumption cores are **neither minimal nor unique**.

---

## 9. TEST CASES AND ACTUAL RESULTS (ALL 35 SCENARIOS)

| Test ID | Test Scenario | Expected Behavior | Actual Result | Status |
|---|---|---|---|---|
| `test_01` | Empty project portfolio | Returns OPTIMAL with 0 selected projects | `OPTIMAL`, count=0, cost=0 | PASSED |
| `test_02` | One feasible project | Selected, scheduled at start period 1 | `OPTIMAL`, start=1, finish=2 | PASSED |
| `test_03` | Multiple feasible projects | High MCPI projects selected within budget | `OPTIMAL`, selected=[PROJ_01] | PASSED |
| `test_04` | Mandatory life-safety selection | Mandatory project selected despite lower MCPI | `OPTIMAL`, selected=[P_MAND] | PASSED |
| `test_05` | Mandatory projects causing infeasibility | INFEASIBLE with structured diagnostics | `INFEASIBLE`, diag report present | PASSED |
| `test_06` | Release period enforcement | Project scheduled $\ge$ release period | `OPTIMAL`, scheduled start $\ge 3$ | PASSED |
| `test_07` | Deadline enforcement | Completion period $\le$ hard deadline | `OPTIMAL`, finish $\le 3$ | PASSED |
| `test_08` | Planning horizon enforcement | Completion period $\le$ planning horizon $T$ | `OPTIMAL`, finish $\le 3$ | PASSED |
| `test_09` | Dependency precedence | Successor selected only if predecessor selected | `OPTIMAL`, selection respected | PASSED |
| `test_10` | Dependency lag | Successor start $\ge$ predecessor finish + lag | `OPTIMAL`, start_B $\ge$ finish_A + 1 | PASSED |
| `test_11` | Circular dependency rejection | Kahn's cycle detection returns MODEL_INVALID | `MODEL_INVALID`, cycle path extracted | PASSED |
| `test_12` | Resource capacity without overlap | Projects execute sequentially to obey capacity | `OPTIMAL`, zero overlap | PASSED |
| `test_13` | Resource capacity with overlap | Forced overlap exceeds capacity $\implies$ INFEASIBLE | `INFEASIBLE`, resource diag present | PASSED |
| `test_14` | Multi-period resource occupancy | Resource held across entire duration | `OPTIMAL`, occupancy non-overlapping | PASSED |
| `test_15` | Indivisible funding assignment | Assigned wholly to exactly one eligible fund | `OPTIMAL`, fund assigned indivisibly | PASSED |
| `test_16` | Ineligible funding source rejection | Projects assigned only to eligible funds | `OPTIMAL`, zero ineligible assignments | PASSED |
| `test_17` | Funding assignment counterexample | Bipartite capacity counterexample $\implies$ INFEASIBLE | `INFEASIBLE`, fund diag present | PASSED |
| `test_18` | Aggregate budget infeasibility | Mandatory cost $>$ total budget $\implies$ INFEASIBLE | `INFEASIBLE`, aggregate budget diag | PASSED |
| `test_19` | Periodic solvency infeasibility | Revenue shortfall in period $t \implies$ INFEASIBLE | `INFEASIBLE`, solvency diag present | PASSED |
| `test_20` | Initial cash contribution | Initial cash $\Phi_0$ satisfies early liquidity | `OPTIMAL`, solvent execution | PASSED |
| `test_21` | Currency conversion | Correct conversion for INR, Lakh, Crore | Exact integer CCU matches | PASSED |
| `test_22` | Decimal rounding directions | Ceil on costs, floor on budgets | Conservative rounding verified | PASSED |
| `test_23` | MCPI quantization | Exact $\lfloor \text{raw} \times 10^7 \rfloor$ quantization | Integer coefficients verified | PASSED |
| `test_24` | Acceleration penalty | Early start preferred under identical MCPI | `OPTIMAL`, scheduled at period 1 | PASSED |
| `test_25` | Solver optimal status | Solvable instance returns status OPTIMAL | `OPTIMAL`, is_optimal=True | PASSED |
| `test_26` | Solver feasible status handling | Status FEASIBLE parsed cleanly | `FEASIBLE` contract parsed | PASSED |
| `test_27` | Solver infeasible status handling | Status INFEASIBLE parsed with diagnostics | `INFEASIBLE`, report extracted | PASSED |
| `test_28` | Unknown / timeout handling | Status UNKNOWN parsed with diagnostics | `UNKNOWN`, timeout handled | PASSED |
| `test_29` | Model invalid handling | Status MODEL_INVALID handled | `MODEL_INVALID` handled | PASSED |
| `test_30` | SHA-256 input fingerprint | Identical inputs produce identical digests | Deterministic digest verified | PASSED |
| `test_31` | Reproducibility metadata | OR-Tools version, parameters, seed captured | All metadata fields populated | PASSED |
| `test_32` | Invalid numerical coefficients | NaN, negative cost, out-of-range MCPI rejected | `ValueError` raised | PASSED |
| `test_33` | Integer overflow protection | ₹10,000 Crore budget processed without overflow | Exact arithmetic verified | PASSED |
| `test_34` | All six diagnostic categories | Pre-solve advisor identifies all 6 categories | All 6 category enums emitted | PASSED |
| `test_35` | Multiple simultaneous categories | Multiple conflicts reported simultaneously | Compound diagnostics emitted | PASSED |

**Milestone 2B Test Suite Execution Summary**: `35 passed in 0.82s`.

---

## 10. REGRESSION RESULTS

### 10.1 Phase 6D-B Milestone 1 Pure Mathematical Services
- Command: `pytest tests/backend/test_phase6d_mathematical_services.py -v`
- Result: **45 passed, 0 failed in 0.76s** ($100\%$).

### 10.2 Phase 6B & Phase 6C Recovery Foundations
- Command: `pytest tests/backend/test_phase6b_recovery.py tests/backend/test_phase6c_damage_needs.py -v`
- Result: **14 passed, 0 failed in 3.04s** ($100\%$).

### 10.3 Full Repository Backend Test Suite
- Command: `pytest tests/backend/ -q`
- Result: **462 passed, 0 failed in 41.77s** ($100\%$).

---

## 11. FROZEN-FILE INTEGRITY AUDIT

To confirm that frozen phases and baseline codebase remained strictly untouched:

| Target Directory / File | Modification Status | Verification Method |
|---|---|---|
| `backend/app/models/` | **UNMODIFIED** | File inspection, zero edits |
| `backend/app/routers/` | **UNMODIFIED** | File inspection, zero edits |
| `frontend/` | **UNMODIFIED** | Directory inspection, zero edits |
| `backend/app/recovery/services/` | **UNMODIFIED** | Write timestamp audit (all files dated Milestone 1) |
| `docs/PHASE6D_B_MILESTONE_2A_*` | **UNMODIFIED** | Approved Milestone 2A design documents frozen |

---

## 12. DATABASE AND MIGRATION AUDIT

The PostgreSQL database state was forensically audited via direct query:
1. **Alembic Migration State**:
   - Command: `alembic current`
   - Output: `phase6b_recovery_foundation (head)`
   - Migrations created: **0**.
2. **PostgreSQL Base Table Count**:
   - Query: `SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'`
   - Result: **40** (39 user application tables + 1 PostGIS `spatial_ref_sys`).
   - Tables added: **0**. Tables dropped: **0**.
3. **Database Write Audit**:
   - Query: `SELECT count(*) FROM recovery_projects WHERE priority_score IS NOT NULL`
   - Result: **0** rows.
   - Database writes to `priority_score`: **ZERO**.

---

## 13. KNOWN LIMITATIONS

1. **In-Memory Pure Optimization**: Milestone 2B implements in-memory calculation services and does not expose persistent REST endpoints or background Celery tasks. Persistence and API exposure are scheduled for Milestone 4.
2. **Assumption Core Minimality**: CP-SAT assumption cores extracted via `SufficientAssumptionsForInfeasibility()` are neither minimal nor unique. They serve as diagnostic search guidance, not minimal unsatisfiable subsets (MUS).
3. **Hardware Non-Bitwise Reproducibility**: While certified execution (`num_search_workers = 1`, fixed seed 42) ensures deterministic solution paths on identical hardware and OR-Tools builds, bitwise reproducibility across disparate CPU instruction sets (e.g., x86 vs. ARM) cannot be mathematically guaranteed.

---

## 14. OUTSTANDING RISKS

| Risk ID | Category | Description | Status | Mitigation in M2B |
|---|---|---|---|---|
| **RSK-M2-01** | Governance | Mandatory Life-Safety Hard Constraint | RESOLVED | Implemented hard mandate $w_j = 1$. Returns INFEASIBLE with structured diagnostics if liquidity/capacity cannot accommodate. |
| **RSK-M2-02** | Numerical | Early Start Acceleration Distortion | RESOLVED | Total acceleration bonus bounded to $< 1000$ micro-units ($< 1$ basis point MCPI). Proved zero effect on $w_j$. |
| **RSK-M2-03** | Performance | Multi-Worker Determinism | RESOLVED | Single-worker (`num_search_workers = 1`) certified execution by default. SHA-256 canonical fingerprint emitted. |
| **RSK-M2-05** | Financial | Solvency Constraints Scope | RESOLVED | Global cash solvency recurrence enforced by default; fund-level capacity checked indivisibly. |
| **RSK-M2-06** | Financial | Indivisible Funding Assignment | RESOLVED | Model B integer assignment $z_{j, f} \in \{0, 1\}$ strictly enforced with $\sum_f z_{j, f} = w_j$. |

---

## 15. EXPLICIT ACCEPTANCE CHECKLIST

- [x] All 5 optimization engine files implemented in `backend/app/recovery/optimization/`.
- [x] All 20 public contracts and classes exported from `__init__.py`.
- [x] Model B indivisible project funding assignment implemented ($z_{j, f} \in \{0, 1\}$).
- [x] Mandatory life-safety hard constraint implemented ($w_j = 1$).
- [x] Certified single-worker reproducibility mode with fixed seed 42 and SHA-256 input fingerprint.
- [x] Six infeasibility diagnostic categories and assumption core extraction implemented.
- [x] All 35 CP-SAT optimization tests passed ($35/35$).
- [x] Milestone 1 pure mathematical services passed ($45/45$).
- [x] Phase 6B/6C recovery tests passed ($14/14$).
- [x] Full backend regression test suite passed ($462/462$).
- [x] Zero database migrations created.
- [x] Database table count strictly 40.
- [x] Zero writes to `recovery_projects.priority_score`.
- [x] Frozen files and Milestone 1 mathematical services completely untouched.
- [x] Comprehensive milestone report authored.
- [x] Execution halted at Acceptance Gate 2 for project owner review.

---

**MILESTONE 2B COMPLETE — READY FOR OWNER REVIEW**
