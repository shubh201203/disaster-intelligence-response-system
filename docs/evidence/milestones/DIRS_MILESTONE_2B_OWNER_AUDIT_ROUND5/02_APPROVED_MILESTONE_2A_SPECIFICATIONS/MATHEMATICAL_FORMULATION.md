# DIRS Phase 6D-B — Milestone 2A: Optimization Mathematical Formulation

**Document ID:** `DIRS-PHASE6D-B-M2A-MATH-01`  
**Classification:** OPERATIONS RESEARCH & MATHEMATICAL FORMULATION SPECIFICATION  
**Author:** Principal Operations Research Scientist & Mathematical Optimization Engineer  
**Date:** November 17, 2026  
**Status:** COMPLETE (MILESTONE 2A DESIGN SPECIFICATION)  
**Database Policy:** ZERO MIGRATIONS — Schema strictly frozen at `phase6b_recovery_foundation`  

---

## 1. Problem Definition & Scope

The **Multi-Period Recovery Project Selection and Scheduling Problem (MP-RPSP)** optimizes the reconstruction of damaged infrastructure across discrete planning periods $t \in \mathcal{T} = \{1, 2, \dots, T\}$.

Given a portfolio of candidate projects $\mathcal{P} = \{1, \dots, N\}$, directed precedence relationships $\mathcal{E}$, multi-period budget envelopes $B_t$, renewable resource capacities $R_{r, t}$, and district equity policy quotas $\underline{\theta}_d$, the engine simultaneously decides:
1. Which projects to select ($w_j \in \{0, 1\}$).
2. The discrete calendar period $s_j \in \{1, \dots, T - d_j + 1\}$ in which each selected project commences.
3. The multi-period capital disbursement trajectory $E_t$ ensuring complete cash solvency ($\Phi_t \ge 0$).

---

## 2. Complete Inventory of Decision Variables

The formulation defines an exact, minimal set of decision variables in Google OR-Tools CP-SAT.

| Symbol | CP-SAT Representation | Index Dimensions | Mathematical Domain | Physical Units | Formal Meaning | Input Dependencies | Output Interpretation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **$w_j$** | `BoolVar` | $j \in \mathcal{P}$ | $\{0, 1\}$ | Dimensionless indicator | Binary portfolio selection indicator ($1$ if project is selected and completed within horizon $T$; $0$ if rejected/deferred). | Candidate project list | If $1$, project is funded and scheduled; if $0$, project is rejected. |
| **$x_{j, t}$** | `BoolVar` | $j \in \mathcal{P}, \; t \in \mathcal{T}_j^{\text{feas}}$ | $\{0, 1\}$ | Dimensionless indicator | Binary start indicator: $= 1$ if project $j$ commences execution at the beginning of calendar period $t$. Feasible range: $\mathcal{T}_j^{\text{feas}} = [E_j, T - d_j + 1]$. | $E_j, d_j, T$ | Identifies the exact scheduled initiation period ($S_j = t$). |
| **$S_j$** | `IntVar` | $j \in \mathcal{P}$ | $[1, T - d_j + 1]$ | Discrete calendar periods ($1, \dots, T$) | Scheduled start period of project $j$. Enforced via affine equality $S_j = \sum_t t \cdot x_{j, t}$ when $w_j = 1$. | $E_j, d_j, T$ | Calendar period when ground construction breaks. |
| **$C_j^{\text{end}}$** | `IntVar` | $j \in \mathcal{P}$ | $[d_j, T]$ | Discrete calendar periods ($1, \dots, T$) | Scheduled completion period of project $j$: $C_j^{\text{end}} = S_j + d_j - 1$ (when $w_j = 1$). | $S_j, d_j$ | Calendar period when facility is commissioned. |
| **$I_j$** | `OptionalIntervalVar` | $j \in \mathcal{P}$ | $[S_j, S_j + d_j]$ | Periods | Optional execution interval variable spanning $[S_j, S_j + d_j]$, present if and only if $w_j = 1$. | $S_j, d_j, w_j$ | Native CP-SAT interval for cumulative resource constraints. |
| **$y_{j, t}$** | `BoolVar` / Expression | $j \in \mathcal{P}, \; t \in \mathcal{T}$ | $\{0, 1\}$ | Dimensionless indicator | Active execution indicator: $= 1$ if project $j$ is actively in execution during period $t$. Formally: $y_{j, t} = \sum_{\tau = \max(E_j, t - d_j + 1)}^t x_{j, \tau}$. | $x_{j, \tau}, d_j$ | Determines whether project consumes machinery/crews in period $t$. |
| **$E_{j, t}$** | `IntVar` | $j \in \mathcal{P}, \; t \in \mathcal{T}$ | $[0, \bar{c}_j]$ | Integer scaled currency (INR Paise) | Capital expenditure required by project $j$ in calendar period $t$: $E_{j, t} = \sum_s \gamma_{j, t - s + 1} x_{j, s}$. | $\boldsymbol{\gamma}_j, x_{j, s}$ | Periodic billing invoice for project $j$. |
| **$E_t$** | `IntVar` | $t \in \mathcal{T}$ | $[0, \sum_j c_j]$ | Integer scaled currency (INR Paise) | Aggregate capital expenditure across all active projects in period $t$: $E_t = \sum_{j \in \mathcal{P}} E_{j, t}$. | $E_{j, t}$ | Total treasury capital disbursement in period $t$. |
| **$\Phi_t$** | `IntVar` | $t \in \mathcal{T}$ | $[0, \sum_{\tau=1}^t B_\tau]$ | Integer scaled currency (INR Paise) | Liquid cash carry-forward balance held at the end of period $t$: $\Phi_t = \eta \Phi_{t-1} + B_t - E_t \ge 0$. | $\Phi_{t-1}, B_t, E_t, \eta$ | Unspent liquid treasury reserve carrying into period $t+1$. |

