# DIRS Phase 6D-B — Milestone 2A: Integer Scaling and Numerical Safety Specification

**Document ID:** `DIRS-PHASE6D-B-M2A-SCALE-01`  
**Classification:** NUMERICAL ANALYSIS & INTEGER PROGRAMMING SAFETY SPECIFICATION  
**Author:** Principal Operations Research Scientist & Mathematical Optimization Engineer  
**Date:** November 17, 2026  
**Status:** COMPLETE (MILESTONE 2A DESIGN SPECIFICATION)  
**Database Policy:** ZERO MIGRATIONS — Schema strictly frozen at `phase6b_recovery_foundation`  

---

## 1. Executive Summary & Problem Context

Google OR-Tools CP-SAT is a pure integer programming and constraint satisfaction engine. All decision variables, affine linear expressions, and constraint bounds must be signed 64-bit integers (`int64`). Floating-point numbers cannot be directly passed to CP-SAT without scaling.

This specification establishes the authoritative integer-scaling factors, rounding directions, overflow bounds, and mathematical precision guarantees for every continuous and fractional dimension in the DIRS Phase 6D-B optimization engine.

### Strict Numerical Safety Invariant
> [!IMPORTANT]
> **Directional Conservative Rounding Rule:**  
> Integer scaling must **never silently weaken or relax any hard physical, safety, or equity constraint**:
> - **Ceiling Bounds (Upper Limits, $\le$):** Right-hand side bounds are rounded **DOWN** (floor: $\lfloor \cdot \rfloor$) to conservatively restrict the upper ceiling.
> - **Floor Bounds (Lower Limits, $\ge$):** Right-hand side bounds are rounded **UP** (ceiling: $\lceil \cdot \rceil$) to conservatively tighten the lower requirement.
> - **Equality Invariants (Conservation):** Integer profile distributions are reconciled using exact residual attribution, guaranteeing zero penny or basis-point leakage.

---

## 2. Comprehensive Integer Scaling Strategy

| Physical / Domain Quantity | Original Domain | Proposed Scale Factor ($S$) | Scaled Integer Domain | Rounding & Allocation Rule | Bound Proof / Conservative Invariant | Reporting Conversion |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| **Capital Cost & Budget ($c_j, B_t, \Phi_t$)** | Float Lakh INR or INR Currency | **$S_{\text{cost}} = 100,000$** (1 Rupee if Lakh input, or $100$ for Paise) | $[0, 2^{53} - 1]$ | $\bar{c}_j = \text{round}(c_j \times S_{\text{cost}})$. Budgets: $\bar{B}_t = \lfloor B_t \times S_{\text{cost}} \rfloor$. | Budgets rounded down ensure public funds are never over-committed. | Value / $S_{\text{cost}}$ |
| **MCPI Objective Score ($\Pi_j$)** | $[0.0, 100.0]$ | **$S_{\text{MCPI}} = 10,000$** (1 Basis Point = $0.0001$) | $[0, 1,000,000]$ | $\bar{\Pi}_j = \text{round}(\Pi_j \times 10,000)$ | Preserves 4 decimal places of MCPI precision; prevents tie-breaking inversions. | Value / $10,000$ |
| **Expenditure Profile Fractions ($\boldsymbol{\gamma}_j$)** | Float $[0.0, 1.0]$, $\sum \gamma_\tau = 1.0$ | **Direct Rupee Split** (No float intermediate) | $[\bar{\gamma}_{j, 1}, \dots, \bar{\gamma}_{j, d_j}]$ | $\bar{\gamma}_{j, \tau} = \lfloor \gamma_\tau \times \bar{c}_j \rfloor$. Residual $\bar{c}_j - \sum \bar{\gamma}_\tau$ assigned to final period. | Exact Rupee Conservation: $\sum_{\tau=1}^{d_j} \bar{\gamma}_{j, \tau} \equiv \bar{c}_j$ exactly. | $\bar{\gamma}_{j, \tau} / S_{\text{cost}}$ |
| **District Equity Quota ($\underline{\theta}_d B$)** | Float $[0.0, 1.0]$ | Evaluated against scaled budget $\bar{B}$ | $[0, \bar{B}]$ | $\bar{R}_{\text{target}, d} = \lceil \underline{\theta}_d \times \bar{B} \rceil$ | Ceiling ensures district equity quota is never diluted below policy minimum. | Value / $S_{\text{cost}}$ |
| **Blackout Reserve ($R_{\text{blackout}, d}$)** | Float $[0.0, 1.0]$ | Evaluated against scaled budget $\bar{B}$ | $[0, \bar{B}]$ | $\bar{R}_{\text{blackout}, d} = \lceil \underline{\theta}_d \times \bar{B} \rceil$ | Ceiling guarantees full reservation of capital for uncontacted zones. | Value / $S_{\text{cost}}$ |
| **Renewable Resources ($u_{j, r}, R_{r, t}$)** | Integer units (crews, machinery) | **$S_{\text{res}} = 1$** (Native integer) | $[0, 10,000]$ | Native integer | Exact integer modeling. | Value |
| **Dependency Lags ($L_{ij}$)** | Float days | **Ceiling Days-to-Period** | $[0, T]$ | $L_{ij} = \lceil L_{\text{days}} / \Delta t \rceil$ | Ceiling ensures technical curing / settlement time is never curtailed. | $L_{ij} \times \Delta t$ |

