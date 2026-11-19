# DIRS Phase 6D-A — DEF-6D-05: Calendar-Period Expenditure Indexing Proof
## Execution Age vs. Calendar Period, Cash-Flow Mapping, and Conservation Proofs

**Document ID:** `DIRS-PHASE6D-DOC-18`  
**Classification:** OPERATIONS RESEARCH & FINANCIAL MATHEMATICS AUDIT  
**Lead Authors:** Principal Disaster Recovery Financial Architect & Operations Research Scientist  
**Date:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Execution Age vs. Global Calendar Period Formalization (DEF-6D-05)

A frequent source of indexing bugs in multi-period project optimization is confusing **internal project execution age** with the **global calendar planning period**.

### 1.1 Strict Index Definitions
1. **Global Planning Horizon ($t$):**
   Discrete calendar intervals $t \in \{1, 2, \dots, T\}$, where each period represents a fixed calendar block (e.g., 30 days).
2. **Project Duration ($d_j$):**
   Total consecutive integer planning periods required to construct project $j$.
3. **Execution Age ($\tau$):**
   Relative progress step within the project's internal timeline:
   $$\tau \in \{1, 2, \dots, d_j\}$$
   where $\tau = 1$ is project mobilization, and $\tau = d_j$ is final commissioning.
4. **Internal Cost Profile Vector ($\boldsymbol{\gamma}_j$):**
   The time-indexed capital expenditure profile defined over execution age $\tau$:
   $$\boldsymbol{\gamma}_j = [\gamma_{j, 1}, \; \gamma_{j, 2}, \; \dots, \; \gamma_{j, d_j}]$$
   where $\gamma_{j, \tau} \ge 0$ is the capital required during relative age $\tau$.
5. **Project Total Capital Cost ($c_j$):**
   $$c_j = \sum_{\tau=1}^{d_j} \gamma_{j, \tau}$$
6. **Project Scheduled Start Period ($S_j$):**
   The calendar period $t$ at which project execution commences:
   $$S_j = \sum_{t=1}^{T - d_j + 1} t \cdot x_{j, t}$$
   where $x_{j, t} \in \{0, 1\}$ is the start indicator variable.

---

## 2. Calendar-Period Cash-Flow Mapping Function

When project $j$ is scheduled to start at period $S_j \in \{1, \dots, T - d_j + 1\}$, its actual expenditure in global calendar period $t \in \{1, \dots, T\}$ is given by:

$$C_{j, t}(S_j, w_j) = \begin{cases} 
0 & \text{if } t < S_j \text{ (Prior to start)} \\ 
\gamma_{j, (t - S_j + 1)} & \text{if } S_j \le t \le S_j + d_j - 1 \text{ (Active execution)} \\ 
0 & \text{if } t > S_j + d_j - 1 \text{ (Post completion)} 
\end{cases} \quad \text{for } w_j = 1$$
If $w_j = 0$ (project not selected), $C_{j, t} \equiv 0 \; \forall t$.

### 2.1 Linearization in Mixed-Integer Formulation
To express $C_{j, t}$ as a linear function of binary start variables $x_{j, s}$:
$$C_{j, t} = \sum_{s = \max(1, t - d_j + 1)}^t \gamma_{j, (t - s + 1)} \cdot x_{j, s}$$
Notice:
- If project $j$ starts at period $s$, then at calendar period $t \ge s$, the project's execution age is exactly $\tau = t - s + 1$.
- Because $\sum_s x_{j, s} \le 1$, at most one term in the summation is non-zero.

---

## 3. Worked Demonstration: Project Starting in Period 3 with Duration 3

Consider Project $P_A$:
- Total duration: $d_A = 3$ periods.
- Global planning horizon: $T = 6$ periods.
- Execution age cost profile:
  - Age $\tau = 1$ (Mobilization & Groundbreaking): $\gamma_{A, 1} = 150$ Lakh INR.
  - Age $\tau = 2$ (Heavy Structural Casting): $\gamma_{A, 2} = 300$ Lakh INR.
  - Age $\tau = 3$ (Finishing & Commissioning): $\gamma_{A, 3} = 100$ Lakh INR.
- Reconciled Total Project Cost:
  $$c_A = 150 + 300 + 100 = 550 \text{ Lakh INR}$$

### 3.1 Start Assignment
Suppose the solver selects Project $P_A$ and schedules it to start at calendar period $t = 3$:
$$x_{A, 3} = 1, \quad x_{A, s} = 0 \; \forall s \ne 3, \quad w_A = 1$$

### 3.2 Period-by-Period Cash-Flow Verification

