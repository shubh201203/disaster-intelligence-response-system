# DIRS Phase 6D-A — Exhaustive 3-Project Optimization Proof & Solvency Analysis
## Rigorous Combinatorial Enumeration, Explicit Start Schedules, District Accounting, and Optimality Verification

**Document ID:** `DIRS-PHASE6D-DOC-31`  
**Classification:** OPERATIONS RESEARCH & MATHEMATICAL OPTIMIZATION PROOF  
**Lead Authors:** Principal Operations Research Scientist & Mathematical Optimization Engineer  
**Date:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Problem Formulation & Exact Parameters

We formulate an explicit post-disaster project scheduling optimization instance to rigorously prove the interaction of:
1. **Mandatory Selection Precedence Co-requisites:** $w_j \le w_i$.
2. **Discrete Non-Preemptive Timing Precedence:** $S_j \ge S_i + d_i + L_{ij}$.
3. **Execution Age vs. Calendar Cash-Flow Mapping:** $C_{j, t} = \sum_{s = \max(1, t - d_j + 1)}^t \gamma_{j, (t - s + 1)} \cdot x_{j, s}$.
4. **Multi-Period Budget Carry-Forward & Solvency:** $\Phi_t = \Phi_{t-1} + B_t - E_t \ge 0$.
5. **District Policy Equity Targets & Dynamic Absorption Bounds:** $\sum_{j \in J_d} c_j w_j \ge \min(\underline{\theta}_d B, \sum_{j \in J_d} c_j)$.

---

### 1.1 Horizon & Budget Envelope Parameters
- Planning Horizon: $T = 3$ discrete calendar periods (e.g., 30-day blocks).
- Tranche Envelopes:
  - Period 1: $B_1 = 300.0$ Lakh INR.
  - Period 2: $B_2 = 200.0$ Lakh INR.
  - Period 3: $B_3 = 250.0$ Lakh INR.
- Total Available Capital: $B = B_1 + B_2 + B_3 = 750.0$ Lakh INR.
- Fiscal Carry-Forward Efficiency: $\eta = 1.00$ (Full liquidity preservation).
- District Allocation Targets:
  - District East Target: $\underline{\theta}_{\text{East}} = 0.40 \implies R_{\text{target}, \text{East}} = 300.0$ Lakh INR.
  - District West Target: $\underline{\theta}_{\text{West}} = 0.40 \implies R_{\text{target}, \text{West}} = 300.0$ Lakh INR.
  - Central Contingency Pool: $0.20 \implies 150.0$ Lakh INR.

---

### 1.2 Candidate Projects Specification

| Attribute | Project $P_1$ (Clinic Shoring) | Project $P_2$ (Trauma Ward Expansion) | Project $P_3$ (Shelter Roof Reconstruction) |
| :--- | :--- | :--- | :--- |
| **Geographic District** | District East ($J_{\text{East}}$) | District East ($J_{\text{East}}$) | District West ($J_{\text{West}}$) |
| **Demographic Baseline** | $P_{\text{census}} = 5,000$ (Verified) | $P_{\text{census}} = 5,000$ (Verified) | $P_{\text{census}} = \text{UNKNOWN}$ (`NULL`) |
| **Vulnerable Headcount** | $\psi_1 = 435 \implies \phi_V = 0.435$ | $\psi_2 = 300 \implies \phi_V = 0.300$ | $\psi_3 = 350 \implies \phi_V = 350/500 = \mathbf{0.700}$ |
| **Priority Score ($\Pi_j$)** | **$\Pi_1 = 75.0$** | **$\Pi_2 = 70.0$** | **$\Pi_3 = 60.0$** |
| **Duration ($d_j$)** | $d_1 = 1$ period | $d_2 = 2$ periods | $d_3 = 1$ period |
| **Execution Cost Vector ($\boldsymbol{\gamma}_j$)** | $\boldsymbol{\gamma}_1 = [200.0]$ Lakh | $\boldsymbol{\gamma}_2 = [100.0, \; 150.0]$ Lakh | $\boldsymbol{\gamma}_3 = [150.0]$ Lakh |
| **Total Project Cost ($c_j$)** | $c_1 = 200.0$ Lakh | $c_2 = 250.0$ Lakh | $c_3 = 150.0$ Lakh |
| **Precedence Dependency** | None (Root project) | **Mandatory Successor of $P_1$ ($L_{12} = 0$)** | None (Independent project) |

