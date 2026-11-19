# DIRS Phase 6D-B: Mathematical Traceability & Formulation Specification

**Subsystem:** Disaster Intelligence and Response System (DIRS)  
**Phase:** 6D-B — Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine  
**Milestone:** Milestone 6 — Final Architecture Treatise & Permanent Freeze  
**Status:** Certified & Frozen  
**Date:** November 2026  

---

## 1. Mathematical Notation & Definitions

Let the recovery optimization problem be defined over the following discrete sets and parameters:

- $\mathcal{P} = \{1, \dots, N\}$: Set of candidate recovery projects, with $N \le 500$.
- $\mathcal{T} = \{1, \dots, T\}$: Set of discrete planning periods, with $T \in [1, 120]$.
- $\mathcal{D}$: Set of geographic districts affected by the disaster event.
- $\mathcal{R}$: Set of renewable resource types (e.g., excavators, structural engineers).
- $\mathcal{F}$: Set of available funding sources under Model B indivisible assignment.
- $\mathcal{E} \subset \mathcal{P} \times \mathcal{P}$: Directed precedence edges $(u, v)$ where project $u$ must finish before $v$ can start.

### Project Parameters:
- $c_i \in \mathbb{Z}^+$: Total estimated project cost in Currency-Cent Units ($1\text{ INR} = 100\text{ CCU}$).
- $d_i \in \{1, \dots, T\}$: Duration in periods for project $i$.
- $r_i \in \mathcal{T}$: Earliest release period for project $i$.
- $\bar{d}_i \in \mathcal{T}$: Hard deadline period for project $i$ ($r_i + d_i - 1 \le \bar{d}_i \le T$).
- $S_i \in [0.0, 1.0]$: Normalized Multi-Criteria Prioritization Index (MCPI) score for project $i$.
- $u_{i, r} \in \mathbb{Z}_{\ge 0}$: Renewable resource demand of project $i$ for resource $r \in \mathcal{R}$.
- $w_{i, \tau} \in [0.0, 1.0]$: Fractional expenditure weight of project $i$ at relative execution offset $\tau \in \{0, \dots, d_i - 1\}$, where $\sum_{\tau=0}^{d_i-1} w_{i, \tau} = 1.0$.

### Policy & Financial Parameters:
- $B_0 \in \mathbb{Z}_{\ge 0}$: Initial cash reserve in CCU cents.
- $B_t \in \mathbb{Z}_{\ge 0}$: Periodic budget allocation inflow in period $t \in \mathcal{T}$.
- $\gamma \in [0.0, 1.0]$: Fiscal retention rate (carryover fraction from period $t$ to $t+1$).
- $\theta_d \in [0.0, 1.0]$: District equity floor target for district $d \in \mathcal{D}$.
- $\mathcal{D}_{\text{blackout}} \subset \mathcal{D}$: Set of uncontacted blackout districts.
- $T_{\text{mand}} \in \mathcal{T}$: Caller-mandatory safety start deadline (RSK-M2-07).

---

## 2. Decision Variables

For each candidate project $i \in \mathcal{P}$:
1. **Selection Variable:**
   $$w_i \in \{0, 1\}, \quad w_i = 1 \iff \text{project } i \text{ is selected for funding and execution.}$$
2. **Start Period Variable:**
   $$x_{i, t} \in \{0, 1\}, \quad x_{i, t} = 1 \iff \text{project } i \text{ starts exactly at period } t \in \{r_i, \dots, \bar{d}_i - d_i + 1\}.$$
3. **Optional Execution Interval:**
   $$\text{IntervalVar}(i): \text{start } \in [r_i, \bar{d}_i - d_i + 1], \quad \text{size } = d_i, \quad \text{end } \in [r_i + d_i, \bar{d}_i + 1], \quad \text{is\_present } = w_i.$$

---

## 3. Objective Function Formulation

The objective function maximizes social benefit while penalizing delayed starts, implemented as a pure 64-bit integer linear combination:

$$\max \quad \mathcal{Z} = \sum_{i \in \mathcal{P}} \left( \alpha_i \cdot w_i - \sum_{t=r_i}^{\bar{d}_i - d_i + 1} \beta_{i, t} \cdot x_{i, t} \right)$$

Where:
- $\alpha_i = \lfloor 10^7 \cdot S_i \rfloor$: Primary benefit weight scaled to prevent precision loss.
- $\beta_{i, t} = \lfloor 10^3 \cdot (t - r_i) \rfloor$: Secondary early-start penalty ensuring projects start as early as feasible.

---

## 4. The 10 Core Constraints

### Constraint 1: Unique Execution Window
A selected project must start exactly once within its feasible temporal window:
$$\sum_{t=r_i}^{\bar{d}_i - d_i + 1} x_{i, t} = w_i \quad \forall i \in \mathcal{P}$$

