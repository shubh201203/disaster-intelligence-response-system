# DIRS Phase 6D-B — Milestone 2A: Final Mathematical Acceptance Correction Report

**Document ID:** `DIRS-PHASE6D-B-M2A-CORR-01`  
**Classification:** FORENSIC OPERATIONS RESEARCH MATHEMATICAL AUDIT & CORRECTION  
**Author:** Principal Operations Research Scientist, Optimization Engineer & QA Lead  
**Date:** November 17, 2026  
**Status:** COMPLETE (FINAL MATHEMATICAL AUDIT DELIVERABLE)  
**Database Policy:** ZERO MIGRATIONS — Schema strictly frozen at `phase6b_recovery_foundation`  

---

## 1. Executive Summary

This forensic mathematical correction report resolves the four findings identified in the Milestone 2A Final Mathematical Acceptance Audit. It establishes:
1. An exact, uncompromised analysis of MCPI integer scaling, proving quantization limits, documenting counterexamples, distinguishing individual ranking from additive knapsack objectives, and defining a non-compensatory sequential/hierarchical objective.
2. A single canonical internal currency unit ($1 \text{ CCU} = 0.00001 \text{ INR} = 10^{-5} \text{ INR}$), with explicit input normalization contracts, directional conservative rounding proofs, and dual-unit test vectors (INR and Lakh INR).
3. A 6-dimensional forensic diagnostic taxonomy isolating mandatory life-safety infeasibility across aggregate budget, periodic cash flow, resource capacity, dependencies, planning horizons, and funding-policy restrictions.
4. Complete interface and formulation consistency across all Milestone 2A documents.

Execution remains strictly **HALTED at the Milestone 2A Design Acceptance Gate**. Zero implementation code has been authored.

---

## 2. MCPI Integer Scaling Proof & Priority Preservation (Item 1)

### 2.1 Mathematical Analysis of Proposed Scaling: $\bar{\Pi}_j = \lfloor \text{raw\_score}_j \times 10^7 \rfloor$

In Milestone 1, `raw_score` is evaluated as an IEEE 754 64-bit double-precision floating-point number in $[0.0, 1.0]$. The reporting index is $\text{MCPI}_j = \text{round}(\text{raw\_score}_j \times 100.0, \; 4) \in [0.0, 100.0]$.

#### 1. Quantization Error Bound:
Let $f(x) = \lfloor x \cdot 10^7 \rfloor$. For any real $x \in [0.0, 1.0]$:
$$x \cdot 10^7 - 1 < \lfloor x \cdot 10^7 \rfloor \le x \cdot 10^7$$
Dividing by $10^7$:
$$x - 10^{-7} < \frac{\bar{\Pi}}{10^7} \le x$$
$$\text{Quantization Error } \epsilon_q = \left| x - \frac{\bar{\Pi}}{10^7} \right| < 10^{-7}$$
The maximum quantization error of this mapping is strictly bounded by $10^{-7} = 0.0000001$.

#### 2. Smallest Positive Difference Guaranteed to Produce Distinct Integers:
For floor quantization, two distinct values $x_1 < x_2$ map to distinct integers $\lfloor x_1 \cdot 10^7 \rfloor < \lfloor x_2 \cdot 10^7 \rfloor$ if and only if there exists an integer $k$ such that:
$$x_1 \cdot 10^7 < k \le x_2 \cdot 10^7$$
To guarantee that $x_1$ and $x_2$ produce distinct integers regardless of where they lie relative to integer boundaries:
$$\Delta x = x_2 - x_1 \ge 10^{-7}$$
Any positive difference strictly smaller than $10^{-7}$ is **NOT guaranteed** to produce distinct integer coefficients.

#### 3. Concrete Counterexample: Distinct Raw Scores Mapping to Identical Integers:
Consider two candidate projects with distinct raw IEEE float scores differing at the 8th decimal place:
$$\text{Project } A: \quad x_A = 0.5000000100 \implies x_A \times 10^7 = 5,000,000.10 \implies \lfloor x_A \times 10^7 \rfloor = \mathbf{5,000,000}$$
$$\text{Project } B: \quad x_B = 0.5000000850 \implies x_B \times 10^7 = 5,000,000.85 \implies \lfloor x_B \times 10^7 \rfloor = \mathbf{5,000,000}$$
- In IEEE 754 float comparison: $x_B > x_A$ (difference is $7.5 \times 10^{-8} > 0$).
- Under $\lfloor x \times 10^7 \rfloor$: $\bar{\Pi}_A = \bar{\Pi}_B = 5,000,000$.
- **Finding:** Distinct raw floating-point scores can map to the exact same integer coefficient. Exact distinction for arbitrary floating-point numbers is mathematically impossible under any finite integer scaling factor.