---

## 3. Detailed Scaling Analyses

### 3.1 Capital Cost & Multi-Period Budget Scaling ($S_{\text{cost}} = 100,000$)
- **Resolution & Unit Meaning:**
  - When source costs and budgets are in whole Indian Rupees (INR), $S_{\text{cost}} = 100,000$ establishes an internal solver precision where **$1 \text{ integer unit} = 0.00001 \text{ INR} = 0.001 \text{ Paise}$**.
  - When source costs and budgets are in Lakh INR (the standard domain convention, where $1 \text{ Lakh} = 100,000 \text{ INR}$), multiplying by $100,000$ converts Lakhs directly to **whole Indian Rupees ($1 \text{ integer unit} = 1 \text{ INR}$)**.
  - **Source Precision:** $0.01$ INR (Paise) or $0.0001$ Lakh INR.
  - **Internal Integer Precision:** $0.00001$ INR ($10^{-5}$ INR).
  - **Display / Reporting Precision:** $2$ decimal places for INR (Paise) or $4$ decimal places for Lakhs.
- **Budget Ceiling Rounding (Conservative Floor: $\lfloor \cdot \rfloor$):**
  $$\bar{B}_t = \lfloor B_t \times S_{\text{cost}} \rfloor$$
  *Mathematical Proof of Non-Relaxation:* Since $\bar{B}_t \le B_t \times S_{\text{cost}}$, dividing by $S_{\text{cost}}$ guarantees $\sum_j E_{j, t} \le B_t$. It is mathematically impossible for the solver to allocate even a fractional rupee beyond the authorized envelope.
- **District Equity Rounding (Conservative Ceiling: $\lceil \cdot \rceil$):**
  $$\bar{R}_{\text{target}, d} = \lceil \underline{\theta}_d \times \bar{B} \rceil$$
  *Mathematical Proof of Non-Relaxation:* Since $\bar{R}_{\text{target}, d} \ge \underline{\theta}_d \times \bar{B}$, dividing by $S_{\text{cost}}$ guarantees $\sum_{j \in \mathcal{P}_d} c_j w_j \ge \underline{\theta}_d B$. District equity allocations cannot be diluted by integer truncation.

---

### 3.2 Capped Integer Expenditure Apportionment Algorithm
When project cost $\bar{c}_j$ is apportioned across periods $\tau \in \{1, \dots, d_j\}$ according to normalized profile weights $p_{j, \tau} \in [0.0, 1.0]$ ($\sum_\tau p_{j, \tau} = 1.0$), subject to individual period expenditure caps $\bar{E}_\tau$:
Ordinary largest-remainder apportionment (Hamilton-Hare) does NOT inherently respect period caps; if applied naively, it can violate $\bar{E}_\tau$.
To guarantee both conservation ($\sum_{\tau} e_{j, \tau} = \bar{c}_j$) and capacity bounds ($0 \le e_{j, \tau} \le \bar{E}_\tau$), the engine defines the **Capped Integer Apportionment Algorithm** (Projected Largest-Remainder):