### Constraint 2: Precedence Dependencies with Lags
If $(u, v) \in \mathcal{E}$ with lag $L_{u, v} \ge 0$, then project $v$ cannot start until project $u$ completes plus the lag period:
$$\text{start}_v \ge \text{start}_u + d_u + L_{u, v} \quad \text{only if } w_u = 1 \land w_v = 1$$
If $w_v = 1$, then $w_u = 1$ is strictly enforced:
$$w_v \le w_u \quad \forall (u, v) \in \mathcal{E}$$

### Constraint 3: Multi-Period Cash-Flow Solvency
For every period $t \in \mathcal{T}$, cumulative project expenditure up to period $t$ cannot exceed available cumulative budget cash flows:
$$\sum_{s=1}^t \sum_{i \in \mathcal{P}} \text{Spend}(i, s) \le \text{CumulativeBudget}(t) \quad \forall t \in \mathcal{T}$$
Where the periodic spend of project $i$ at period $s$ is:
$$\text{Spend}(i, s) = \sum_{k=\max(r_i, s - d_i + 1)}^{\min(s, \bar{d}_i - d_i + 1)} x_{i, k} \cdot \left( c_i \cdot w_{i, s - k} \right)$$

### Constraint 4: District Policy Equity Floors
For each district $d \in \mathcal{D}$ with target quota $\theta_d$:
$$\sum_{i \in \mathcal{P} \,|\, \text{district}(i) = d} c_i \cdot w_i \ge \min \left( \lceil \theta_d \cdot B_{\text{total}} \rceil, \sum_{i \,|\, \text{district}(i)=d} c_i \right)$$

### Constraint 5: Uncontacted Blackout District Ring-Fencing
For blackout districts $d \in \mathcal{D}_{\text{blackout}}$, the equity quota is ring-fenced as an untouchable escrow reserve $R_{\text{blackout}}$:
$$R_{\text{blackout}} = \sum_{d \in \mathcal{D}_{\text{blackout}}} \lceil \theta_d \cdot B_{\text{total}} \rceil$$
Total allocable spend across all selected candidate projects is strictly bounded:
$$\sum_{i \in \mathcal{P}} c_i \cdot w_i \le B_{\text{total}} - R_{\text{blackout}}$$

### Constraint 6: Renewable Resource Capacity Limits
For every resource $r \in \mathcal{R}$ and period $t \in \mathcal{T}$, concurrent resource utilization cannot exceed capacity $C_{r, t}$:
$$\sum_{i \in \mathcal{P}} u_{i, r} \cdot \left( \sum_{s=\max(1, t - d_i + 1)}^t x_{i, s} \right) \le C_{r, t} \quad \forall r \in \mathcal{R}, \forall t \in \mathcal{T}$$

### Constraint 7: Caller-Mandatory Life-Safety Start Deadlines (RSK-M2-07)
For all Tier-1 life-safety mandatory projects ($i \in \mathcal{P}_{\text{mand}}$):
$$w_i = 1 \quad \forall i \in \mathcal{P}_{\text{mand}}$$
$$\text{start}_i \le T_{\text{mand}} \quad \forall i \in \mathcal{P}_{\text{mand}}$$

### Constraint 8: Indivisible Funding Assignment (Model B)
Each selected project is funded by at most one discrete funding source:
$$\sum_{f \in \mathcal{F}} z_{i, f} = w_i \quad \forall i \in \mathcal{P}$$
$$\sum_{i \in \mathcal{P}} c_i \cdot z_{i, f} \le \text{Capacity}(f) \quad \forall f \in \mathcal{F}$$

### Constraint 9: Release and Deadline Window Bounds
$$\text{start}_i \ge r_i \cdot w_i \quad \forall i \in \mathcal{P}$$
$$\text{start}_i + d_i - 1 \le \bar{d}_i \cdot w_i + T \cdot (1 - w_i) \quad \forall i \in \mathcal{P}$$

### Constraint 10: Fiscal Retention Carryover Dynamics
Unused cash $U_t$ at period $t$ carries over to $t+1$ discounted by retention rate $\gamma$:
$$U_t = \max(0, \text{Inflow}_t + \gamma \cdot U_{t-1} - \text{Spend}_t)$$

---

## 5. Infeasibility Diagnostic Engine (4-Tier Architecture)

When CP-SAT reports `INFEASIBLE`, the diagnostic subsystem classifies the mathematical root cause:
1. **Tier 1 — Proven Root Causes:** Analytical contradictions detected prior to or independent of solver search (e.g., $r_i > \bar{d}_i$, cyclic dependencies, or mandatory project $EarliestStart(i) > T_{\text{mand}}$).
2. **Tier 2 — Necessary Condition Violations:** Deficit of total budget versus mandatory candidate sum ($B_{\text{total}} < \sum_{i \in \mathcal{P}_{\text{mand}}} c_i$).
3. **Tier 3 — Solver-Assisted Hypotheses:** Extracted via OR-Tools CP-SAT `SufficientAssumptionsForInfeasibility()` using boolean assumption literals ($prec_{u, v}, solv_t, eq_d$).
4. **Tier 4 — Minimal Core Isolation:** Isolates irreducible inconsistent subsets (IIS) of conflicting constraints.