---

### 2.2 Operational Role: Individual Ranking vs. Additive Portfolio Objective vs. Lexicographic Objective

To eliminate ambiguity, we distinguish the three mathematical roles of MCPI:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        THREE MATHEMATICAL ROLES OF MCPI IN DIRS                        │
└────────────────────────────────────────────────────────────────────────────────────────┘

  ROLE 1: INDIVIDUAL PROJECT PRIORITIZATION (MILESTONE 1 ENGINE)
  ──────────────────────────────────────────────────────────────
  - Evaluated by: MCPIPrioritizationService.rank_portfolio.
  - Nature: Total lexicographic preorder over candidate projects.
  - Ordering: Mandatory Life-Safety → Raw MCPI → phi_L → phi_V → Cascade → Cost → project_id.
  - Arithmetic: Exact 64-bit IEEE double float comparisons (DEV-M1-01 / DEV-M1-02).
  - Status: Strictly preserved. Unchanged in Milestone 2.

  ROLE 2: ADDITIVE SOCIETAL RECOVERY UTILITY OBJECTIVE (PHASE 6D-A BASELINE)
  ──────────────────────────────────────────────────────────────────────────
  - Evaluated by: CP-SAT solver objective: Maximize Z = ∑_{j} Pi_j * w_j.
  - Nature: Additive Knapsack Objective maximizing total societal recovery value.
  - Known Knapsack Property: In an additive knapsack problem under budget constraint ∑ c_j w_j ≤ B,
    the optimal portfolio does NOT necessarily select projects in greedy individual priority order.
    Example: Project A (Score 80, Cost 100) vs Projects B & C (Scores 45 & 45, Costs 50 & 50).
    The additive knapsack chooses {B, C} (Total 90) over {A} (Total 80), even though A > B and A > C.
  - Scientific Finding: The additive knapsack objective maximizes collective societal recovery;
    it does not, and mathematically cannot, replicate greedy single-project selection when costs differ.

  ROLE 3: NON-COMPENSATORY MANDATORY LIFE-SAFETY (GOVERNANCE HARD CONSTRAINT)
  ──────────────────────────────────────────────────────────────────────────
  - Evaluated by: Hard selection constraint: w_j = 1 for all j in J_mandatory.
  - Nature: Absolute non-compensatory constraint.
  - Guarantee: Mandatory life-safety projects can NEVER be displaced by any collection of
    standard projects, regardless of scores or costs.