---

## 2. Complete Mathematical Optimization Model

### 2.1 The Objective Function
$$\text{Maximize } Z = \sum_{j=1}^3 \Pi_j \cdot w_j = 75.0 \cdot w_1 + 70.0 \cdot w_2 + 60.0 \cdot w_3$$

**Formal Component Definitions:**
- **Decision Variables:** Binary selection indicators $w_j \in \{0, 1\}$ for each candidate project $j \in \{1, 2, 3\}$.
- **Objective Coefficients ($\Pi_j$):** Verified additive Multi-Criteria Recovery Priority Index (MCPI) scores:
  - $\Pi_1 = 75.0$ (District East Clinic Shoring)
  - $\Pi_2 = 70.0$ (District East Trauma Ward Expansion)
  - $\Pi_3 = 60.0$ (District West Shelter Roof Reconstruction)
- **Additivity & Linearity:** Project priorities are purely additive linear weights representing total societal recovery utility.
- **Absence of Penalties or Bonuses:** The objective function contains zero penalty terms or soft artificial bonuses; all governance and physical rules are enforced strictly through hard constraints.

---

### 2.2 System Constraints (Full Model)

1. **Selection Precedence Co-requisite (Hard Constraint):**
   $$w_2 \le w_1$$
   (Project $P_2$ cannot be selected unless its mandatory prerequisite $P_1$ is selected).

2. **Start Variable Execution Uniqueness (Hard Constraint):**
   $$\sum_{t=1}^{T - d_j + 1} x_{j, t} = w_j \quad \forall j \in \{1, 2, 3\}$$
   - $P_1$: $x_{1, 1} + x_{1, 2} + x_{1, 3} = w_1$ (Allowed start periods $S_1 \in \{1, 2, 3\}$).
   - $P_2$: $x_{2, 1} + x_{2, 2} = w_2$ (Allowed start periods $S_2 \in \{1, 2\}$ due to $d_2 = 2, T = 3$).
   - $P_3$: $x_{3, 1} + x_{3, 2} + x_{3, 3} = w_3$ (Allowed start periods $S_3 \in \{1, 2, 3\}$).

3. **Discrete Timing Precedence with Zero Lag (Hard Constraint):**
   $$S_2 \ge S_1 + d_1 + L_{12} = S_1 + 1 + 0 = S_1 + 1 \quad (\text{if } w_2 = 1)$$

4. **Calendar-Period Expenditure Mapping:**
   $$E_1 = 200 \cdot x_{1, 1} + 100 \cdot x_{2, 1} + 150 \cdot x_{3, 1}$$
   $$E_2 = 200 \cdot x_{1, 2} + 150 \cdot x_{2, 1} + 100 \cdot x_{2, 2} + 150 \cdot x_{3, 2}$$
   $$E_3 = 200 \cdot x_{1, 3} + 150 \cdot x_{2, 2} + 150 \cdot x_{3, 3}$$

5. **Cash-Flow Solvency Invariants (Hard Constraint):**
   $$\Phi_1 = 300.0 - E_1 \ge 0$$
   $$\Phi_2 = \Phi_1 + 200.0 - E_2 \ge 0$$
   $$\Phi_3 = \Phi_2 + 250.0 - E_3 \ge 0$$