---

## 3. Objective Function Formulation

### 3.1 Primary Optimization Objective
The primary recovery optimization objective maximizes the total societal utility of selected recovery projects:

$$\text{Maximize } Z = Z_{\text{utility}} + Z_{\text{acceleration}}$$

Where:
$$Z_{\text{utility}} = \sum_{j \in \mathcal{P}} \Pi_j \cdot w_j$$

And $\Pi_j = \text{MCPI}_j \in [0.0, 100.0]$ is the verified Multi-Criteria Recovery Priority Index computed by `MCPIPrioritizationService`.

---

### 3.2 Non-Compensatory Life-Safety Architecture (RSK-M2-01 Approved Policy)
In disaster recovery, critical life-safety breaches ($S_L \ge 0.85$, designated `TIER_1_MANDATORY`) must **never** be subject to compensatory trade-offs against cost, convenience, or economic return.

Per Project-Owner Decision **RSK-M2-01 (Option A Approved)**, every project formally classified as mandatory life-safety is enforced as an inviolable hard constraint:

$$w_j = 1 \quad \forall j \in \mathcal{J}_{\text{mandatory}}$$
$$S_j \le T_{\text{safety\_max}} \quad \forall j \in \mathcal{J}_{\text{mandatory}}$$

#### Governing Invariant on Infeasibility:
If hard budget limits, periodic cash-flow solvency, resource capacity, technical dependencies, or planning horizon constraints cannot accommodate 100% of the mandatory projects, the solver must return **`INFEASIBLE`** and generate structured root-cause diagnostics. 
- **Zero Silent Relaxation:** The solver and diagnostics are strictly forbidden from softening mandatory life-safety constraints to manufacture a feasible schedule.
- **Sequential Lexicographic Fallback (Optional Future Mode):** If explicitly enabled by ministerial decree, sequential lexicographic optimization (Stage 1: $\max \sum w_j$ for Tier 1; Stage 2: maximize standard MCPI subject to Stage 1 optimum) may be evaluated, but it is not the default operational mode.

> [!CRITICAL]
> **Prohibition of Large "M-Penalty" Approximations:**  
> The system strictly rejects assigning an arbitrary large constant (e.g. $10^6$) to Tier 1 projects in a single additive objective. In integer programming, artificial big-$M$ objective weights distort solver branch-and-bound heuristics, cause severe numerical instability, and fail to guarantee true non-compensatory behavior.

---

### 3.3 Optional Acceleration Preference ($Z_{\text{acceleration}}$)
To encourage earlier reconstruction among projects with identical substantive priority without overturning selection decisions, an optional time-discounted acceleration term may be enabled:

$$Z_{\text{acceleration}} = \sum_{j \in \mathcal{P}} \sum_{t=E_j}^{T - d_j + 1} \omega_{j, t} \cdot x_{j, t}$$

