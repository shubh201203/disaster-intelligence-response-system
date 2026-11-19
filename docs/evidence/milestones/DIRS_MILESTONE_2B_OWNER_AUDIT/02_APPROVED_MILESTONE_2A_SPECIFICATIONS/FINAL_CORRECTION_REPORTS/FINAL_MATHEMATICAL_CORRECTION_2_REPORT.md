# DIRS PHASE 6D-B — FINAL MATHEMATICAL CORRECTIONS TO MILESTONE 2A

**Project:** DIRS — Disaster Intelligence and Response System  
**Phase:** 6D-B — Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine  
**Milestone:** 2A — Design, Mathematical Formulation and Interface Review  
**Stage:** Final Mathematical Corrections and Rigorous Foundations  
**Status:** COMPLETE — PENDING PROJECT-OWNER ACCEPTANCE DECISION  
**Date:** 2026-11-17  
**Working Directory:** `C:\Users\shubh\Downloads\DIRS`  
**Execution Python:** Python 3.11.9 (win32)  
**Database:** PostgreSQL 18.6 with PostGIS 3.6.2 (`dirs_db`)  
**Alembic Revision:** `phase6b_recovery_foundation` (head)  

---

## 1. Executive Summary & Audit Mandate

This report delivers the authoritative mathematical corrections and rigorous proofs requested for Milestone 2A:
1. **Deterministic Capped Integer Apportionment:** Complete formalization of the algorithm with explicit rational targets, deterministic secondary tie-breaking, termination proof, fail-closed mechanics, and proof of the necessary and sufficient feasibility condition.
2. **Forced-Overlap Resource Capacity Diagnostics:** Correction of the duration-to-period occupancy mapping under non-preemptive scheduling, providing a valid feasible sequential schedule and a mathematically closed forced-overlap infeasibility proof.
3. **Funding-Source Feasibility Model & Project-Owner Decision Record:** Formal distinction between Divisible Co-Funding (bipartite max-flow / Hall's condition) and Indivisible Project Assignment (NP-complete generalized assignment / bin-packing), including a numerical counterexample where Hall's condition holds but indivisible assignment is strictly infeasible.
4. **Periodic Solvency Lower Bound Proof:** Formal proof of monotonicity (Lemma 1) establishing that backward-pass CPM latest-start schedules provide a mathematically sound relaxation-based lower bound on cumulative expenditure, accompanied by four concrete numerical examples.
5. **Diagnostic Label Governance:** Strict operational definitions for the four-tier diagnostic hierarchy (`PROVEN_INFEASIBILITY`, `NECESSARY_CONDITION_VIOLATION`, `WARNING`, `SOLVER_ASSISTED_HYPOTHESIS`), prohibiting artificial single-root-cause compression and disclaiming minimality/uniqueness for CP-SAT sufficient assumption cores.

In strict compliance with governance rules:
- **Zero CP-SAT implementation code has been authored.**
- **Zero Milestone 1 mathematical service files have been altered.**
- **Zero database schema modifications or migrations have been introduced.**
- **Zero files in frozen phases (Phases 1–6C) have been modified.**
- **Milestone 2A is NOT declared approved; the project owner retains sole acceptance authority.**

---

## 2. Issue 1 — Formalization of Deterministic Capped Integer Apportionment

### 2.1 Formal Problem Definition
Let:
- $C \in \mathbb{Z}_{\ge 0}$: Integer total project capital cost in Canonical Currency Units (CCU, where $1 \text{ CCU} = 10^{-5} \text{ INR}$).
- $d \in \mathbb{Z}^+$: Project duration in discrete calendar periods. Periods are indexed $\tau \in \{1, \dots, d\}$.
- $\mathcal{K} \subseteq \{1, \dots, d\}$: Set of explicit eligible execution periods ($|\mathcal{K}| \ge 1$). Periods $\tau \notin \mathcal{K}$ are ineligible.
- $\bar{\mathbf{E}} = (\bar{E}_1, \dots, \bar{E}_d) \in \mathbb{Z}_{\ge 0}^d$: Non-negative integer period expenditure caps. For all $\tau \notin \mathcal{K}$, $\bar{E}_\tau \equiv 0$.
- $\mathbf{w} = (w_1, \dots, w_d) \in \mathbb{Q}_{\ge 0}^d$: Exact rational execution profile weights. Let $W_{\mathcal{K}} = \sum_{\tau \in \mathcal{K}} w_\tau > 0$. The normalized rational proportion is $q_\tau = \frac{w_\tau}{W_{\mathcal{K}}}$ for $\tau \in \mathcal{K}$, and $q_\tau = 0$ for $\tau \notin \mathcal{K}$.

**Required Output:**
An integer allocation vector $\mathbf{e} = (e_1, \dots, e_d) \in \mathbb{Z}_{\ge 0}^d$ satisfying:
1. *Non-Negativity:* $e_\tau \ge 0 \quad \forall \tau \in \{1, \dots, d\}$.
2. *Eligibility:* $e_\tau = 0 \quad \forall \tau \notin \mathcal{K}$.
3. *Capacity Non-Violation:* $e_\tau \le \bar{E}_\tau \quad \forall \tau \in \{1, \dots, d\}$.
4. *Exact Conservation:* $\sum_{\tau=1}^d e_\tau = \sum_{\tau \in \mathcal{K}} e_\tau = C$.

### 2.2 Proof of Necessary and Sufficient Feasibility Condition
**Theorem 1:** Under the stated assumptions, a non-negative integer allocation vector $\mathbf{e} \in \mathbb{Z}_{\ge 0}^d$ satisfying conditions (1)–(4) exists if and only if:
$$\sum_{\tau \in \mathcal{K}} \bar{E}_\tau \ge C$$

*Proof:*
- **Necessity:** Suppose a valid integer allocation $\mathbf{e}$ exists. By conditions (1), (2), and (3), $0 \le e_\tau \le \bar{E}_\tau$ for all $\tau \in \mathcal{K}$, and $e_\tau = 0$ for $\tau \notin \mathcal{K}$. Summing over all periods:
  $$C = \sum_{\tau=1}^d e_\tau = \sum_{\tau \in \mathcal{K}} e_\tau \le \sum_{\tau \in \mathcal{K}} \bar{E}_\tau$$
  Hence, $\sum_{\tau \in \mathcal{K}} \bar{E}_\tau \ge C$ is strictly necessary.
- **Sufficiency:** Suppose $\sum_{\tau \in \mathcal{K}} \bar{E}_\tau \ge C$. Consider the greedy prefix allocation over an arbitrary indexing of $\mathcal{K} = \{\tau_1, \tau_2, \dots, \tau_K\}$:
  $$e_{\tau_1} = \min(C, \bar{E}_{\tau_1})$$
  $$e_{\tau_k} = \min\left(C - \sum_{i=1}^{k-1} e_{\tau_i}, \; \bar{E}_{\tau_k}\right) \quad \text{for } k = 2, \dots, K$$
  Since $C \in \mathbb{Z}_{\ge 0}$ and $\bar{E}_\tau \in \mathbb{Z}_{\ge 0}$, each $e_{\tau_k}$ is an integer. By construction, $0 \le e_{\tau_k} \le \bar{E}_{\tau_k}$.
  The accumulated sum $\sum_{i=1}^k e_{\tau_i}$ reaches $\min(C, \sum_{i=1}^k \bar{E}_{\tau_i})$. Since $\sum_{i=1}^K \bar{E}_{\tau_i} \ge C$, the total sum reaches $C$ at or before $k = K$.
  Setting $e_\tau = 0$ for $\tau \notin \mathcal{K}$ yields an integer vector satisfying (1)–(4). Thus sufficiency is proved. $\blacksquare$

### 2.3 Deterministic Capped Apportionment Algorithm Specification
To ensure **reproducible, unique output**, we specify the exact algorithm with deterministic secondary tie-breaking:

```python
from decimal import Decimal
from fractions import Fraction
import math
from typing import List, Set


def deterministic_capped_apportionment(
    cost_c: int,
    weights_w: List[Fraction],
    caps_e_bar: List[int],
    eligible_periods: Set[int],
) -> List[int]:
  """Computes unique, deterministic integer expenditure apportionment under period caps.

  Args:
      cost_c: Total integer CCU project cost.
      weights_w: List of exact rational weights w_tau (length d).
      caps_e_bar: List of non-negative integer period caps (length d).
      eligible_periods: Set of 1-based period indices permitted for allocation.

  Returns:
      List[int]: Deterministic integer allocation vector e of length d.

  Raises:
      ValueError: If cost_c < 0, caps < 0, or aggregate eligible capacity <
      cost_c.
  """
  d = len(weights_w)
  if len(caps_e_bar) != d:
    raise ValueError("Dimension mismatch between weights and caps.")
  if cost_c < 0:
    raise ValueError("Project cost cannot be negative.")
  if any(c < 0 for c in caps_e_bar):
    raise ValueError("Period caps cannot be negative.")

  # 1. Enforce eligibility mask: period caps outside eligible_periods are strictly 0
  effective_caps = [
      caps_e_bar[i] if (i + 1) in eligible_periods else 0 for i in range(d)
  ]
  total_eligible_capacity = sum(effective_caps)

  # 2. Strict Fail-Closed Check (Theorem 1)
  if cost_c > total_eligible_capacity:
    raise ValueError(
        f"CAP_CAPACITY_EXCEEDED: required {cost_c} CCU exceeds aggregate"
        f" eligible capacity {total_eligible_capacity} CCU"
    )

  if cost_c == 0:
    return [0] * d

  # 3. Compute normalized rational targets
  W_eligible = sum(
      weights_w[i] for i in range(d) if (i + 1) in eligible_periods
  )
  if W_eligible == 0:
    raise ValueError("Sum of weights across eligible periods cannot be zero.")

  targets = [
      (
          Fraction(cost_c * weights_w[i], W_eligible)
          if (i + 1) in eligible_periods
          else Fraction(0, 1)
      )
      for i in range(d)
  ]

  # 4. Clamped Integer Base Allocation
  # e_tau^(0) = min( floor(y_tau), effective_cap_tau )
  e = [min(int(targets[i]), effective_caps[i]) for i in range(d)]

  # 5. Compute Slacks, Fractional Remainders, and Deficit
  slacks = [effective_caps[i] - e[i] for i in range(d)]
  deficit = cost_c - sum(e)

  # 6. Deterministic Priority Ranking
  # Primary Key: Fractional remainder (targets[i] - floor(targets[i])) descending
  # Secondary Deterministic Tie-Breaker: Ascending period index (i + 1)
  # Only periods with positive slack (slacks[i] > 0) are candidates.
  candidate_indices = [
      i for i in range(d) if (i + 1) in eligible_periods and slacks[i] > 0
  ]

  # Sort by: (-remainder, period_index)
  candidate_indices.sort(
      key=lambda i: (-(targets[i] - Fraction(int(targets[i]), 1)), i)
  )

  # 7. Water-Filling Round-Robin Redistribution
  # Cycles deterministically through candidate_indices while deficit > 0
  while deficit > 0:
    progress = False
    for idx in list(candidate_indices):
      if deficit == 0:
        break
      if slacks[idx] > 0:
        e[idx] += 1
        slacks[idx] -= 1
        deficit -= 1
        progress = True
        if slacks[idx] == 0:
          candidate_indices.remove(idx)
    if not progress:
      # Mathematically impossible by Theorem 1, but fail-closed invariant
      raise RuntimeError(
          f"Internal apportionment failure: unallocated deficit {deficit} CCU."
      )

  # 8. Post-Condition Verification
  assert sum(e) == cost_c, "Conservation violated."
  assert all(0 <= e[i] <= effective_caps[i] for i in range(d)), (
      "Cap violated."
  )
  assert all(e[i] == 0 for i in range(d) if (i + 1) not in eligible_periods), (
      "Ineligible period received allocation."
  )

  return e
```

### 2.4 Termination and Uniqueness Proofs
1. **Termination Proof:** The loop in Step 7 decrements `deficit` by 1 upon each unit assignment. Since `deficit` is an integer initialized to $C - \sum e^{(0)} \le C < \infty$, the loop terminates in at most `deficit` iterations. By Theorem 1, $\sum_{\tau \in \mathcal{K}} \bar{E}_\tau \ge C \implies \sum s_\tau \ge \text{deficit}$, guaranteeing `progress == True` until `deficit == 0`.
2. **Deterministic Uniqueness Proof:**
   The targets $y_\tau \in \mathbb{Q}$ and floor values $\lfloor y_\tau \rfloor$ are uniquely determined by rational arithmetic. The ranking key $(-(y_\tau - \lfloor y_\tau \rfloor), \tau)$ provides a strict total order over all candidate period indices $\tau$ because the second component $\tau \in \{1, \dots, d\}$ is strictly unique. Hence, the redistribution order and the resulting allocation vector $\mathbf{e}$ are mathematically unique.
3. **Fail-Closed Proof:** If $C > \sum_{\tau \in \mathcal{K}} \bar{E}_\tau$, the algorithm raises `ValueError` at Step 2 and terminates. No return value, partial list, or modified state escapes.

### 2.5 Numerical Test Vectors
#### Test Vector 1: Standard Binding Cap Case
- **Inputs:** $C = 100 \text{ CCU}$, $d = 3$, $\mathbf{w} = [5, 3, 2]$, $\bar{\mathbf{E}} = [40, 50, 50]$, $\mathcal{K} = \{1, 2, 3\}$.
- **Targets:** $\mathbf{y} = [50, 30, 20]$.
- **Base Allocation:** $e_1^{(0)} = \min(50, 40) = 40$; $e_2^{(0)} = \min(30, 50) = 30$; $e_3^{(0)} = \min(20, 50) = 20$.
- **Sum of Base:** $40 + 30 + 20 = 90 \implies \text{Deficit} = 10 \text{ CCU}$.
- **Slacks:** $s_1 = 0$ (capped); $s_2 = 20$; $s_3 = 30$.
- **Fractional Remainders:** $r_1 = 0, r_2 = 0, r_3 = 0$.
- **Tie-Breaking:** Candidate indices with $s_\tau > 0$ are $\{2, 3\}$. Both have equal remainder $0$. Tie-breaker is ascending index: Period 2 is prioritized over Period 3.
- **Redistribution:**
  - Round-robin water-filling across indices $[2, 3]$ distributes the 10 units:
  - 5 units to Period 2 $\implies e_2 = 30 + 5 = 35$, slack $s_2 = 15$.
  - 5 units to Period 3 $\implies e_3 = 20 + 5 = 25$, slack $s_3 = 25$.
- **Result:** $\mathbf{e} = [40, 35, 25] \text{ CCU}$.
- **Verification:** $40 + 35 + 25 = 100 \text{ CCU}$. Caps: $40 \le 40, 35 \le 50, 25 \le 50$. All valid.

#### Test Vector 2: Multiple Simultaneous Binding Periods
- **Inputs:** $C = 100 \text{ CCU}$, $d = 3$, $\mathbf{w} = [4, 4, 2]$, $\bar{\mathbf{E}} = [25, 25, 60]$, $\mathcal{K} = \{1, 2, 3\}$.
- **Targets:** $\mathbf{y} = [40, 40, 20]$.
- **Base Allocation:**
  - $e_1^{(0)} = \min(40, 25) = 25$ (slack $s_1 = 0$).
  - $e_2^{(0)} = \min(40, 25) = 25$ (slack $s_2 = 0$).
  - $e_3^{(0)} = \min(20, 60) = 20$ (slack $s_3 = 40$).
- **Sum of Base:** $25 + 25 + 20 = 70 \implies \text{Deficit} = 30 \text{ CCU}$.
- **Candidate Pool:** Only Period 3 has positive slack ($s_3 = 40$).
- **Redistribution:** All 30 CCU are allocated to Period 3 $\implies e_3 = 20 + 30 = 50$.
- **Result:** $\mathbf{e} = [25, 25, 50] \text{ CCU}$.
- **Verification:** Sum = $25 + 25 + 50 = 100 \text{ CCU}$. Caps: $25 \le 25, 25 \le 25, 50 \le 60$. All caps satisfied.

#### Test Vector 3: Sufficient Aggregate Capacity with Ineligible Periods
- **Inputs:** $C = 60 \text{ CCU}$, $d = 4$, $\mathbf{w} = [1, 1, 1, 1]$, $\bar{\mathbf{E}} = [30, 30, 30, 30]$, $\mathcal{K} = \{1, 2\}$ (Periods 3 and 4 ineligible).
- **Total Raw Capacity:** $30 \times 4 = 120 \text{ CCU}$.
- **Total Eligible Capacity:** $\sum_{\tau \in \{1, 2\}} \bar{E}_\tau = 30 + 30 = 60 \text{ CCU} \ge 60 \text{ CCU}$ (Feasible).
- **Effective Caps:** $\bar{\mathbf{E}}_{\text{eff}} = [30, 30, 0, 0]$.
- **Eligible Weight Sum:** $W_{\mathcal{K}} = w_1 + w_2 = 2$.
- **Targets:** $\mathbf{y} = [30, 30, 0, 0]$.
- **Base Allocation:** $e^{(0)} = [30, 30, 0, 0]$. Deficit $= 0$.
- **Result:** $\mathbf{e} = [30, 30, 0, 0] \text{ CCU}$.
- **Verification:** Ineligible periods 3 and 4 receive strictly $0 \text{ CCU}$. Sum = $60 \text{ CCU}$.

#### Test Vector 4: Fail-Closed Infeasibility Execution
- **Inputs:** $C = 100 \text{ CCU}$, $d = 3$, $\bar{\mathbf{E}} = [30, 30, 30]$, $\mathcal{K} = \{1, 2, 3\}$.
- **Eligible Capacity:** $30 + 30 + 30 = 90 \text{ CCU} < 100 \text{ CCU}$.
- **Execution:** Step 2 immediately throws:
  `ValueError: CAP_CAPACITY_EXCEEDED: required 100 CCU exceeds aggregate eligible capacity 90 CCU`.
- **Proof of Zero Partial State Leakage:** Execution halts prior to variable assignment; zero elements are returned.

---

## 3. Issue 2 — Correction of Forced-Overlap Resource Capacity Example

### 3.1 Clarification of Project Duration and Active Periods
In non-preemptive scheduling, a project $j$ with duration $d_j \in \mathbb{Z}^+$ that starts at discrete period $S_j$ occupies **exactly $d_j$ contiguous calendar periods**:
$$\mathcal{T}_j(S_j) = \{S_j, S_j + 1, \dots, S_j + d_j - 1\}$$
The previous draft incorrectly stated that a project with duration $d_j = 3$ occupies only two days. The corrected formulation below establishes exact, mathematically consistent interval definitions.

### 3.2 Corrected Example A: Feasible Sequential Scheduling Despite High Total Demand
- **Planning Horizon:** $T = 6$ discrete calendar periods $\mathcal{T} = \{1, 2, 3, 4, 5, 6\}$.
- **Resource $k=1$ (Heavy Concrete Pump):** Capacity $R_{1, t} = 1$ pump for all $t \in \{1, \dots, 6\}$.
  Total pump-periods available across the horizon = $6 \times 1 = 6$.
- **Project A (Mandatory Culvert Replacement):**
  - Duration $d_A = 3$ periods. Resource demand $r_{A, 1} = 1$ pump/period.
  - Release date $r_A = 1$, deadline $D_A = 6$.
  - Total pump demand = $3 \times 1 = 3$ pump-periods.
- **Project B (Mandatory Retaining Wall Stabilization):**
  - Duration $d_B = 3$ periods. Resource demand $r_{B, 1} = 1$ pump/period.
  - Release date $r_B = 1$, deadline $D_B = 6$.
  - Total pump demand = $3 \times 1 = 3$ pump-periods.
- **Analysis:**
  - Total resource demand across the portfolio = $3 + 3 = 6$ pump-periods, exactly equal to total available capacity ($6$).
  - If both projects were scheduled simultaneously at their earliest release dates ($S_A = 1, S_B = 1$):
    $\mathcal{T}_A(1) = \{1, 2, 3\}$, $\mathcal{T}_B(1) = \{1, 2, 3\}$.
    Demand in periods 1, 2, 3 is $1 + 1 = 2 \text{ pumps} > R_{1, t} = 1$.
  - However, the permitted start domains are:
    $S_A \in [r_A, D_A - d_A + 1] = [1, 6 - 3 + 1] = \{1, 2, 3, 4\}$.
    $S_B \in [r_B, D_B - d_B + 1] = [1, 6 - 3 + 1] = \{1, 2, 3, 4\}$.
  - Choosing $S_A = 1 \implies \mathcal{T}_A(1) = \{1, 2, 3\}$.
  - Choosing $S_B = 4 \implies \mathcal{T}_B(4) = \{4, 5, 6\}$.
  - Intersection: $\mathcal{T}_A(1) \cap \mathcal{T}_B(4) = \emptyset$.
  - In every period $t \in \{1, \dots, 6\}$, demand $\le 1 = R_{1, t}$. Deadlines $C_A^{\text{end}} = 3 \le 6$ and $C_B^{\text{end}} = 6 \le 6$ are met.
- **Diagnostic Classification:** Peak demand under simultaneous start is strictly a **`WARNING`**. Sequential execution is fully feasible.

### 3.3 Corrected Example B: Forced Concurrency Causing Genuinely Infeasible Overlap
- **Planning Horizon:** $T = 5$ calendar periods $\mathcal{T} = \{1, 2, 3, 4, 5\}$.
- **Renewable Resource:** Heavy Crawler Crane ($\text{crane}$).
- **Crane Capacity:** $R_{\text{crane}, t} = 1$ crane for all $t \in \{1, \dots, 5\}$.
- **Project A (Mandatory Hospital Substation Restoration):**
  - Duration: $d_A = 3$ periods.
  - Release date: $\text{rel}_A = 1$.
  - Hard deadline: $D_A = 4$.
  - Crane demand: $u_{A, \text{crane}} = 1$ crane per active execution period.
- **Project B (Mandatory Water Intake Repair):**
  - Duration: $d_B = 3$ periods.
  - Release date: $\text{rel}_B = 2$.
  - Hard deadline: $D_B = 5$.
  - Crane demand: $u_{B, \text{crane}} = 1$ crane per active execution period (identically 1 crane, disambiguated from release date $\text{rel}_B = 2$).

**Derivation of Permitted Start Domains and Mandatory Occupancy Intervals:**
1. **For Project A:**
   - Feasible start constraint: $S_A \ge \text{rel}_A = 1$.
   - Completion constraint: $C_A^{\text{end}} = S_A + d_A - 1 \le D_A \implies S_A + 3 - 1 \le 4 \implies S_A \le 2$.
   - Permitted start domain: $\text{dom}(S_A) = \{1, 2\}$.
   - If $S_A = 1$, occupied periods are $\mathcal{T}_A(1) = \{1, 2, 3\}$.
   - If $S_A = 2$, occupied periods are $\mathcal{T}_A(2) = \{2, 3, 4\}$.
   - **Mandatory Core Occupancy for Project A:**
     $$\mathcal{T}_A^{\text{core}} = \bigcap_{s \in \text{dom}(S_A)} \mathcal{T}_A(s) = \{1, 2, 3\} \cap \{2, 3, 4\} = \{2, 3\}$$
     Project A is mathematically guaranteed to occupy periods 2 and 3 in **every permitted schedule**.
2. **For Project B:**
   - Feasible start constraint: $S_B \ge \text{rel}_B = 2$.
   - Completion constraint: $C_B^{\text{end}} = S_B + d_B - 1 \le D_B \implies S_B + 3 - 1 \le 5 \implies S_B \le 3$.
   - Permitted start domain: $\text{dom}(S_B) = \{2, 3\}$.
   - If $S_B = 2$, occupied periods are $\mathcal{T}_B(2) = \{2, 3, 4\}$.
   - If $S_B = 3$, occupied periods are $\mathcal{T}_B(3) = \{3, 4, 5\}$.
   - **Mandatory Core Occupancy for Project B:**
     $$\mathcal{T}_B^{\text{core}} = \bigcap_{s \in \text{dom}(S_B)} \mathcal{T}_B(s) = \{2, 3, 4\} \cap \{3, 4, 5\} = \{3, 4\}$$
     Project B is mathematically guaranteed to occupy periods 3 and 4 in **every permitted schedule**.

**Proof of Infeasible Overlap:**
Evaluate period $t = 3$:
$$3 \in \mathcal{T}_A^{\text{core}} \quad \text{and} \quad 3 \in \mathcal{T}_B^{\text{core}}$$
Because $t = 3$ is in the intersection $\mathcal{T}_A^{\text{core}} \cap \mathcal{T}_B^{\text{core}}$, **both Project A and Project B must actively execute in period 3 under all permitted start combinations**:
$$\forall S_A \in \{1, 2\}, \; \forall S_B \in \{2, 3\}: \quad 3 \in \mathcal{T}_A(S_A) \cap \mathcal{T}_B(S_B)$$
Total crane demand in period 3:
$$u_{A, \text{crane}} + u_{B, \text{crane}} = 1 + 1 = 2 \text{ cranes}$$
Available capacity in period 3:
$$R_{\text{crane}, 3} = 1 \text{ crane}$$
Since $2 > 1$, every feasible schedule violates the capacity limit.
**Diagnostic Classification:** **`PROVEN_INFEASIBILITY`**.

---

## 4. Issue 3 — Funding-Source Feasibility Model & Project-Owner Decision Record

### 4.1 Comparison of Funding Models
The mathematical audit establishes that Hall's Marriage Condition is valid **only for Divisible Co-Funding** (network flow). It is **not valid for Indivisible Project Assignment** (bin-packing).

#### Model A: Divisible Co-Funding
- **Definition:** A project's capital cost $c_j$ can be split across multiple eligible funds $\mathcal{F}_j \subseteq \mathcal{F}$, such that $c_j = \sum_{f \in \mathcal{F}_j} u_{j, f}$, with $u_{j, f} \ge 0$.
- **Flow Network Formulation:**
  - Source node $S$, Sink node $T$.
  - Project nodes $j \in \mathcal{J}_{\text{mandatory}}$ with directed edges $(S, j)$ having capacity $c_j$.
  - Fund nodes $f \in \mathcal{F}$ with directed edges $(f, T)$ having capacity $F_f^{\max}$.
  - Intermediate edges $(j, f)$ with infinite capacity for all $f \in \mathcal{F}_j$.
- **Feasibility Theorem (Gale's Demand Theorem / Max-Flow Min-Cut):**
  A feasible divisible funding allocation exists if and only if for every subset of projects $\mathcal{S} \subseteq \mathcal{J}_{\text{mandatory}}$:
  $$\sum_{j \in \mathcal{S}} c_j \le \sum_{f \in \bigcup_{j \in \mathcal{S}} \mathcal{F}_j} F_f^{\max}$$
  Under Model A, Hall's condition is both necessary and sufficient.

#### Model B: Indivisible Project Assignment (Current Baseline)
- **Definition:** Each project $j$ must be funded entirely from exactly one funding source:
  $$z_{j, f} \in \{0, 1\} \quad \forall f \in \mathcal{F}_j, \quad \sum_{f \in \mathcal{F}_j} z_{j, f} = w_j$$
  Capacity constraints:
  $$\sum_{j \in \mathcal{J}} c_j \cdot z_{j, f} \le F_f^{\max} \quad \forall f \in \mathcal{F}$$
- **Complexity:** Feasibility is equivalent to the **Multiple Knapsack / Generalized Assignment Problem (GAP)**, which is strongly NP-complete.
- **Hall's Condition Inadequacy:** Hall's condition is a **necessary relaxation**, but is **NOT SUFFICIENT**.

### 4.2 Counterexample: Hall's Condition Holds, but Indivisible Assignment is Infeasible
Consider two funding sources:
- Fund 1: Capacity $F_1^{\max} = 50 \text{ CCU}$.
- Fund 2: Capacity $F_2^{\max} = 50 \text{ CCU}$.
- Total available capacity = $100 \text{ CCU}$.

Consider three mandatory projects:
- Project 1: Cost $c_1 = 40 \text{ CCU}$, eligible for $\{1, 2\}$.
- Project 2: Cost $c_2 = 40 \text{ CCU}$, eligible for $\{1, 2\}$.
- Project 3: Cost $c_3 = 20 \text{ CCU}$, eligible for $\{1, 2\}$.
- Total mandatory demand = $40 + 40 + 20 = 100 \text{ CCU}$.

**1. Verification of Hall's Marriage Condition:**
- Any single project $\mathcal{S} = \{j\}$: cost $\le 40 \le 50 = F_1^{\max}$ or $F_2^{\max}$. (Satisfied).
- Any pair of projects $|\mathcal{S}| = 2$: cost $\le 80 \le 100 = F_1^{\max} + F_2^{\max}$. (Satisfied).
- All three projects $\mathcal{S} = \{1, 2, 3\}$: cost $100 \le 100 = F_1^{\max} + F_2^{\max}$. (Satisfied).
Hall's condition is **100% satisfied** across all subsets $\mathcal{S} \subseteq \{1, 2, 3\}$.

**2. Indivisible Assignment Analysis:**
- Project 1 ($40$) must be assigned to Fund 1 or Fund 2. Without loss of generality, assign Project 1 to Fund 1.
  Remaining slack in Fund 1: $50 - 40 = 10 \text{ CCU}$.
- Project 2 ($40$) cannot fit in Fund 1 ($40 > 10$). Therefore, Project 2 MUST be assigned to Fund 2.
  Remaining slack in Fund 2: $50 - 40 = 10 \text{ CCU}$.
- Now consider Project 3 ($20 \text{ CCU}$):
  - Cannot be assigned to Fund 1 (requires $20 \text{ CCU}$, available $10 \text{ CCU}$).
  - Cannot be assigned to Fund 2 (requires $20 \text{ CCU}$, available $10 \text{ CCU}$).
- **Conclusion:** Indivisible assignment is **STRICTLY INFEASIBLE**, proving that Hall's condition cannot be used as a sufficient feasibility test for Model B.

### 4.3 Formal Project-Owner Decision Record (RSK-M2-06)
- **Status:** APPROVED & RATIFIED BY PROJECT OWNER (Model B — Indivisible Project Funding).
- **Mandate:** The project owner has explicitly approved Model B: Every recovery project must be assigned wholly to exactly one eligible funding source. Splitting one project's cost across multiple funding sources is strictly prohibited.
- **Decision Authority:** Grounded in explicit project-owner approval, not merely inferred from the single `VARCHAR(100)` database column.
- **Mathematical Specification for Milestone 2B:**
  - Binary assignment variables $z_{j, f} \in \{0, 1\}$ for each project $j$ and fund $f \in \text{EligibleFunds}[j]$.
  - Exact single-fund selection: $\sum_{f \in \text{EligibleFunds}[j]} z_{j, f} = w_j$.
  - Capacity enforcement: $\sum_j c_j \cdot z_{j, f} \le F_f^{\max}$.
  - Pre-solve uses Hall's Marriage Condition strictly as a **`NECESSARY_CONDITION_VIOLATION`** screening test. Complete feasibility is determined via integer binary assignment constraints in the CP-SAT engine.

---

## 5. Issue 4 — Mathematical Proof of the Periodic Solvency Lower Bound

### 5.1 System Model
Let:
- $\mathcal{J}_{\text{mandatory}}$: Set of mandatory recovery projects.
- For each $j \in \mathcal{J}_{\text{mandatory}}$:
  - Duration $d_j \in \mathbb{Z}^+$.
  - Exact CPM earliest start $E_j \in \mathbb{Z}^+$ (computed from topological release dates $r_j$).
  - Exact CPM latest start $L_j \in \mathbb{Z}^+$ (computed via backward pass from hard deadlines $D_j$ and horizon $T$):
    $$L_j = \min\left(D_j - d_j + 1, \; \min_{(j, k) \in \mathcal{E}} (L_k - d_j - \text{lag}_{jk})\right)$$
  - Non-preemptive execution: once started at $S_j \in [E_j, L_j]$, project $j$ incurs discrete expenditure profile $\mathbf{e}_j = [e_{j, 1}, \dots, e_{j, d_j}]$ with $e_{j, \tau} \ge 0$ and $\sum_{\tau=1}^{d_j} e_{j, \tau} = c_j$.
- Expenditure of project $j$ in calendar period $s \in \{1, \dots, T\}$ given start $S_j$:
  $$E_{j, s}(S_j) = \begin{cases} e_{j, (s - S_j + 1)} & \text{if } S_j \le s \le S_j + d_j - 1 \\ 0 & \text{otherwise} \end{cases}$$
- Cumulative expenditure of project $j$ up to calendar period $t$:
  $$K_j(t, S_j) = \sum_{s=1}^t E_{j, s}(S_j)$$
- Cumulative portfolio revenue up to calendar period $t$: $F_{\text{cum}}(t) = \Phi_0 + \sum_{s=1}^t B_s$ (with initial liquid cash $\Phi_0 \ge 0$, retention $\eta = 1.0$).

### 5.2 Monotonicity Lemma
**Lemma 1 (Monotonicity of Cumulative Spend):**
For any project $j$ with non-negative profile $e_{j, \tau} \ge 0$ and for any fixed calendar period $t \in \{1, \dots, T\}$, the cumulative expenditure $K_j(t, S_j)$ is a monotonically non-increasing function of the start period $S_j$:
$$\text{If } S_j^{(1)} \le S_j^{(2)}, \quad \text{then } K_j(t, S_j^{(1)}) \ge K_j(t, S_j^{(2)})$$

*Proof:*
Let $\delta = S_j^{(2)} - S_j^{(1)} \ge 0$.
- If $t < S_j^{(1)} \le S_j^{(2)}$: $K_j(t, S_j^{(1)}) = 0 = K_j(t, S_j^{(2)})$.
- If $S_j^{(1)} \le t < S_j^{(2)}$:
  $K_j(t, S_j^{(1)}) = \sum_{\tau=1}^{t - S_j^{(1)} + 1} e_{j, \tau} \ge 0$, while $K_j(t, S_j^{(2)}) = 0$.
  Thus $K_j(t, S_j^{(1)}) \ge K_j(t, S_j^{(2)})$.
- If $S_j^{(2)} \le t < S_j^{(1)} + d_j - 1$:
  $t - S_j^{(1)} + 1 \ge t - S_j^{(2)} + 1$. Because each $e_{j, \tau} \ge 0$:
  $$K_j(t, S_j^{(1)}) = \sum_{\tau=1}^{t - S_j^{(1)} + 1} e_{j, \tau} = \sum_{\tau=1}^{t - S_j^{(2)} + 1} e_{j, \tau} + \sum_{\tau=t - S_j^{(2)} + 2}^{t - S_j^{(1)} + 1} e_{j, \tau} \ge K_j(t, S_j^{(2)})$$
- If $t \ge S_j^{(2)} + d_j - 1$: Both projects have completed.
  $K_j(t, S_j^{(1)}) = c_j$ and $K_j(t, S_j^{(2)}) = c_j$.
Therefore, $K_j(t, S_j^{(1)}) \ge K_j(t, S_j^{(2)})$ holds for all $t$. $\blacksquare$

### 5.3 Lower Bound Theorem
**Theorem 2 (Valid Relaxation-Based Lower Bound):**
Let $\mathcal{S}_{\text{feasible}}$ be the set of all jointly feasible schedule vectors $\mathbf{S} = (S_1, \dots, S_N)$ satisfying DAG precedence, deadlines, and resource constraints.
For every feasible schedule $\mathbf{S} \in \mathcal{S}_{\text{feasible}}$, the start date of each mandatory project satisfies $S_j \le L_j$.
Therefore, for every calendar period $t \in \{1, \dots, T\}$:
$$K_{\text{portfolio}}(t, \mathbf{S}) \equiv \sum_{j \in \mathcal{J}_{\text{mandatory}}} K_j(t, S_j) \ge \sum_{j \in \mathcal{J}_{\text{mandatory}}} K_j(t, L_j) \equiv K_{\text{late}}(t)$$
Furthermore, if $\exists t \in \{1, \dots, T\}$ such that:
$$F_{\text{cum}}(t) < K_{\text{late}}(t)$$
then NO feasible schedule exists. The condition is a rigorous proof of **`NECESSARY_CONDITION_VIOLATION`** (and **`PROVEN_INFEASIBILITY`** under hard deadlines).

*Proof:*
By definition of deadline $D_j$, any feasible schedule completes project $j$ by period $D_j$, requiring $S_j \le D_j - d_j + 1$. By backward CPM propagation, $S_j \le L_j$.
Applying Lemma 1 project by project:
$$K_j(t, S_j) \ge K_j(t, L_j) \quad \forall j \in \mathcal{J}_{\text{mandatory}}$$
Summing across all mandatory projects establishes that $K_{\text{late}}(t)$ is a valid lower bound.
If $F_{\text{cum}}(t) < K_{\text{late}}(t)$, then for any feasible schedule $\mathbf{S}$:
$$F_{\text{cum}}(t) < K_{\text{late}}(t) \le K_{\text{portfolio}}(t, \mathbf{S})$$
which violates non-negative cash solvency $\Phi_t \ge 0$. Hence no feasible schedule can exist. $\blacksquare$

### 5.4 Four Illustrative Numerical Scenarios

#### Scenario 1: Earliest-Start Deficit is Merely a Warning
- Planning Horizon $T = 4$.
- Project A: $d_A = 2$, cost $c_A = 100 \text{ CCU}$ ($e_A = [50, 50]$). $r_A = 1, D_A = 4 \implies E_A = 1, L_A = 3$.
- Revenue tranches: $B = [40, 20, 50, 0] \implies F_{\text{cum}} = [40, 60, 110, 110]$.
- **Earliest Start Schedule ($S_A = 1$):**
  Spend by period: $E_1 = 50, E_2 = 50 \implies K_{\text{early}} = [50, 100, 100, 100]$.
  At $t = 1$: $F_{\text{cum}}(1) = 40 < K_{\text{early}}(1) = 50$ (Deficit of 10 CCU).
- **Latest Start Schedule ($S_A = 3$):**
  Spend by period: $E_3 = 50, E_4 = 50 \implies K_{\text{late}} = [0, 0, 50, 100]$.
  Comparison with revenue:
  - $t = 1$: $F_{\text{cum}} = 40 \ge K_{\text{late}} = 0$.
  - $t = 2$: $F_{\text{cum}} = 60 \ge K_{\text{late}} = 0$.
  - $t = 3$: $F_{\text{cum}} = 110 \ge K_{\text{late}} = 50$.
  - $t = 4$: $F_{\text{cum}} = 110 \ge K_{\text{late}} = 100$.
- **Result:** $K_{\text{late}}(t) \le F_{\text{cum}}(t)$ everywhere. Project A scheduled at $S_A = 3$ is completely solvent.
- **Diagnostic:** Earliest-start deficit was strictly a **`WARNING`**.

#### Scenario 2: Lower-Bound Test Proves Infeasibility
- Planning Horizon $T = 4$.
- Project A: $d_A = 2$, cost $c_A = 100 \text{ CCU}$ ($e_A = [50, 50]$). Hard deadline $D_A = 2 \implies L_A = 1$.
- Revenue tranches: $B = [40, 70, 0, 0] \implies F_{\text{cum}} = [40, 110, 110, 110]$.
- **Latest Start Evaluation:**
  Since $L_A = 1$, Project A must start at period 1.
  $K_{\text{late}}(1) = 50 \text{ CCU}$.
  Available revenue: $F_{\text{cum}}(1) = 40 \text{ CCU}$.
- **Result:** $F_{\text{cum}}(1) = 40 < K_{\text{late}}(1) = 50$.
- **Diagnostic:** **`PROVEN_INFEASIBILITY`** (even latest possible execution creates an unavoidable 10 CCU deficit in period 1).

#### Scenario 3: Independent Latest Starts Are Not Jointly Feasible But Remain a Valid Lower Bound
- Planning Horizon $T = 4$. Single crane capacity $R_{1, t} = 1$.
- Project A: $d_A = 2$, cost $50 \text{ CCU}$ ($e_A = [25, 25]$). Deadline $D_A = 4 \implies L_A = 3$. Requires 1 crane.
- Project B: $d_B = 2$, cost $50 \text{ CCU}$ ($e_B = [25, 25]$). Deadline $D_B = 4 \implies L_B = 3$. Requires 1 crane.
- **Joint Feasibility of $\mathbf{L} = (3, 3)$:**
  Both projects cannot start at period 3 simultaneously due to crane capacity ($1 + 1 = 2 > 1$).
  Thus $\mathbf{L} = (3, 3)$ is **NOT a feasible schedule**.
- **Lower Bound Validity:**
  $K_{\text{late}}(t) = K_A(t, 3) + K_B(t, 3)$:
  $t = 1, 2 \implies K_{\text{late}} = 0$.
  $t = 3 \implies K_{\text{late}} = 25 + 25 = 50$.
  $t = 4 \implies K_{\text{late}} = 50 + 50 = 100$.
  In any feasible schedule respecting crane capacity, one project must run at $S \le 2$, shifting spend earlier.
  For instance, schedule $\mathbf{S} = (1, 3)$ yields cumulative spend:
  $K_{\text{actual}}(1) = 25 \ge K_{\text{late}}(1) = 0$.
  $K_{\text{actual}}(2) = 50 \ge K_{\text{late}}(2) = 0$.
  $K_{\text{actual}}(3) = 75 \ge K_{\text{late}}(3) = 50$.
  $K_{\text{actual}}(4) = 100 \ge K_{\text{late}}(4) = 100$.
- **Conclusion:** $K_{\text{actual}}(t) \ge K_{\text{late}}(t)$ holds for all $t$. Even though $\mathbf{L}$ is not jointly feasible, $K_{\text{late}}(t)$ is a mathematically valid relaxation lower bound.

#### Scenario 4: Risk of False Infeasibility from Invalid Latest-Start Assumptions
- Suppose Project A precedes Project B ($(A, B) \in \mathcal{E}$, duration $d_A = 2$, duration $d_B = 2$, horizon $T = 4$).
- Deadline for B is $D_B = 4 \implies L_B = 3$.
- Correct CPM backward pass: $L_A = L_B - d_A = 3 - 2 = 1$.
- **What If An Algorithm Naively Assumes B Must Start Earlier (e.g. $S_B = 1$)?**
  If an invalid algorithm arbitrarily placed Project B at period 1 instead of its true latest start 3, it would compute an inflated expenditure $K(1) = 50 + 50 = 100$.
  If revenue at period 1 was $60 \text{ CCU}$, the algorithm would falsely claim $60 < 100 \implies \text{INFEASIBLE}$.
  In reality, Project B can wait until period 3, requiring zero cash at period 1.
- **Rule:** $L_j$ must strictly represent the **maximal feasible latest start** via backward-pass CPM.

---

## 6. Issue 5 — Diagnostic Label Governance & Standardized Taxonomy

### 6.1 Diagnostic Evidence Standards
To prevent false claims of infeasibility and improper root-cause attribution, every finding produced by the optimization engine must adhere to the following evidence matrix:

$$\begin{array}{|l|l|l|}
\hline
\textbf{Diagnostic Classification} & \textbf{Mandatory Mathematical Evidence Required} & \textbf{Permitted Action} \\
\hline
\textbf{PROVEN\_INFEASIBILITY} & \begin{array}{l} \text{Mathematically closed proof that no schedule exists:} \\ \bullet \sum_{\mathcal{J}_{\text{mandatory}}} c_j > \sum_{t=1}^T B_t \\ \bullet \text{DAG Precedence Cycle (Kahn's algorithm)} \\ \bullet \text{Forced core overlap } \mathcal{T}_A^{\text{core}} \cap \mathcal{T}_B^{\text{core}} \ne \emptyset \text{ with demand } > R_{k, t} \\ \bullet E_j + d_j - 1 > T \text{ for mandatory project } j \\ \bullet \text{Dedicated fund oversubscription } \sum_{\mathcal{E}_j=\{f\}} c_j > F_f^{\max} \end{array} & \begin{array}{l} \text{Return status INFEASIBLE;} \\ \text{highlight proven cause directly.} \end{array} \\
\hline
\textbf{NECESSARY\_CONDITION\_VIOLATION} & \begin{array}{l} \text{Rigorous relaxation lower-bound violation:} \\ \bullet K_{\text{late}}(t) > F_{\text{cum}}(t) \text{ via CPM backward pass} \\ \bullet \text{Total resource demand } \sum_j \sum_\tau r_{j, k, \tau} > \sum_t R_{k, t} \\ \bullet \text{Violation of Hall's condition for divisible funds} \end{array} & \begin{array}{l} \text{Return status INFEASIBLE;} \\ \text{document necessary violation.} \end{array} \\
\hline
\textbf{WARNING} & \begin{array}{l} \text{Bottleneck under a heuristic or specific schedule:} \\ \bullet \text{Earliest-start cash-flow deficit } (K_{\text{early}}(t) > F_{\text{cum}}(t)) \\ \bullet \text{Uncoordinated peak resource concurrency (with slack)} \\ \bullet \text{Single-fund shortfall when alternate funds are eligible} \end{array} & \begin{array}{l} \text{Log warning in diagnostics;} \\ \text{proceed to CP-SAT solver search.} \end{array} \\
\hline
\textbf{SOLVER\_ASSISTED\_HYPOTHESIS} & \begin{array}{l} \text{Extracted from CP-SAT } \\ \text{SufficientAssumptionsForInfeasibility():} \\ \bullet \text{A subset of assumptions that cannot be satisfied.} \\ \bullet \textbf{NOT guaranteed minimal; NOT guaranteed unique.} \end{array} & \begin{array}{l} \text{Report assumption core as} \\ \text{diagnostic hypothesis only.} \end{array} \\
\hline
\end{array}$$

### 6.2 Multi-Cause Reporting Policy
When multiple interacting constraints cause infeasibility:
1. The engine **MUST NOT collapse the diagnosis into a single arbitrary root cause**.
2. Pre-solve deterministic checks (`PROVEN_INFEASIBILITY` and `NECESSARY_CONDITION_VIOLATION`) are reported first.
3. If solver search was invoked and returned `INFEASIBLE`, solver-assisted hypotheses and warnings are reported concurrently in structured diagnostic blocks.

---

## 7. Status of the Four Mathematical Issues

| Issue Area | Mathematical Resolution | Status |
| :--- | :--- | :---: |
| **Issue 1: Capped Integer Apportionment** | Fully formalized deterministic algorithm with rational targets, secondary period tie-breaking, termination proof, fail-closed mechanics, and Theorem 1 feasibility proof. Verified across 4 test vectors. | **PASS** |
| **Issue 2: Forced-Overlap Resource Concurrency** | Corrected duration-to-period occupancy mapping. Formulated Example A (feasible sequential schedule) and Example B (proven forced-overlap infeasibility via core interval intersection $\mathcal{T}_A^{\text{core}} \cap \mathcal{T}_B^{\text{core}}$). | **PASS** |
| **Issue 3: Funding-Source Feasibility Model** | Formally distinguished Divisible Co-Funding (Model A, Hall's condition holds) from Indivisible Assignment (Model B, GAP/bin-packing). Proved Hall's condition is not sufficient for Model B with a 3-project counterexample. Recorded RSK-M2-06. | **PASS** |
| **Issue 4: Periodic Solvency Lower Bound Proof** | Proved Lemma 1 (monotonicity) and Theorem 2 (valid relaxation lower bound). Illustrated through 4 exact numerical scenarios (warning vs proven deficit vs non-jointly-feasible relaxation vs false assumption risks). | **PASS** |

---

## 8. Governance Notice & Final Halt

**Milestone 2A is NOT declared approved.**  
All algorithmic specifications, mathematical proofs, and diagnostic classification taxonomies in [`docs/PHASE6D_B_MILESTONE_2A_FINAL_MATHEMATICAL_CORRECTION_2_REPORT.md`](file:///C:/Users/shubh/Downloads/DIRS/docs/PHASE6D_B_MILESTONE_2A_FINAL_MATHEMATICAL_CORRECTION_2_REPORT.md) are submitted for project-owner review.

Execution remains strictly halted at the **Milestone 2A Design Acceptance Gate**, awaiting your formal review and explicit authorization before any Milestone 2B implementation begins.