6. **District Policy Equity Constraints (Hard Constraints):**
   - **District East Policy Floor:**
     $$\sum_{j \in J_{\text{East}}} c_j \cdot w_j \ge \min(\underline{\theta}_{\text{East}} B, \; \sum_{j \in J_{\text{East}}} c_j) = \min(300.0, \; 450.0) = 300.0$$
     $$\implies 200.0 \cdot w_1 + 250.0 \cdot w_2 \ge 300.0$$
   - **District West Policy Floor:**
     $$\sum_{j \in J_{\text{West}}} c_j \cdot w_j \ge \min(\underline{\theta}_{\text{West}} B, \; \sum_{j \in J_{\text{West}}} c_j) = \min(300.0, \; 150.0) = 150.0$$
     $$\implies 150.0 \cdot w_3 \ge 150.0 \implies w_3 = 1$$

---

## 3. Exhaustive Combinatorial Enumeration of All 8 Configurations

To provide an incontrovertible mathematical proof of global optimality, we evaluate all $2^3 = 8$ configurations across four distinct levels of feasibility:
- **Level A (Selection & Precedence Feasibility):** Satisfies $w_2 \le w_1$.
- **Level B (Scheduling Feasibility):** Admits start periods $S_j$ satisfying duration boundaries and $S_2 \ge S_1 + 1$.
- **Level C (Liquidity & Solvency Feasibility):** Cash balances remain non-negative ($\Phi_t \ge 0 \; \forall t$).
- **Level D (Full-Model Feasibility):** Satisfies Levels A, B, C **AND** hard District East and West Equity Constraints.

| Config | Selection Vector $(w_1, w_2, w_3)$ | Level A (Precedence $w_2 \le w_1$) | Level B & C (Scheduling & Solvency) | District East Spend ($200w_1 + 250w_2 \ge 300$) | District West Spend ($150w_3 \ge 150$) | Full-Model Feasibility Status | Objective Value $Z$ |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Config 1** | $(0, 0, 0)$ | Pass ($0 \le 0$) | Pass | **$0.0 < 300$ (FAILED)** | **$0.0 < 150$ (FAILED)** | **INFEASIBLE UNDER FULL MODEL** (Violates East & West Equity) | Inadmissible ($0.0$) |
| **Config 2** | $(0, 0, 1)$ | Pass ($0 \le 0$) | Pass | **$0.0 < 300$ (FAILED)** | Pass ($150 \ge 150$) | **INFEASIBLE UNDER FULL MODEL** (Violates East Equity) | Inadmissible ($60.0$) |
| **Config 3** | $(0, 1, 0)$ | **FAILED ($1 \le 0$)** | Infeasible | Pass ($250 < 300 \implies$ Failed) | **$0.0 < 150$ (FAILED)** | **INFEASIBLE UNDER FULL MODEL** (Violates Precedence & Equity) | Inadmissible ($0.0$) |
| **Config 4** | $(0, 1, 1)$ | **FAILED ($1 \le 0$)** | Infeasible | **$250.0 < 300$ (FAILED)** | Pass ($150 \ge 150$) | **INFEASIBLE UNDER FULL MODEL** (Violates Precedence & East Equity) | Inadmissible ($0.0$) |
| **Config 5** | $(1, 0, 0)$ | Pass ($0 \le 1$) | Pass | **$200.0 < 300$ (FAILED)** | **$0.0 < 150$ (FAILED)** | **INFEASIBLE UNDER FULL MODEL** (Violates East & West Equity) | Inadmissible ($75.0$) |
| **Config 6** | $(1, 0, 1)$ | Pass ($0 \le 1$) | Pass | **$200.0 < 300$ (FAILED)** | Pass ($150 \ge 150$) | **INFEASIBLE UNDER FULL MODEL** (Violates East Equity) | Inadmissible ($135.0$) |
| **Config 7** | $(1, 1, 0)$ | Pass ($1 \le 1$) | Pass | Pass ($450 \ge 300$) | **$0.0 < 150$ (FAILED)** | **INFEASIBLE UNDER FULL MODEL** (Violates West Equity) | Inadmissible ($145.0$) |
| **Config 8** | **$(1, 1, 1)$** | **Pass ($1 \le 1$)** | **Pass** | **Pass ($450 \ge 300$)** | **Pass ($150 \ge 150$)** | **FEASIBLE UNDER FULL MODEL (UNIQUE)** | **$\mathbf{205.0}$ (GLOBAL OPTIMUM)** |