Where:
$$\omega_{j, t} = \left\lfloor \frac{\Pi_j \cdot (T - t)}{K_{\text{discount}}} \right\rfloor$$

#### Non-Compensatory Bounding Condition:
To guarantee that the acceleration bonus can **never** cause a lower-priority project to be selected over a higher-priority project:
$$\sum_{j \in \mathcal{P}} \max_t \omega_{j, t} < \min_{j, k \mid \Pi_j > \Pi_k} (\Pi_j - \Pi_k) \cdot S_{\text{MCPI}}$$

By choosing $K_{\text{discount}} \gg N \cdot T$, the acceleration term operates strictly as an internal schedule tie-breaker (preferring $S_j = 1$ over $S_j = 3$), with mathematical proof of zero influence on portfolio selection $w_j$.

---

## 4. Formal Constraint System

### 4.1 Selection & Execution Atomicity
Each candidate project is executed at most once, and only if selected:
$$\sum_{t=E_j}^{T - d_j + 1} x_{j, t} = w_j \quad \forall j \in \mathcal{P}$$
$$w_j \in \{0, 1\}$$

If $w_j = 0$, then $x_{j, t} = 0 \; \forall t$, guaranteeing zero expenditure and zero resource consumption.

---

### 4.2 Start Period Linkage & Completion Mapping
For all selected projects ($w_j = 1$), the scheduled start period is:
$$S_j = \sum_{t=E_j}^{T - d_j + 1} t \cdot x_{j, t}$$
The completion period is:
$$C_j^{\text{end}} = S_j + d_j - 1$$
Horizon boundary invariant:
$$C_j^{\text{end}} \le T \quad (\text{guaranteed by } t \le T - d_j + 1)$$

---

### 4.3 Technical Dependency Precedence (DEF-6D-04 Remediation)
For every directed dependency edge $(i, j) \in \mathcal{E}$, where $i$ is a prerequisite for $j$:

1. **Selection Co-requisite (Hard Invariant):**
   $$w_j \le w_i \quad \forall (i, j) \in \mathcal{E}$$
   A successor project cannot be selected unless its mandatory prerequisite is also selected.

2. **Timing Precedence with Completion-to-Start Lag ($L_{ij}$):**
   When successor $j$ is selected ($w_j = 1$):
   $$S_j \ge S_i + d_i + L_{ij}$$
   *(Note: Since $w_j = 1 \implies w_i = 1$, both $S_j$ and $S_i$ are well-defined).*

In CP-SAT, this is implemented using native boolean reification:
```python
model.Add(w[j] <= w[i])
model.Add(start_var[j] >= start_var[i] + d[i] + L_ij).OnlyEnforceIf(w[j])
```

---

### 4.4 Calendar Cost Expenditure Convolution & Horizon Boundary Reconciliation
Let $\boldsymbol{\gamma}_j = [\gamma_{j, 1}, \dots, \gamma_{j, d_j}]$ be the discrete execution profile vector generated by `CalendarCostService`, where each $\gamma_{j, \tau} \ge 0$ represents the fraction of capital required at relative execution age $\tau$, and $\sum_{\tau=1}^{d_j} \gamma_{j, \tau} = 1.0$.

#### 1. Discrete Expenditure Convolution:
The capital cash-flow incurred by project $j$ in calendar period $t \in \{1, \dots, T\}$ is:
$$E_{j, t} = \sum_{s = \max(E_j, t - d_j + 1)}^t \gamma_{j, (t - s + 1)} \cdot c_j \cdot x_{j, s}$$

Aggregate period capital demand:
$$E_t = \sum_{j \in \mathcal{P}} E_{j, t} = \sum_{j \in \mathcal{P}} \sum_{s = \max(E_j, t - d_j + 1)}^t \gamma_{j, (t - s + 1)} \cdot c_j \cdot x_{j, s}$$

#### 2. Planning Horizon & Capital Conservation Invariant:
- **Default Policy (Standard Horizon Containment):**
  Every selected project must completely finish on or before period $T$:
  $$S_j + d_j - 1 \le T \iff x_{j, s} = 0 \quad \forall s > T - d_j + 1$$
  Under this policy, **zero expenditure lies beyond horizon $T$**, guaranteeing strict lifetime conservation:
  $$\sum_{t=1}^T E_{j, t} = c_j \cdot w_j \quad \forall j \in \mathcal{P}$$