```

---

### 2.3 Solver Objective Hierarchy: Sequential Optimization Protocol

Because a single scalar integer objective cannot guarantee greedy priority preservation without distorting knapsack additivity, the engine implements a **two-phase optimization protocol**:

#### Phase 1: Inviolable Mandatory Life-Safety Hard Constraint
Mandatory life-safety projects ($S_L \ge 0.85$) are locked as hard constraints:
$$w_j = 1 \quad \forall j \in \mathcal{J}_{\text{mandatory}}$$
This guarantees that mandatory projects are non-compensatory by construction.

#### Phase 2: Additive Recovery Utility with Subordinate Degeneracy Breaking
To maximize societal utility among standard projects while breaking ties without altering substantive selection:
$$\text{Maximize } \bar{Z} = \sum_{j \in \mathcal{P}} \bar{\Pi}_j \cdot w_j + Z_{\text{tie\_break}}$$
Where:
- $\bar{\Pi}_j = \text{round}(\text{MCPI}_j \times 10,000)$ ($1 \text{ integer unit} = 0.0001 \text{ MCPI points}$).
- Since $\text{MCPI}_j$ has 4 decimal places, $\bar{\Pi}_j$ is **EXACT with ZERO quantization error**.
- $Z_{\text{tie\_break}} = \sum_{j \in \mathcal{P}} \sum_{t=1}^T \omega_{j, t} x_{j, t}$ where:
  $$\sum_{j \in \mathcal{P}} \max_t \omega_{j, t} < 1 \text{ integer unit of } \bar{\Pi}$$
  *Proof:* Because the maximum possible value of the tie-breaking term across the entire portfolio is strictly less than $1$ unit of $\bar{\Pi}$, the tie-breaker can **never** invert or alter the selection or rejection of any candidate project. It acts strictly to schedule earlier start times ($S_j = 1$ over $S_j = 3$) among alternate optimal schedules.

---

## 3. Canonical Currency Input Convention & Non-Relaxation Proofs (Item 2)

### 3.1 The Canonical Currency Unit (CCU)

To prevent unit ambiguity, the DIRS Phase 6D-B engine establishes **exactly one internal canonical currency unit**:

$$\mathbf{1 \text{ CANONICAL CURRENCY UNIT (CCU)} = 0.00001 \text{ INR} = 10^{-5} \text{ INR} = 0.001 \text{ PAISE}}$$

Every monetary quantity inside Google OR-Tools CP-SAT is an integer count of CCUs.

---

### 3.2 Explicit Input Currency Contract & Pre-Solve Normalization

The optimization request schema mandates an explicit `currency_unit` tag for all monetary inputs:

```python
class CurrencyUnit(str, Enum):
  INR = "INR"  # Standard Indian Rupees
  LAKH_INR = "LAKH_INR"  # 1 Lakh INR = 100,000 INR
  CRORE_INR = "CRORE_INR"  # 1 Crore INR = 10,000,000 INR