---

## 4. Rigorous Proof of Global Optimality

### 4.1 Proof by Unique Full-Model Feasibility
1. **Uniqueness:** Out of all $8$ combinatorial selection vectors, **Configuration 8 $(1, 1, 1)$ is the ONLY configuration that satisfies both the East and West equity constraints simultaneously while honoring selection precedence and cash-flow solvency**.
   - Configurations 1, 2, 5, 6 violate District East's hard equity floor ($200 w_1 + 250 w_2 < 300$).
   - Configurations 1, 3, 5, 7 violate District West's hard equity floor ($150 w_3 < 150$).
   - Configurations 3 and 4 violate mandatory selection precedence ($w_2 \le w_1$).
2. **Global Optimality:** Because the feasible region of the full model contains exactly one selection vector—Configuration $(1, 1, 1)$—it is **trivially and mathematically guaranteed to be the unique global optimum**.
3. **Objective Maximization:** Since all project priority coefficients are strictly positive ($\Pi_1, \Pi_2, \Pi_3 > 0$), Configuration $(1, 1, 1)$ also achieves the unconstrained theoretical upper bound:
   $$Z^* = \sum_{j=1}^3 \Pi_j = 75.0 + 70.0 + 60.0 = \mathbf{205.0}$$
   No feasible solution can exist with $Z > 205.0$, and all other configurations are infeasible under the full model.

### 4.2 Multiple Optimal Schedules
While the optimal project selection is unique ($(1, 1, 1)$), there exist **two alternate optimal schedules** that achieve the global optimum $Z = 205.0$:
- **Schedule A:** $(S_1 = 1, S_2 = 2, S_3 = 2)$
- **Schedule B:** $(S_1 = 1, S_2 = 2, S_3 = 3)$
Both schedules are fully solvent, satisfy all physical precedence lags, and achieve identical objective score $Z^* = 205.0$. Schedule A completes all projects by Period $t = 2$ (makespan 2), whereas Schedule B completes by Period $t = 3$ (makespan 3).

---

## 5. Explicit Schedule Solutions under Global Optimum $(1, 1, 1)$

### 5.1 Schedule Option A: Project $P_3$ Starts in Period 2 ($S_3 = 2$)
- **Scheduled Start Periods:**
  $$S_1 = 1, \quad S_2 = 2, \quad S_3 = 2$$
- **Detailed Execution Timeline:**
  - Period 1 ($t = 1$):
    - $P_1$ executes (Age $\tau = 1$): Cost $= 200.0$ Lakh.
    - $P_2$ is idle (waiting for $P_1$ to finish).
    - $P_3$ is idle.
    - Total Period 1 Spend: $E_1 = 200.0$ Lakh.
    - Closing Liquidity: $\Phi_1 = 300.0 - 200.0 = \mathbf{100.0 \text{ Lakh INR}} \ge 0$.
  - Period 2 ($t = 2$):
    - $P_1$ is complete.
    - $P_2$ begins (Age $\tau = 1$): Cost $= 100.0$ Lakh.
    - $P_3$ begins and completes (Age $\tau = 1$): Cost $= 150.0$ Lakh.
    - Total Period 2 Spend: $E_2 = 100.0 + 150.0 = 250.0$ Lakh.
    - Available Cash: $\Phi_1 + B_2 = 100.0 + 200.0 = 300.0$ Lakh.
    - Closing Liquidity: $\Phi_2 = 300.0 - 250.0 = \mathbf{50.0 \text{ Lakh INR}} \ge 0$.
  - Period 3 ($t = 3$):
    - $P_1$ is complete.
    - $P_2$ finishes (Age $\tau = 2$): Cost $= 150.0$ Lakh.
    - $P_3$ is complete.
    - Total Period 3 Spend: $E_3 = 150.0$ Lakh.
    - Available Cash: $\Phi_2 + B_3 = 50.0 + 250.0 = 300.0$ Lakh.
    - Closing Liquidity: $\Phi_3 = 300.0 - 150.0 = \mathbf{150.0 \text{ Lakh INR}} \ge 0$.