- **Phased Multi-Year Extension Policy (If Projects Extend Beyond $T$):**
  If an authorized multi-year scenario permits project initiation where $S_j + d_j - 1 > T$, **no expenditure may disappear**:
  $$c_j \cdot w_j = \sum_{t=1}^T E_{j, t} + E_{j, >T}$$
  Where:
  $$E_{j, >T} = \sum_{\tau = T - S_j + 2}^{d_j} \gamma_{j, \tau} \cdot c_j$$
  The tail expenditure $E_{j, >T}$ is formally accounted for as an **Unfunded Future Capital Encumbrance**, carried as an explicit liability against subsequent fiscal envelopes and logged in `PortfolioSolvencyAudit`. Partial final periods occurring at the boundary $T$ are fully accounted for, and `is_fully_reconciled` is flagged accordingly per Milestone 1 conventions.

---

### 4.5 Fiscal Liquidity & Cash-Flow Solvency Recurrence
Reconstruction capital is released in tranches $B_t \ge 0$ with initial liquid cash balance $\Phi_0 \ge 0$. Unspent funds carry forward into subsequent periods with fiscal efficiency factor $\eta \in [0.0, 1.0]$:

$$\Phi_t = \eta \cdot \Phi_{t-1} + B_t - E_t \quad \forall t \in \{1, \dots, T\}$$
$$\Phi_0 \ge 0 \quad (\text{Initial Cash Balance, default } 0)$$
$$\Phi_t \ge 0 \quad \forall t \in \{1, \dots, T\}$$

Under standard full retention ($\eta = 1.0$), cumulative solvency is expressed directly as:
$$\sum_{s=1}^t E_s \le \Phi_0 + \sum_{s=1}^t B_s \equiv F_{\text{cum}}(t) \quad \forall t \in \{1, \dots, T\}$$

**Solvency Invariant:**
Total cumulative expenditure up to period $t$ can never exceed initial cash plus cumulative receipts:
$$\sum_{s=1}^t E_s \le F_{\text{cum}}(t)$$
Zero deficit spending is strictly enforced.

---

### 4.6 Indivisible Project Funding Source Assignment (RSK-M2-06)
In accordance with project-owner decision `RSK-M2-06`, recovery projects must be funded **indivisibly**: each selected project is assigned wholly to exactly one eligible funding source. Cost splitting across multiple funding sources is prohibited.

For every project $j \in \mathcal{P}$ and funding source $f \in \mathcal{F}$:
1. **Binary Assignment Variables:**
   $$z_{j, f} \in \{0, 1\} \quad \forall j \in \mathcal{P}, \; \forall f \in \mathcal{F}$$
2. **Exact Single-Fund Selection:**
   If project $j$ is selected ($w_j = 1$), it must be assigned to exactly one eligible fund; if not selected ($w_j = 0$), all assignment variables are zero:
   $$\sum_{f \in \mathcal{F}_j^{\text{eligible}}} z_{j, f} = w_j \quad \forall j \in \mathcal{P}$$
3. **Ineligible Source Prohibition:**
   $$z_{j, f} = 0 \quad \forall f \notin \mathcal{F}_j^{\text{eligible}}$$
4. **Funding Source Capacity Envelopes:**
   Total capital cost of all projects assigned to fund $f$ cannot exceed its authorized capacity $F_f^{\max}$:
   $$\sum_{j \in \mathcal{P}} c_j \cdot z_{j, f} \le F_f^{\max} \quad \forall f \in \mathcal{F}$$

**Mathematical Complexity & Screening Rule:**
Indivisible project funding constitutes a **Generalized Assignment Problem (GAP) / Multiple Knapsack Problem**, which is NP-complete. Hall's Marriage Condition is applied during pre-solve strictly as a **necessary screening test** (`NECESSARY_CONDITION_VIOLATION`); complete feasibility is decided by the integer CP-SAT solver.

---

### 4.7 District Policy Equity Floors & Dynamic Absorption
To ensure equitable spatial allocation without forcing wasteful capital expenditure:

$$\sum_{j \in \mathcal{P}_d} c_j \cdot w_j \ge \min\left(\underline{\theta}_d \cdot B, \; \sum_{j \in \mathcal{P}_d} c_j\right) \quad \forall d \in \mathcal{D}$$

Where:
- $\underline{\theta}_d \in [0.0, 1.0]$: Administrative policy equity quota for district $d$.
- $B = \sum_{t=1}^T B_t$: Total multi-period capital envelope.
- $\sum_{j \in \mathcal{P}_d} c_j$: Total capital demand submitted by district $d$.