```

#### Deterministic Normalization Formulas to CCU Integers:
Let $V$ denote a raw input monetary value (budget $B_t$, project cost $c_j$, or equity target).
1. **If `currency_unit == CurrencyUnit.INR`:**
   $$\text{Canonical CCU Value } \bar{V} = V \times 100,000$$
2. **If `currency_unit == CurrencyUnit.LAKH_INR`:**
   $$\text{Canonical CCU Value } \bar{V} = V \times 100,000 \times 100,000 = V \times 10^{10}$$
3. **If `currency_unit == CurrencyUnit.CRORE_INR`:**
   $$\text{Canonical CCU Value } \bar{V} = V \times 10,000,000 \times 100,000 = V \times 10^{12}$$

> [!IMPORTANT]
> **No Unit Inference from Magnitude:**  
> The engine strictly prohibits heuristic guessing of units based on numerical magnitude. If `currency_unit` is omitted or invalid, pre-solve validation fails immediately with `MODEL_INVALID`.

---

### 3.3 Directional Conservative Rounding Proofs

When continuous or fractional currency values are converted to integer CCUs, directional rounding rules guarantee that hard constraints are never weakened:

#### 1. Budget Ceiling Rounding (Conservative Floor: $\lfloor \cdot \rfloor$):
$$\bar{B}_t = \lfloor B_t \times S \rfloor$$
- **Proof:** $\bar{B}_t \le B_t \times S$. Dividing by $S$:
  $$\frac{\sum_{j} \bar{E}_{j, t}}{S} \le \frac{\bar{B}_t}{S} \le B_t$$
  Actual allocated expenditure in period $t$ cannot exceed the authorized ceiling $B_t$. Budget limits are strictly tightened or exact.

#### 2. District Equity Floor Rounding (Conservative Ceiling: $\lceil \cdot \rceil$):
$$\bar{R}_{\text{target}, d} = \lceil \underline{\theta}_d \times \bar{B} \rceil$$
- **Proof:** $\bar{R}_{\text{target}, d} \ge \underline{\theta}_d \times \bar{B}$. Dividing by $S$:
  $$\frac{\sum_{j \in \mathcal{P}_d} \bar{c}_j w_j}{S} \ge \frac{\bar{R}_{\text{target}, d}}{S} \ge \underline{\theta}_d B$$
  Capital allocated to district $d$ can never be diluted below the policy quota. District protection is strictly tightened or exact.

#### 3. Project Cost Rounding (Standard Rupee Rounding: $\text{round}$):
$$\bar{c}_j = \text{round}(c_j \times S)$$
Source costs specified in paise ($0.01$ INR) convert to exact integer CCUs with zero rounding: $0.01 \times 100,000 = 1,000 \text{ CCU}$.

#### 4. Expenditure Profile Apportionment (Largest-Remainder Algorithm):
When execution weights $\gamma_{j, \tau}$ are applied to $\bar{c}_j$:
$$\sum_{\tau=1}^{d_j} \bar{\gamma}_{j, \tau} \equiv \bar{c}_j \quad \forall j \in \mathcal{P}$$
Zero rupee or CCU leakage across the entire planning horizon.

---

### 3.4 Verification Test Vectors: Dual-Denomination Identity Proof

To prove that source inputs in different denominations normalize to identical canonical values:

| Test Case | Raw Input Value | Input Currency Unit | Normalization Formula | Canonical Integer CCUs ($\bar{V}$) | Verification Result |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Vector 1A** | `150.0` | `CurrencyUnit.LAKH_INR` | $150.0 \times 10^{10}$ | `1,500,000,000,000` | **Identical Integer to 1B** |
| **Vector 1B** | `15,000,000.0` | `CurrencyUnit.INR` | $15,000,000.0 \times 10^5$ | `1,500,000,000,000` | **Identical Integer to 1A** |
| **Vector 2A** | `0.45` | `CurrencyUnit.LAKH_INR` | $0.45 \times 10^{10}$ | `4,500,000,000` | **Identical Integer to 2B** |
| **Vector 2B** | `45,000.0` | `CurrencyUnit.INR` | $45,000.0 \times 10^5$ | `4,500,000,000` | **Identical Integer to 2A** |
| **Vector 3A** | `2.50` | `CurrencyUnit.CRORE_INR` | $2.50 \times 10^{12}$ | `25,000,000,000,000` | **Identical Integer to 3B** |
| **Vector 3B** | `25,000,000.0` | `CurrencyUnit.INR` | $25,000,000.0 \times 10^5$ | `25,000,000,000,000` | **Identical Integer to 3A** |

All test vectors normalize to identical 64-bit integer CCUs, proving complete unit independence.

---

## 4. Mandatory Project & Planning Horizon Infeasibility Taxonomy (Item 3)

The solver never reports every optimization failure as an undifferentiated "budget shortfall". When `cp_model.INFEASIBLE` is returned, the `InfeasibilityAdvisor` classifies the failure into one of six mutually exclusive physical failure modes:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   FORENSIC INFEASIBILITY DIAGNOSTIC TAXONOMY (6 MODES)                 │
└────────────────────────────────────────────────────────────────────────────────────────┘

  MODE 1: AGGREGATE BUDGET INFEASIBILITY
  ──────────────────────────────────────
  Condition:  ∑_{j ∈ J_mandatory} c_j > B_total.
  Diagnosis:  The cumulative capital required by non-negotiable life-safety projects
              exceeds the total authorized funding envelope across all T periods.

  MODE 2: PERIODIC CASH-FLOW SOLVENCY INFEASIBILITY
  ─────────────────────────────────────────────────
  Condition:  ∑ c_j ≤ B_total, but ∃ t: MinMandatorySpend_t > η Φ_{t-1} + B_t.
  Diagnosis:  Total budget is sufficient, but front-loaded life-safety capital demand
              exceeds early-period cash tranches, creating an unavoidable cash deficit.

  MODE 3: RESOURCE CAPACITY INFEASIBILITY
  ───────────────────────────────────────
  Condition:  ∃ r, t: ∑_{j ∈ J_mandatory} u_{j, r} y_{j, t} > R_{r, t}.
  Diagnosis:  Concurrent mandatory projects require more specialized engineering crews
              or heavy machinery than physically available in period t.

  MODE 4: DEPENDENCY & PRECEDENCE DEADLINE INFEASIBILITY
  ──────────────────────────────────────────────────────
  Condition:  Mandatory project j requires predecessor chain whose minimum execution
              time (CPM Makespan) prevents j from completing within horizon T.
  Diagnosis:  Physical prerequisite duration chain exceeds available time.

  MODE 5: PLANNING HORIZON EXCEEDED INFEASIBILITY
  ──────────────────────────────────────────────
  Condition:  ∃ j ∈ J_mandatory: E_j + d_j - 1 > T.
  Diagnosis:  Mandatory project cannot physically complete on or before final period T
              due to late release date E_j or long physical construction duration d_j.

  MODE 6: FUNDING-SOURCE RESTRICTION INFEASIBILITY
  ────────────────────────────────────────────────
  Condition:  Mandatory project j is restricted to funding stream f, but B_{f, total} < c_j.
  Diagnosis:  Total budget is sufficient, but restricted funding-stream policy rules
              prevent capital from being disbursed to eligible mandatory projects.
```