### 5.2 Schedule Option B: Project $P_3$ Starts in Period 3 ($S_3 = 3$)
- **Scheduled Start Periods:**
  $$S_1 = 1, \quad S_2 = 2, \quad S_3 = 3$$
- **Detailed Execution Timeline:**
  - Period 1 ($t = 1$): $E_1 = 200.0$ Lakh, Closing Liquidity $\Phi_1 = \mathbf{100.0 \text{ Lakh}} \ge 0$.
  - Period 2 ($t = 2$): $P_2$ executes (Cost $100.0$). $E_2 = 100.0$ Lakh, Closing Liquidity $\Phi_2 = 100.0 + 200.0 - 100.0 = \mathbf{200.0 \text{ Lakh}} \ge 0$.
  - Period 3 ($t = 3$): $P_2$ finishes (Cost $150.0$), $P_3$ executes (Cost $150.0$). $E_3 = 300.0$ Lakh.
    - Available Cash: $\Phi_2 + B_3 = 200.0 + 250.0 = 450.0$ Lakh.
    - Closing Liquidity: $\Phi_3 = 450.0 - 300.0 = \mathbf{150.0 \text{ Lakh INR}} \ge 0$.

### 5.3 Why $S_3 = 1$ is Mathematically INFEASIBLE
- If $P_3$ were scheduled to start at period $t = 1$ alongside $P_1$:
  $$E_1 = C_{1, 1} + C_{3, 1} = 200.0 + 150.0 = 350.0 \text{ Lakh}$$
  $$\Phi_1 = B_1 - E_1 = 300.0 - 350.0 = -50.0 \text{ Lakh INR}$$
  $$\Phi_1 \ge 0 \implies -50.0 \ge 0 \quad (\mathbf{CONTRADICTION — INFEASIBLE})$$
- Therefore, $P_3$ **must start in Period 2 or Period 3**. Both options yield the identical maximum objective score $Z = 205.0$.

---

## 6. District Accounting & Policy Reserve Reconciliation

| Accounting Dimension | District East | District West | Central Pool | Total System Ledger |
| :--- | :---: | :---: | :---: | :---: |
| **Approved Budget Share ($\underline{\theta}_d B$)** | $300.0$ Lakh ($40\%$) | $300.0$ Lakh ($40\%$) | $150.0$ Lakh ($20\%$) | $750.0$ Lakh ($100\%$) |
| **Submitted Project Volume** | $c_1 + c_2 = 450.0$ Lakh | $c_3 = 150.0$ Lakh | — | $600.0$ Lakh |
| **Dynamic Absorption Floor** | $\min(300, 450) = \mathbf{300.0}$ Lakh | $\min(300, 150) = \mathbf{150.0}$ Lakh | — | $450.0$ Lakh |
| **Committed Capital Expenditure** | $200 + 250 = \mathbf{450.0}$ Lakh | $150.0 = \mathbf{150.0}$ Lakh | — | $\mathbf{600.0 \text{ Lakh}}$ |
| **District Equity Compliance** | **SATISFIED** ($450 \ge 300$) | **SATISFIED** ($150 \ge 150$) | — | **100% Compliant** |
| **Unspent Administrative Reserve** | $0.0$ Lakh | $\mathbf{150.0 \text{ Lakh}}$ (Encumbered) | $0.0$ Lakh | $\mathbf{150.0 \text{ Lakh}}$ |
| **Final Closing Liquidity ($\Phi_3$)** | — | — | — | $\mathbf{150.0 \text{ Lakh INR}}$ |

**Accounting Invariant Verified:**
$$\text{Total Expenditure} + \text{Closing Cash Balance} = 600.0 + 150.0 = 750.0 \text{ Lakh} \equiv B$$
Every single rupee is accounted for with zero leakage or duplication.

---
*End of DIRS Phase 6D-A Task 5 Proof Document.*