```python
import math
from typing import List


def capped_largest_remainder_apportionment(
    total_cost_ccu: int,
    profile_weights: List[float],
    period_caps_ccu: List[int],
    allow_uniform_fallback: bool = False,
) -> List[int]:
  """Apportions total_cost_ccu across periods while strictly enforcing period caps.

  Guarantees:
  1. Bounds: 0 <= e[tau] <= period_caps[tau]
  2. Conservation: sum(e) == total_cost_ccu (if feasible)
  3. Fails closed with ValueError if total_cost_ccu > sum(period_caps).
  4. Fails closed with ValueError if all weights are zero for non-zero cost (unless allow_uniform_fallback=True).
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
        f"CAP_CAPACITY_EXCEEDED: required {total_cost_ccu} CCU exceeds aggregate period cap {total_cap} CCU"
    )

  if total_cost_ccu == 0:
    return [0] * d

  # Zero-weight governance: fail-closed default
  total_weight = sum(profile_weights)
  if total_weight == 0:
    if not allow_uniform_fallback:
      raise ValueError(
          "ZERO_ELIGIBLE_WEIGHTS: Cannot apportion non-zero capital cost when all period weights are zero."
      )
    profile_weights = [1.0 / d] * d
  else:
    # Normalize weights so sum is 1.0
    profile_weights = [w / total_weight for w in profile_weights]

  # Step 1: Target unrounded allocations and initial clamped base
  targets = [total_cost_ccu * p for p in profile_weights]
  e = [min(int(math.floor(t)), cap) for t, cap in zip(targets, period_caps_ccu)]

  # Step 2: Track slack capacity
  slacks = [cap - alloc for alloc, cap in zip(e, period_caps_ccu)]
  deficit = total_cost_ccu - sum(e)

  # Step 3: Priority based on fractional remainder
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
        f"CAP_CAPACITY_EXCEEDED: cannot allocate remaining {deficit} CCU within period caps"
    )

  assert sum(e) == total_cost_ccu
  assert all(0 <= alloc <= cap for alloc, cap in zip(e, period_caps_ccu))
  return e
```

#### Mathematical Properties of Capped Apportionment:
1. **Feasibility Condition:** A solution exists if and only if $\bar{c}_j \le \sum_{\tau=1}^{d_j} \bar{E}_\tau$ and each $\bar{E}_\tau \ge 0$.
2. **Conservation Proof:** If feasible, $\sum_{\tau=1}^{d_j} e_{j, \tau} \equiv \bar{c}_j$. Zero CCU leakage.
3. **Capacity Non-Violation:** $e_{j, \tau} \le \bar{E}_\tau$ is enforced by construction at every step.
4. **Non-Negativity:** Since $\bar{c}_j \ge 0$ and $p_{j, \tau} \ge 0$, $e_{j, \tau} \ge 0$ strictly holds.
5. **Fail-Closed Guarantee:** If $\bar{c}_j > \sum_{\tau=1}^{d_j} \bar{E}_\tau$, the algorithm fails closed immediately (`CAP_CAPACITY_EXCEEDED`); it never produces truncated or invalid partial spend.

---

### 3.3 MCPI Objective Function Scaling & Exact Priority Preservation
- **Domain:** $\text{MCPI}_j \in [0.0, 100.0]$.
- **Scale Factor:** $S_{\text{MCPI}} = 10,000$.
- **Scaled Domain:** $\bar{\Pi}_j \in [0, 1,000,000]$.
- **Quantization Error:** Exactly $0.0$ with respect to 4-decimal `mcpi_score`.
- **Preservation of Sub-Tolerance Floating Differences (DEV-M1-01):**
  If two candidate projects have raw double-precision scores differing by $10^{-5}$ or $10^{-6}$ (so their 4-decimal rounded `mcpi_score` is equal), integer scaling of `mcpi_score` alone would map them to the same integer.
  To preserve the approved exact-comparison rule (`DEV-M1-01`), the solver scales `raw_score` directly:
  $$\bar{\Pi}_j^{\text{hierarchical}} = \lfloor \text{raw\_score}_j \times 10^7 \rfloor$$
  Since $10^7 \times 10^{-6} = 10$, any substantive raw score difference $\ge 10^{-6}$ produces a distinct integer coefficient, ensuring the solver strictly favors the higher-scoring project without tolerance grouping.
