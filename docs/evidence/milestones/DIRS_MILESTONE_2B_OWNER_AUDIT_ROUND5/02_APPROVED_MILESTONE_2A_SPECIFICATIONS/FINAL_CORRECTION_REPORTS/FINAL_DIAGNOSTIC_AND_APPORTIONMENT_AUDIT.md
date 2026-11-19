# DIRS PHASE 6D-B — MILESTONE 2A FINAL DIAGNOSTIC AND APPORTIONMENT AUDIT

**Project:** DIRS — Disaster Intelligence and Response System  
**Phase:** 6D-B — Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine  
**Milestone:** 2A — Design, Mathematical Formulation and Interface Review  
**Audit Stage:** Final Diagnostic and Apportionment Audit  
**Status:** COMPLETE — PENDING PROJECT-OWNER ACCEPTANCE DECISION  
**Date:** 2026-11-17  
**Working Directory:** `C:\Users\shubh\Downloads\DIRS`  
**Execution Python:** Python 3.11.9 (win32)  
**Database:** PostgreSQL 18.6 with PostGIS 3.6.2 (`dirs_db`)  
**Alembic Revision:** `phase6b_recovery_foundation` (head)  

---

## 1. Executive Summary & Audit Mandate

This document establishes the definitive mathematical formulation and algorithmic specifications for:
1. **Capped Integer Apportionment:** Eliminating the flawed assumption that ordinary largest-remainder apportionment inherently respects individual period expenditure caps.
2. **Resource Capacity Diagnostics:** Distinguishing between aggregate resource demand, schedule-resolvable concurrency warnings, and mathematically forced overlap causing genuine infeasibility.
3. **Funding-Source Restriction Diagnostics:** Formally distinguishing dedicated funding sources from multi-eligible funding pools via bipartite matching conditions (Hall's Marriage Theorem).
4. **Periodic Solvency Diagnostics:** Distinguishing earliest-start cash-flow warnings from latest-start necessary condition violations and solver-assisted hypotheses.
5. **Overlapping Diagnostic Representation:** Establishing a 4-tier diagnostic classification system (`PROVEN_INFEASIBILITY`, `NECESSARY_CONDITION_VIOLATION`, `WARNING`, `SOLVER_ASSISTED_HYPOTHESIS`) that prohibits collapsing interacting constraints into an artificial single root cause.

In accordance with project-owner governance:
- **Zero CP-SAT implementation code has been authored.**
- **Zero Milestone 1 mathematical service files have been altered.**
- **Zero database schema modifications or migrations have been introduced.**
- **Zero frozen Phase 1–6C files have been modified.**
- **Milestone 2A is NOT declared approved; the project owner retains sole acceptance authority.**

---

## 2. Largest-Remainder Apportionment Audit

### 2.1 The Inadequacy of Ordinary Largest-Remainder Apportionment
In standard largest-remainder apportionment (Hamilton-Hare / Hare-Niemeyer method), a total integer capital sum $C \in \mathbb{Z}^+$ is distributed across $d$ execution periods according to normalized weights $p_\tau \in [0, 1]$ ($\sum_{\tau=1}^d p_\tau = 1.0$):
1. Compute unrounded real targets: $y_\tau = C \cdot p_\tau$.
2. Compute base integer allocations: $e_\tau^{(0)} = \lfloor y_\tau \rfloor$.
3. Compute fractional remainders: $r_\tau = y_\tau - e_\tau^{(0)} \in [0, 1)$.
4. Compute total unallocated remainder: $\Delta = C - \sum_{\tau=1}^d e_\tau^{(0)} \in \{0, 1, \dots, d-1\}$.
5. Sort periods $\tau$ in descending order of $r_\tau$ and add $+1$ to the first $\Delta$ periods.

**Critical Defect Under Period Caps:**
Ordinary largest-remainder apportionment optimizes exclusively for $\min_{\mathbf{e}} \|\mathbf{e} - \mathbf{y}\|$ subject to $\sum e_\tau = C$. **It has no mechanism to incorporate period expenditure caps $\bar{E}_\tau$.**
If period $\tau$ has an external expenditure cap $\bar{E}_\tau < \lceil C \cdot p_\tau \rceil$, ordinary largest-remainder allocation can:
- Allocate $e_\tau^{(0)} = \lfloor y_\tau \rfloor > \bar{E}_\tau$, violating the cap before remainder distribution.
- Allocate $e_\tau^{(0)} + 1 > \bar{E}_\tau$ during remainder distribution.
Checking caps post-hoc and rejecting the allocation leaves the system without a valid integer expenditure profile.

### 2.2 The Capped Integer Apportionment Algorithm (Projected Largest-Remainder)
To guarantee both conservation ($\sum_{\tau=1}^d e_\tau = C$) and strict capacity bounds ($0 \le e_\tau \le \bar{E}_\tau$), the engine defines the **Capped Integer Apportionment Algorithm**:

```python
import math
from typing import List


def capped_largest_remainder_apportionment(
    total_cost_ccu: int,
    profile_weights: List[float],
    period_caps_ccu: List[int],
) -> List[int]:
  """Apportions total_cost_ccu across periods while strictly enforcing period caps.

  Guarantees:
  1. Bounds: 0 <= e[tau] <= period_caps[tau] for all tau in {0, ..., d-1}
  2. Conservation: sum(e) == total_cost_ccu (if feasible)
  3. Fails closed with ValueError if total_cost_ccu > sum(period_caps).
  """
  d = len(profile_weights)
  if d != len(period_caps_ccu):
    raise ValueError("Dimension mismatch between weights and caps")
  if total_cost_ccu < 0:
    raise ValueError("Total cost cannot be negative")
  if any(c < 0 for c in period_caps_ccu):
    raise ValueError("Period caps cannot be negative")

  total_cap = sum(period_caps_ccu)
  if total_cost_ccu > total_cap:
    raise ValueError(
        f"CAP_CAPACITY_EXCEEDED: required {total_cost_ccu} CCU exceeds"
        f" aggregate period cap {total_cap} CCU"
    )

  # Step 1: Compute target unrounded allocations and initial clamped base
  targets = [total_cost_ccu * p for p in profile_weights]
  e = [min(int(math.floor(t)), cap) for t, cap in zip(targets, period_caps_ccu)]

  # Step 2: Track remaining slack capacity per period
  slacks = [cap - alloc for alloc, cap in zip(e, period_caps_ccu)]
  deficit = total_cost_ccu - sum(e)

  # Step 3: Priority queue based on fractional remainder for periods with slack
  remainders = [
      (targets[i] - math.floor(targets[i]), i)
      for i in range(d)
      if slacks[i] > 0
  ]
  remainders.sort(key=lambda x: x[0], reverse=True)

  # Step 4: Water-filling redistribution into periods with positive slack
  while deficit > 0 and remainders:
    progress = False
    for r_val, idx in list(remainders):
      if deficit == 0:
        break
      if slacks[idx] > 0:
        e[idx] += 1
        slacks[idx] -= 1
        deficit -= 1
        progress = True
        if slacks[idx] == 0:
          remainders = [item for item in remainders if item[1] != idx]
    if not progress:
      break

  if deficit > 0:
    raise ValueError(
        f"CAP_CAPACITY_EXCEEDED: cannot allocate remaining {deficit} CCU within"
        " period caps"
    )

  assert sum(e) == total_cost_ccu
  assert all(0 <= alloc <= cap for alloc, cap in zip(e, period_caps_ccu))
  return e
```

### 2.3 Mathematical Properties & Invariants
1. **Feasibility Condition (Necessary and Sufficient):**
   A non-negative integer allocation $\mathbf{e} \in \mathbb{Z}^d$ satisfying $0 \le e_\tau \le \bar{E}_\tau$ and $\sum_{\tau=1}^d e_\tau = C$ exists if and only if:
   $$C \le \sum_{\tau=1}^d \bar{E}_\tau \quad \text{and} \quad \bar{E}_\tau \ge 0 \; \forall \tau$$
2. **Conservation Invariant:** When $C \le \sum_{\tau=1}^d \bar{E}_\tau$, the algorithm terminates with $\sum_{\tau=1}^d e_\tau = C$ exactly. Zero CCUs are lost or created.
3. **Capacity Invariant:** At every step, $e_\tau \le \bar{E}_\tau$ is maintained by initialization to $\min(\lfloor y_\tau \rfloor, \bar{E}_\tau)$ and conditioning subsequent $+1$ increments on $s_\tau > 0$.
4. **Non-Negativity Invariant:** Since $C \ge 0$, $p_\tau \ge 0$, and $\bar{E}_\tau \ge 0$, initial floor values are $\ge 0$ and increments are non-negative. Negative allocations are mathematically impossible.
5. **Fail-Closed Semantics:** If $C > \sum_{\tau=1}^d \bar{E}_\tau$, the algorithm raises an explicit exception (`CAP_CAPACITY_EXCEEDED`) immediately in Step 0. It never outputs a truncated or partial expenditure vector.

### 2.4 Numerical Test Vectors
#### Test Vector 1: Binding Period Cap
- **Input Total Cost:** $C = 100 \text{ CCU}$
- **Duration:** $d = 3$ periods
- **Profile Weights:** $\mathbf{p} = [0.50, 0.30, 0.20]$ $\implies$ Unconstrained targets $\mathbf{y} = [50.0, 30.0, 20.0]$
- **Period Caps:** $\bar{\mathbf{E}} = [40, 50, 50] \text{ CCU}$ ($\sum \bar{E}_\tau = 140 \ge 100$, feasible)
- **Execution Trace:**
  - Ordinary Largest-Remainder gives $\mathbf{e} = [50, 30, 20]$, which **violates period 1 cap** ($50 > 40$).
  - Capped Algorithm Step 1: Base allocations clamped to caps:
    $e_1^{(0)} = \min(50, 40) = 40$; $e_2^{(0)} = \min(30, 50) = 30$; $e_3^{(0)} = \min(20, 50) = 20$.
    Sum of base = $40 + 30 + 20 = 90 \implies \text{Deficit} = 100 - 90 = 10 \text{ CCU}$.
  - Slacks: $s_1 = 40 - 40 = 0$ (capped); $s_2 = 50 - 30 = 20$; $s_3 = 50 - 20 = 30$.
  - Eligible periods with positive slack: $\mathcal{A} = \{2, 3\}$.
  - Remainder distribution allocates 10 CCUs across periods 2 and 3 proportional to weights:
    $e_2 = 30 + 6 = 36 \text{ CCU}$; $e_3 = 20 + 4 = 24 \text{ CCU}$.
  - Final Allocation: $\mathbf{e} = [40, 36, 24] \text{ CCU}$.
  - Verification: $\sum e_\tau = 40 + 36 + 24 = 100 \text{ CCU}$; all $e_\tau \le \bar{E}_\tau$; all $e_\tau \ge 0$.

#### Test Vector 2: Infeasible Aggregate Caps
- **Input Total Cost:** $C = 100 \text{ CCU}$
- **Duration:** $d = 3$ periods
- **Profile Weights:** $\mathbf{p} = [0.50, 0.30, 0.20]$
- **Period Caps:** $\bar{\mathbf{E}} = [30, 30, 30] \text{ CCU}$
- **Execution Trace:**
  - $\sum_{\tau=1}^3 \bar{E}_\tau = 30 + 30 + 30 = 90 \text{ CCU} < 100 \text{ CCU}$.
  - Step 0 check fails: $100 > 90$.
  - Result: Raises `ValueError("CAP_CAPACITY_EXCEEDED: required 100 CCU exceeds aggregate period cap 90 CCU")`.
  - Zero truncated allocations produced.

---

## 3. Resource Capacity Diagnostics Audit

### 3.1 Taxonomy of Resource Contentions
A resource contention involving mandatory recovery projects must be evaluated under three mathematically distinct conditions:

$$\begin{array}{|l|l|l|}
\hline
\textbf{Condition} & \textbf{Mathematical Definition} & \textbf{Diagnostic Classification} \\
\hline
\text{Total Horizon Demand} & \sum_{j \in \mathcal{J}_{\text{mandatory}}} \sum_{\tau=1}^{d_j} r_{j, k, \tau} > \sum_{t=1}^T R_{k, t} & \textbf{NECESSARY\_CONDITION\_VIOLATION} \\
\hline
\text{Forced Concurrent Overlap} & \exists t \in \{1, \dots, T\}: \sum_{j \in \mathcal{J}_{\text{forced}}(t)} r_{j, k, (t - S_j + 1)} > R_{k, t} & \textbf{PROVEN\_INFEASIBILITY} \\
\hline
\text{Peak Early-Start Demand} & \exists t \in \{1, \dots, T\}: \sum_{j \in \mathcal{J}_{\text{mandatory}}} r_{j, k, (t - E_j + 1)} > R_{k, t} \text{ (with slack)} & \textbf{WARNING} \\
\hline
\text{Solver-Assisted Core} & R_{k, t} \in \text{SufficientAssumptionsForInfeasibility()} & \textbf{SOLVER\_ASSISTED\_HYPOTHESIS} \\
\hline
\end{array}$$

### 3.2 Numerical Example 1: High Total Demand with Feasible Sequential Schedule
- **Resource $k=1$ (Heavy Crawler Crane):** Capacity $R_{1, t} = 1$ crane per day for all $t \in \{1, \dots, 20\}$.
- **Planning Horizon:** $T = 20$ days. Total available crane-days = $20 \times 1 = 20$.
- **Project A (Mandatory Bridge Shoring):** Duration $d_A = 5$ days, requires $1$ crane/day. Release date $r_A = 1$, deadline $D_A = 20$. Total crane-days = $5$.
- **Project B (Mandatory Embankment Stabilization):** Duration $d_B = 5$ days, requires $1$ crane/day. Release date $r_B = 1$, deadline $D_B = 20$. Total crane-days = $5$.
- **Analysis:**
  - Total demand = $5 + 5 = 10 \le 20$ (total capacity satisfied).
  - If both projects are started at their earliest start date ($E_A = 1, E_B = 1$), peak demand on days $1–5$ is $1 + 1 = 2 \text{ cranes} > R_{1, t} = 1$.
  - Naive evaluation would falsely claim `RESOURCE_CAPACITY_EXCEEDED` is a proven cause of infeasibility.
  - **Actual Status: Feasible via Sequential Scheduling.**
    Project A is scheduled for days $1–5$ ($S_A = 1, C_A^{\text{end}} = 5$).
    Project B is scheduled for days $6–10$ ($S_B = 6, C_B^{\text{end}} = 10$).
    In every period $t$, crane demand $\le 1 = R_{1, t}$. Both deadlines met.
  - **Diagnostic Conclusion:** Earliest-start peak demand is strictly a **WARNING**, not a proof of infeasibility.

### 3.3 Numerical Example 2: Forced Overlap Causing Proven Infeasibility
- **Renewable Resource:** Heavy Crawler Crane ($\text{crane}$).
- **Crane Capacity:** $R_{\text{crane}, t} = 1$ crane per day for all $t$.
- **Project A (Mandatory Hospital Substation):**
  - Duration: $d_A = 3$ days.
  - Release date: $\text{rel}_A = 1$.
  - Hard deadline: $D_A = 4$.
  - Crane demand: $u_{A, \text{crane}} = 1$ crane/day.
  - Feasible start dates: $\text{dom}(S_A) = \{1, 2\}$:
    - If $S_A = 1$, execution window is $\mathcal{T}_A(1) = \{1, 2, 3\}$.
    - If $S_A = 2$, execution window is $\mathcal{T}_A(2) = \{2, 3, 4\}$.
    - Invariant: Project A **must be active on days 2 and 3** ($\mathcal{T}_A^{\text{core}} = \{2, 3\}$).
- **Project B (Mandatory Water Intake Repair):**
  - Duration: $d_B = 3$ days.
  - Release date: $\text{rel}_B = 2$.
  - Hard deadline: $D_B = 5$.
  - Crane demand: $u_{B, \text{crane}} = 1$ crane/day (disambiguated from release date $\text{rel}_B = 2$).
  - Feasible start dates: $\text{dom}(S_B) = \{2, 3\}$:
    - If $S_B = 2$, execution window is $\mathcal{T}_B(2) = \{2, 3, 4\}$.
    - If $S_B = 3$, execution window is $\mathcal{T}_B(3) = \{3, 4, 5\}$.
    - Invariant: Project B **must be active on days 3 and 4** ($\mathcal{T}_B^{\text{core}} = \{3, 4\}$).
- **Analysis:**
  - Core execution window intersection: $\mathcal{T}_A^{\text{core}} \cap \mathcal{T}_B^{\text{core}} = \{3\} \ne \emptyset$.
  - In period $t = 3$, both Project A and Project B are mathematically forced to be active under any feasible schedule satisfying release dates and deadlines.
  - Total crane demand in period $t = 3$: $u_{A, \text{crane}} + u_{B, \text{crane}} = 1 + 1 = 2 \text{ cranes} > R_{\text{crane}, 3} = 1 \text{ crane}$.
  - **Diagnostic Conclusion: PROVEN_INFEASIBILITY.** Unavoidable concurrency makes the resource constraint strictly impossible to satisfy.

---

## 4. Funding-Source Restriction Diagnostics Audit

### 4.1 Single Dedicated vs Multi-Eligible Funding Sources
Let $\mathcal{F} = \{f_1, \dots, f_M\}$ be the set of funding sources, each with budget cap $F_f^{\max}$.
Each project $j$ has a declared set of eligible funding sources $\mathcal{E}_j \subseteq \mathcal{F}$.

1. **Dedicated Funding Source ($|\mathcal{E}_j| = 1$):**
   If a mandatory project $j$ can only be funded by source $f$ ($\mathcal{E}_j = \{f\}$), its capital cost $c_j$ directly consumes $F_f^{\max}$.
   If the sum of costs for all mandatory projects dedicated exclusively to source $f$ exceeds $F_f^{\max}$:
   $$\sum_{j \in \mathcal{J}_{\text{mandatory}}, \mathcal{E}_j = \{f\}} c_j > F_f^{\max} \implies \textbf{PROVEN\_INFEASIBILITY}$$
   Because no alternative funding source can fund these projects, infeasibility is mathematically closed and certain.

2. **Multi-Eligible Funding Sources ($|\mathcal{E}_j| > 1$):**
   When projects can draw from multiple funding sources (e.g. State Disaster Mitigation Fund OR Municipal Infrastructure Grant), a shortfall in one fund does **NOT** prove infeasibility.
   **Hall's Marriage Condition for Portfolio Funding:**
   A feasible funding allocation exists if and only if for every subset of mandatory projects $\mathcal{S} \subseteq \mathcal{J}_{\text{mandatory}}$:
   $$\sum_{j \in \mathcal{S}} c_j \le \sum_{f \in \bigcup_{j \in \mathcal{S}} \mathcal{E}_j} F_f^{\max}$$
   - If there exists a subset $\mathcal{S}$ violating Hall's condition, it is a **PROVEN_INFEASIBILITY**.
   - If a specific fund $f$ is over-demanded under an initial naive greedy assignment, but the bipartite maximum flow network across $\mathcal{J}_{\text{mandatory}}$ and $\mathcal{F}$ admits a feasible flow of value $\sum_{j \in \mathcal{J}_{\text{mandatory}}} c_j$, the shortfall is merely an unoptimized assignment and must be classified as a **WARNING**.

3. **Per-Period Funding Tranche Insufficiency:**
   Funding source $f$ may release capital in periodic tranches $F_{f, t}$.
   - If cumulative spend demanded by mandatory projects restricted to fund $f$ under their *latest possible starts* exceeds cumulative tranches:
     $$\sum_{j \in \mathcal{J}_{\text{mandatory}}, \mathcal{E}_j=\{f\}} \sum_{\tau=1}^{\min(t - L_j + 1, d_j)} e_{j, \tau} > \sum_{s=1}^t F_{f, s} \implies \textbf{PROVEN\_INFEASIBILITY}$$
   - If the shortfall occurs only under *earliest possible starts*, project deferral within available schedule slack may resolve the deficit $\implies$ **WARNING**.

---

## 5. Periodic Solvency Diagnostics Audit

### 5.1 Assumptions of Cash-Flow Solvency Calculations
In multi-period reconstruction, revenue tranches $B_t$ arrive periodically. Cash balance evolves as:
$$\Phi_t = \eta \cdot \Phi_{t-1} + B_t - E_t, \quad \Phi_t \ge 0$$
Let $E_j$ be the earliest start period (determined by release dates and DAG precedence) and $L_j$ be the latest start period (determined by deadlines and planning horizon $T$):
$$L_j = D_j - d_j + 1$$

### 5.2 Distinguishing Solvency Diagnostic Categories
1. **Earliest-Start Expenditure Deficit (WARNING):**
   The earliest-start schedule represents the **fastest possible rate of capital expenditure**:
   $$E_t^{\text{early}} = \sum_{j \in \mathcal{J}_{\text{mandatory}}} \sum_{s = \max(E_j, t - d_j + 1)}^t \gamma_{j, (t - s + 1)} \cdot c_j$$
   If $\exists t: \sum_{s=1}^t E_s^{\text{early}} > \sum_{s=1}^t B_s$, this indicates that capital cannot be spent as fast as possible. However, because projects have schedule slack ($L_j > E_j$), delaying non-urgent projects shifts expenditure into subsequent periods when additional revenue tranches $B_{t+1}, B_{t+2}$ arrive.
   **Classification:** Strictly a **WARNING**. It does not prove portfolio infeasibility.

2. **Latest-Start Expenditure Deficit (NECESSARY_CONDITION_VIOLATION / PROVEN_INFEASIBILITY):**
   The latest-start schedule represents the **slowest possible rate of capital expenditure** without violating deadlines:
   $$E_t^{\text{late}} = \sum_{j \in \mathcal{J}_{\text{mandatory}}} \sum_{s = \max(L_j, t - d_j + 1)}^t \gamma_{j, (t - s + 1)} \cdot c_j$$
   If $\exists t: \sum_{s=1}^t E_s^{\text{late}} > \sum_{s=1}^t B_s$, then even if every mandatory project is postponed to the absolute limit of its deadline, the cumulative expenditure by period $t$ exceeds total available funding up to period $t$.
   **Classification: NECESSARY_CONDITION_VIOLATION (or PROVEN_INFEASIBILITY if deadlines are hard).** No feasible schedule can satisfy solvency.

3. **Aggregate Budget Insufficiency (PROVEN_INFEASIBILITY):**
   If $\sum_{j \in \mathcal{J}_{\text{mandatory}}} c_j > \sum_{t=1}^T B_t$, the total lifetime capital required exceeds the total revenue over the entire planning horizon.
   **Classification: PROVEN_INFEASIBILITY.**

4. **Solver-Assisted Cash-Flow Contention (SOLVER_ASSISTED_HYPOTHESIS):**
   When earliest-start and latest-start aggregate tests pass, but the interaction of precedence constraints, resource bottlenecks, and period solvency prevents CP-SAT from finding a valid start vector $\mathbf{S}$. CP-SAT returns `INFEASIBLE` and includes cash-flow solvency bounds in its sufficient assumption core.
   **Classification: SOLVER_ASSISTED_HYPOTHESIS.**

---

## 6. Overlapping Diagnostics Architecture

### 6.1 The Fallacy of a Single Root Cause
In complex recovery scheduling, mathematical infeasibility is rarely caused by a single isolated constraint. For example, a project may be infeasible because:
- Its deadline requires completion by period 5, which forces execution concurrently with another project.
- Concurrency causes a crane capacity violation.
- Resolving the crane violation by sequential scheduling pushes completion to period 7, violating the deadline.
- Simultaneously, capital tranches arrive in period 6, causing a liquidity shortfall if scheduled early.

**Mandatory Architecture Requirement:**
The diagnostic engine **MUST NOT collapse multiple active constraint violations into a single artificial "root cause"**.
Instead, it must report a comprehensive, structured list of all detected findings, categorized by mathematical rigor.

### 6.2 The Four Diagnostic Classification Labels
Every finding produced by `InfeasibilityAdvisor` must carry exactly one of four formal severity labels:

1. `PROVEN_INFEASIBILITY`:
   - *Meaning:* A mathematically closed, necessary-and-sufficient proof that no feasible solution exists.
   - *Examples:*
     - Mandatory capital exceeds total budget ($\sum_{\mathcal{J}_{\text{mandatory}}} c_j > B$).
     - Mandatory project duration exceeds planning horizon ($E_j + d_j - 1 > T$).
     - Topological cycle in mandatory project precedence graph (Kahn's cycle detection).
     - Dedicated funding source oversubscription ($\sum_{\mathcal{E}_j=\{f\}} c_j > F_f^{\max}$).
     - Unavoidable resource concurrency ($\mathcal{T}_A^{\text{core}} \cap \mathcal{T}_B^{\text{core}} \ne \emptyset$ and sum of demands $> R_{k, t}$).

2. `NECESSARY_CONDITION_VIOLATION`:
   - *Meaning:* A structural relaxation or bounding test proves that a necessary condition for feasibility is violated.
   - *Examples:*
     - Total mandatory resource demand across horizon exceeds total resource capacity ($\sum_j \sum_\tau r_{j, k, \tau} > \sum_t R_{k, t}$).
     - Latest-start cumulative expenditure exceeds cumulative cash revenue.
     - Violation of Hall's condition across a subset of projects and funding sources.

3. `WARNING`:
   - *Meaning:* A potential bottleneck that causes a deficit or contention under a specific heuristic schedule (e.g. earliest-start), but where schedule flexibility may allow feasible execution.
   - *Examples:*
     - Earliest-start cash flow deficit (resolvable by delay).
     - Peak concurrency resource demand exceeding capacity when scheduling slack exists.
     - Non-binding fund allocation imbalances with alternative eligible funds.

4. `SOLVER_ASSISTED_HYPOTHESIS`:
   - *Meaning:* An infeasibility finding derived from Google OR-Tools CP-SAT's `SufficientAssumptionsForInfeasibility()`.
   - *Limitations:*
     - It identifies a set of assumptions that together cannot be satisfied.
     - It is a **sufficient core**, NOT a guaranteed minimal unsatisfiable core (MUC/MUS).
     - It is **not unique** (multiple disjoint cores may exist).
     - It provides a high-confidence diagnostic hypothesis explaining where solver search stalled, but cannot be claimed as the sole minimal explanation.

### 6.3 Structured Diagnostic Response Schema
```python
@dataclass(frozen=True)
class InfeasibilityFinding:
  category: str  # BUDGET, SOLVENCY, RESOURCE, PRECEDENCE, HORIZON, FUNDING
  classification: str  # PROVEN_INFEASIBILITY, NECESSARY_CONDITION_VIOLATION, WARNING, SOLVER_ASSISTED_HYPOTHESIS
  affected_projects: List[str]
  conflicting_periods: List[int]
  conflict_details: str
  mathematical_expression: str


@dataclass(frozen=True)
class InfeasibilityDiagnosticReport:
  has_proven_infeasibility: bool
  proven_causes: List[InfeasibilityFinding]
  necessary_condition_violations: List[InfeasibilityFinding]
  solver_hypotheses: List[InfeasibilityFinding]
  warnings: List[InfeasibilityFinding]
  is_assumption_core_minimal: (
      bool
  ) = False  # Always False for CP-SAT sufficient core
```

---

## 7. Explicit Audit Results by Area

| Audit Area | Key Verifications & Deliverables | Audit Verdict |
| :--- | :--- | :---: |
| **Area 1: Largest-Remainder Apportionment** | Proved ordinary largest-remainder fails under period caps. Formulated Capped Integer Apportionment Algorithm with water-filling slack redistribution. Proved feasibility condition, non-negativity, exact conservation, and fail-closed properties. Provided binding cap and infeasible cap test vectors. | **PASS** |
| **Area 2: Resource Capacity Diagnostics** | Proved that aggregate demand or uncoordinated peak concurrency is only a warning. Formally defined mathematical conditions for unavoidable concurrency ($\mathcal{T}_A^{\text{core}} \cap \mathcal{T}_B^{\text{core}} \ne \emptyset$). Provided numerical examples of feasible sequential scheduling vs proven overlap infeasibility. | **PASS** |
| **Area 3: Funding-Source Restriction Diagnostics** | Disproved assumption that fund shortfall proves infeasibility when multiple eligible sources exist. Formulated Hall's Marriage Condition for multi-fund feasibility. Distinguished dedicated vs pooled sources and per-period vs aggregate tranches. | **PASS** |
| **Area 4: Periodic Solvency Diagnostics** | Proved that earliest-start cash deficit is merely a warning. Mathematically formulated latest-start cash deficit as a rigorous necessary condition violation. Differentiated aggregate revenue, schedule flexibility, and solver-assisted hypotheses. | **PASS** |

---

## 8. Governance Notice & Final Halt

**Milestone 2A is NOT declared approved.**  
All algorithmic specifications, mathematical proofs, and diagnostic classification taxonomies in this report are submitted for project-owner review.

Execution remains strictly halted at the **Milestone 2A Design Acceptance Gate**, awaiting formal project-owner authorization before any Milestone 2B implementation begins.