If district $d$ submits less capital demand than its quota ($\sum_{j \in \mathcal{P}_d} c_j < \underline{\theta}_d B$), the dynamic bound clamps to $100\%$ of submitted demand, preventing solver infeasibility while funding all verified projects in that district.

---

### 4.8 Uncontacted Blackout Reserve Protection
For districts under complete communications or transport blackout ($\mathcal{D}_{\text{blackout}}$, where $|J_d| = 0$):

The total allocable capital available across all candidate projects is constrained by:
$$\sum_{j \in \mathcal{P}} c_j \cdot w_j \le B - \sum_{d \in \mathcal{D}_{\text{blackout}}} \underline{\theta}_d \cdot B$$

This mathematically blocks the solver from appropriating uncontacted communities' equity allocations for urban projects.

---

### 4.9 Renewable Resource Capacity Limits
Let $\mathcal{R}$ denote renewable resources (e.g., structural engineering inspectors, hydraulic excavators). Project $j$ requires $u_{j, r}$ units of resource $r$ during each period of its active execution. Total period capacity is $R_{r, t}$:

$$\sum_{j \in \mathcal{P}} u_{j, r} \cdot y_{j, t} \le R_{r, t} \quad \forall r \in \mathcal{R}, \forall t \in \mathcal{T}$$

In CP-SAT, this is modeled via the cumulative scheduling constraint:
```python
for r in resources:
  model.AddCumulative(
      intervals=[interval_var[j] for j in projects if u[j, r] > 0],
      demands=[u[j, r] for j in projects if u[j, r] > 0],
      capacity=R[r],  # If stationary capacity
  )
```

---

## 5. Constraint Taxonomy: Inviolable Hard vs. Discretionary Policy Levers

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DIRS PHASE 6D-B CONSTRAINT CLASSIFICATION TAXONOMY              │
└────────────────────────────────────────────────────────────────────────────────────────┘

  TIER 1: INVIOLABLE PHYSICAL & MATHEMATICAL HARD CONSTRAINTS (NEVER RELAXED)
  ───────────────────────────────────────────────────────────────────────────
  1. Selection Precedence Co-requisite:    w_j ≤ w_i              ∀ (i, j) ∈ E
  2. Timing Precedence with Lag:           S_j ≥ S_i + d_i + L_ij (when w_j = 1)
  3. Single Start Period Uniqueness:       ∑_t x_{j, t} = w_j ≤ 1
  4. Non-Preemptive Interval Execution:    C_j = S_j + d_j - 1
  5. Cash-Flow Solvency Recurrence:        Φ_t = η Φ_{t-1} + B_t - E_t ≥ 0
  6. Milestone Horizon Boundaries:         S_j ≥ E_j,  C_j ≤ T

  TIER 2: GOVERNANCE & POLICY CONSTRAINTS (CONFIGURABLE ADMINISTRATIVE POLICY)
  ───────────────────────────────────────────────────────────────────────────
  1. Mandatory Life-Safety Mandate:        w_j = 1                ∀ j ∈ P_Tier1
  2. District Policy Equity Floor:         ∑_{j∈d} c_j w_j ≥ min(θ_d B, ∑ c_j)
  3. Uncontacted Blackout Ring-Fencing:    ∑ c_j w_j ≤ B - ∑_{blackout} θ_d B
  4. Renewable Resource Capacity Limits:   ∑ u_{j, r} y_{j, t} ≤ R_{r, t}
```

---

## 6. Mathematical Consistency & Dimensional Verification

1. **Dimensional Consistency:**
   - Budget envelopes $B_t$, project costs $c_j$, expenditures $E_t$, and cash reserves $\Phi_t$ all share identical dimensions (scaled integer INR currency).
   - Variables $w_j, x_{j, t}, y_{j, t}$ are dimensionless booleans.
   - Durations $d_j$, lags $L_{ij}$, start times $S_j$, and horizon $T$ share identical dimensions (discrete integer time periods).
2. **Bounded Feasible Region:**
   - The decision space is bounded: $w_j \in \{0, 1\}^N$, $x_{j, t} \in \{0, 1\}^{N \times T}$.
   - The combinatorial search space is strictly finite ($\le 2^N \cdot T^N$), guaranteeing that CP-SAT will either prove optimality, find a feasible solution, or prove infeasibility in finite time.