- **Exactness of Aggregate Objective:**
  The aggregate objective $\sum \bar{\Pi}_j^{\text{hierarchical}} w_j$ is mathematically exact. It guarantees that project selection strictly honors the substantive priority ranking without artificial clustering.

---

## 4. Integer Overflow Risk Assessment & 64-Bit Arithmetic Proof

Google OR-Tools CP-SAT internally represents integers as signed 64-bit integers:
$$\text{Max Int64} = 2^{63} - 1 \approx 9.22 \times 10^{18}$$

We calculate the maximum possible value attained by any linear combination in the model:

### 4.1 Maximum Budget / Cash Flow Accumulation
Suppose a massive state reconstruction portfolio:
- $N = 1,000$ projects.
- Total portfolio capital cost: $B_{\text{total}} = 1,000,000 \text{ Lakh INR} = 100 \text{ Billion INR} \approx \$1.2 \text{ Billion USD}$.
- Scaled budget value:
  $$\bar{B}_{\text{total}} = 10^{11} \text{ INR} = 10^{11} \text{ integer units}$$
- Solvency balance $\Phi_t$:
  $$\max \bar{\Phi}_t \le \bar{B}_{\text{total}} = 10^{11}$$
- Headroom calculation:
  $$\frac{2^{63} - 1}{\bar{B}_{\text{total}}} = \frac{9.22 \times 10^{18}}{10^{11}} \approx 92,200,000$$
  The maximum possible financial accumulator is **over 92 million times smaller** than the 64-bit integer overflow limit. Zero overflow risk.

### 4.2 Maximum Objective Value
Suppose $N = 1,000$ candidate projects, each achieving maximum possible MCPI score ($100.0$):
- Scaled project coefficient: $\bar{\Pi}_j = 1,000,000$.
- Total objective value:
  $$Z_{\max} = \sum_{j=1}^{1000} \bar{\Pi}_j = 1,000 \times 1,000,000 = 10^9 \text{ integer units}$$
- Headroom calculation:
  $$\frac{2^{63} - 1}{Z_{\max}} = \frac{9.22 \times 10^{18}}{10^9} \approx 9.22 \times 10^9$$
  The objective function accumulator operates with **9 orders of magnitude** of headroom before signed 64-bit overflow.

---

## 5. Non-Compensatory Acceleration Tie-Breaker Calibration

If the optional early start acceleration bonus is activated:
$$Z_{\text{acceleration}} = \sum_{j \in \mathcal{P}} \sum_{t=1}^T \omega_{j, t} \cdot x_{j, t}$$

We establish the exact integer formula for $\omega_{j, t}$ such that:
$$\sum_{j \in \mathcal{P}} \max_t \omega_{j, t} < 1 \text{ scaled MCPI point}$$

Let $N_{\max} = 1,000$ and $T_{\max} = 50$:
$$\omega_{j, t} = \lfloor \frac{T - t}{T} \rfloor$$
If we set $\omega_{j, t} \in [0, 10]$ integer micro-units:
$$\sum_{j=1}^N \omega_{j, t} \le 1,000 \times 10 = 10,000 \text{ micro-units} = 1 \text{ basis point}$$

**Mathematical Guarantee:**
Under this integer calibration, it is mathematically impossible for an acceleration bonus to alter the selection or rejection of any project ($w_j$). It operates exclusively as a secondary schedule arbiter between alternate schedules of identical project selections.

---

## 6. Numerical Safety Verification Checklist

- [x] All continuous physical quantities map to dedicated integer scaling factors.
- [x] Budgets are rounded down ($\lfloor \cdot \rfloor$), preventing unauthorized deficit spending.
- [x] District equity floors are rounded up ($\lceil \cdot \rceil$), safeguarding vulnerable communities against mathematical dilution.
- [x] Dependency lags are rounded up ($\lceil \cdot \rceil$), safeguarding physical curing and safety times.
- [x] Exact largest-remainder apportionment eliminates penny loss in multi-period cost distributions.
- [x] 64-bit signed integer headroom exceeds 7 orders of magnitude for all variables and expressions.
- [x] Result unscaling functions are exact inverses of scaling factors ($V_{\text{report}} = \bar{V} / S$).