| Global Calendar Period $t$ | Active Start Window $s \in [\max(1, t - 2), t]$ | Term Evaluated ($\gamma_{A, t - s + 1} \cdot x_{A, s}$) | Actual Cash Flow $C_{A, t}$ | Verification State |
| :---: | :---: | :--- | :---: | :--- |
| **$t = 1$** | $s \in [1, 1]$ | $\gamma_{A, 1} \cdot x_{A, 1} = 150 \times 0$ | **$0.0$** | **Zero spend before start** |
| **$t = 2$** | $s \in [1, 2]$ | $\gamma_{A, 2} x_{A, 1} + \gamma_{A, 1} x_{A, 2} = 0 + 0$ | **$0.0$** | **Zero spend before start** |
| **$t = 3$ (Start)** | $s \in [1, 3]$ | $\gamma_{A, 1} \cdot x_{A, 3} = 150 \times 1$ | **$150.0$ Lakh** | **Age $\tau = 1$ expenditure** |
| **$t = 4$** | $s \in [2, 4]$ | $\gamma_{A, 2} \cdot x_{A, 3} = 300 \times 1$ | **$300.0$ Lakh** | **Age $\tau = 2$ expenditure** |
| **$t = 5$ (Finish)** | $s \in [3, 5]$ | $\gamma_{A, 3} \cdot x_{A, 3} = 100 \times 1$ | **$100.0$ Lakh** | **Age $\tau = 3$ expenditure** |
| **$t = 6$** | $s \in [4, 6]$ | $s=3$ is outside window; sum $= 0$ | **$0.0$** | **Zero spend after completion** |

### 3.3 Lifetime Cost Reconciliation Proof
$$\sum_{t=1}^T C_{A, t} = 0 + 0 + 150 + 300 + 100 + 0 = 550 \text{ Lakh INR} \equiv c_A$$
**Reconciliation Invariant:**
$$\sum_{t=1}^T C_{j, t} = w_j \cdot c_j, \quad \forall j \in \mathcal{P}$$
Total multi-period expenditure matches the project's contracted capital cost to the exact rupee.

---

## 4. Multi-Project Aggregation & Period Budget Enforcement

Let multiple projects execute concurrently across the horizon.

### 4.1 Aggregate Period Expenditure
The total capital demand of all active recovery projects in calendar period $t$ is:
$$E_t = \sum_{j \in \mathcal{P}} C_{j, t} = \sum_{j \in \mathcal{P}} \sum_{s = \max(1, t - d_j + 1)}^t \gamma_{j, (t - s + 1)} \cdot x_{j, s}$$

### 4.2 Multi-Period Budget Carry-Forward Mechanics
Let $B_t$ denote the newly released government revenue tranche allocated to period $t$.
Let $\Phi_t \ge 0$ denote unspent cash carried forward from period $t$ into period $t+1$:

$$\Phi_t = \eta_t \cdot \Phi_{t-1} + B_t - E_t, \quad \forall t \in \{1, \dots, T\}$$
$$\Phi_0 \equiv 0$$
where $\eta_t \in [0.90, 1.0]$ is the fiscal carry-forward efficiency factor.

**Conservation & Non-Duplication Guarantees:**
1. **Solvency Guarantee ($\Phi_t \ge 0$):**
   $$E_t \le \eta_t \Phi_{t-1} + B_t$$
   Total capital expenditure in period $t$ can **never** exceed the sum of carried-over liquidity and the current tranche.
2. **No Phantom Funding Creation:**
   Because $\Phi_t$ is strictly defined as remaining liquid cash minus actual spent capital ($E_t$), money spent in period $t$ is permanently subtracted from the system. It cannot be spent again in period $t+1$.
3. **Cumulative Global Envelope Invariant:**
   Summing across all $T$ periods (with $\eta_t = 1.0$):
   $$\sum_{t=1}^T E_t + \Phi_T = \sum_{t=1}^T B_t = B_{\text{total}}$$
   Total expenditure across all projects plus final unspent surplus equals exactly the total authorized budget.

---

## 5. Multi-Source Funding Restrictions

Capital tranches originate from statutory sources with strict legal ring-fencing:
- $\mathcal{F} = \{\text{STATE\_SDRF}, \; \text{NATIONAL\_NDRF}, \; \text{MULTILATERAL\_WB}, \; \text{NGO\_AID}\}$.

For each funding source $f \in \mathcal{F}$:
- Let $B_{f, t}$ be the period-$t$ allocation from fund $f$.
- Let $u_{j, f} \in [0, 1]$ be the approved funding fraction of project $j$ supported by fund $f$ ($\sum_{f \in \mathcal{F}} u_{j, f} = 1.0$).

**Ring-Fencing Constraint:**
$$\Phi_{f, t} = \Phi_{f, t-1} + B_{f, t} - \sum_{j \in \mathcal{P}} u_{j, f} \cdot C_{j, t} \ge 0, \quad \forall f \in \mathcal{F}, \; \forall t$$
World Bank multilateral funds cannot be diverted to cover unauthorized state SDRF projects; each funding stream maintains independent solvency.

---
*End of DIRS Phase 6D-A DEF-6D-05 Remediation Document.*