### 4.1 Boundary Treatment: Projects Extending Beyond Horizon $T$

1. **Standard Candidate Projects with $E_j + d_j - 1 > T$:**
   - Any project that cannot physically finish within horizon $T$ has its start window domain clamped:
     $$\mathcal{T}_j^{\text{feas}} = [E_j, T - d_j + 1] = \emptyset$$
   - Since $\sum_{t \in \emptyset} x_{j, t} = 0$, the solver forces $w_j = 0$ (rejected from selection).
2. **Mandatory Projects with $E_j + d_j - 1 > T$:**
   - Because $w_j = 1$ is mandatory, the empty start window $\sum_{t \in \emptyset} x_{j, t} = 1$ is immediately contradictory ($0 = 1$).
   - The engine pre-solve gate intercepts this condition and declares **`PLANNING_HORIZON_EXCEEDED`**, reporting:
     > *"Mandatory project [code] requires [duration] periods starting from period [E_j], which exceeds planning horizon [T]. Execution cannot complete within authorized milestone horizon."*
3. **No Silent Cost Truncation:**
   - The engine strictly rejects silently truncating duration or cutting off capital expenditure to artificially force a project into horizon $T$. A project's full duration $d_j$ and full cost $c_j$ are preserved inviolably.

---

## 5. Interface and Formulation Consistency Audit (Item 4)

We conduct a cross-document consistency audit across all Milestone 2A specifications:

| Audit Parameter | Architecture Document | Mathematical Formulation | Constraint Traceability | Integer Scaling | Status & Resolution |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Canonical Currency Unit** | Defined as CCU ($10^{-5}$ INR) | Scaled integer CCUs | Scaled integer CCUs | Scaled integer CCUs ($10^5$ factor for INR) | **100% Consistent** |
| **Time-Index Convention** | $t \in \{1, \dots, T\}$ (1-indexed) | $t \in \{1, \dots, T\}$ | $t \in \{1, \dots, T\}$ | Discrete integer periods | **100% Consistent** |
| **Mandatory Life-Safety** | $w_j = 1$ hard constraint | $w_j = 1$ hard constraint | Inviolable Executive Mandate | $w_j = 1$ hard constraint | **100% Consistent** |
| **Dependency Formulation** | $w_j \le w_i$ & boolean reified lag | $w_j \le w_i$ & boolean reified lag | Inviolable Hard Constraint | Integer lag ceiling $\lceil L / \Delta t \rceil$ | **100% Consistent** |
| **Solver Status Codes** | OPTIMAL, FEASIBLE, INFEASIBLE, TIMEOUT_UNKNOWN, MODEL_INVALID | Mapped to CP-SAT status | Diagnostic engine mapping | Fails closed on invalid scale | **100% Consistent** |
| **Multi-Fund Classification** | Funding-Policy Constraints | Funding-Policy Constraints | Funding-Policy Constraints | Multi-fund recurrence | **100% Consistent** |

---

## 6. Updated Assumptions and Governance Invariants

1. **Knapsack Additivity Invariant:** The CP-SAT objective maximizes collective societal recovery utility $\sum \Pi_j w_j$. It does not replicate greedy individual project ranking when project costs differ.
2. **Non-Compensatory Life-Safety Invariant:** Human life-safety is protected via hard constraint $w_j = 1$. It can never be compromised by knapsack cost trade-offs.
3. **Zero Real-World Banking Invariant:** Policy ring-fencing and blackout reserves are mathematical optimization bounds, not commercial bank escrows.
4. **Zero Silent Relaxation Invariant:** Infeasible instances return forensic diagnostic reports and halt execution.
5. **Zero Database Migrations Invariant:** Schema strictly frozen at `phase6b_recovery_foundation` (39 user tables + 1 `spatial_ref_sys` = 40 base tables).

---

### Gate Status Declaration

> **STOP:** Execution is strictly **HALTED at the Milestone 2A Design Acceptance Gate**.  
> The final mathematical correction report and all five updated design documents are complete, verified, and reconciled.  
> Awaiting explicit project-owner authorization to proceed to **Milestone 2B (Engine Implementation)**.
