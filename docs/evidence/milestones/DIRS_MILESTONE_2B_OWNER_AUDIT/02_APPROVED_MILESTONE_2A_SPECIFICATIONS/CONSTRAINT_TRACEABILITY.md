# DIRS Phase 6D-B — Milestone 2A: Constraint Traceability Matrix

**Document ID:** `DIRS-PHASE6D-B-M2A-CONSTR-01`  
**Classification:** OPERATIONS RESEARCH CONSTRAINT SPECIFICATION & AUDIT TRACEABILITY  
**Author:** Principal Operations Research Scientist & Optimization Engineer  
**Date:** November 17, 2026  
**Status:** COMPLETE (MILESTONE 2A DESIGN SPECIFICATION)  
**Database Policy:** ZERO MIGRATIONS — Schema strictly frozen at `phase6b_recovery_foundation`  

---

## 1. Overview & Constraint Traceability Methodology

This document provides a forensic, equation-by-equation mapping for every constraint enforced in the **DIRS Phase 6D-B Recovery Optimization Engine**. 

Each constraint is defined mathematically, explained in operational terms, classified under the project's strict constraint taxonomy (Inviolable Hard vs. Discretionary Policy), mapped to its approved Phase 6D-A source specification, and paired with an automated validation and test strategy.

---

## 2. Exhaustive Constraint Traceability Matrix

### Constraint 1: Multi-Period Cash-Flow Solvency Recurrence

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $\Phi_t = \eta \cdot \Phi_{t-1} + B_t - E_t \ge 0, \quad \forall t \in \{1, \dots, T\}, \quad \Phi_0 = 0$ |
| **Plain-Language Explanation** | The total expenditure in any calendar period $t$ cannot exceed the sum of new budget released in period $t$ ($B_t$) plus unspent liquid cash carried over from the prior period ($\eta \Phi_{t-1}$). The system cannot run a cash deficit in any period. |
| **Relevant Input Fields** | `budget_envelopes: List[float]`, `fiscal_retention_rate: float` ($\eta \in [0.0, 1.0]$), and periodic expenditures $E_t = \sum_j E_{j, t}$. |
| **Physical / Scaled Units** | Integer scaled INR currency (Paise or Lakhs scaled by $10^5$). |
| **Constraint Classification** | **Inviolable Hard Constraint.** (Financial law; deficit spending is legally and physically prohibited). |
| **Source Document & Section** | [`docs/PHASE6D_PROJECT_SCHEDULING_FORMULATION.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_PROJECT_SCHEDULING_FORMULATION.md) §4.4, §5.3; [`docs/PHASE6D_CALENDAR_COST_INDEXING_PROOF.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_CALENDAR_COST_INDEXING_PROOF.md) §4.2; [`docs/PHASE6D_OPTIMIZATION_PROOF_EXHAUSTIVE.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_OPTIMIZATION_PROOF_EXHAUSTIVE.md) §2.2 Item 5. |
| **Milestone 1 Service** | Validated post-solve by `CashFlowSolvencyService.evaluate_portfolio_solvency`. |
| **Validation & Test Strategy** | Inject instances with early budget shortfalls (e.g., $B_1 = 50$, $c_1 = 100$, $d_1 = 1$). Prove solver either delays project start to period where $\Phi_{t-1} + B_t \ge 100$ or marks it infeasible if no solvent schedule exists. |

---

### Constraint 2: Total Global Budget Ceiling

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $\sum_{j \in \mathcal{P}} c_j \cdot w_j \le \sum_{t=1}^T B_t = B_{\text{total}}$ |
| **Plain-Language Explanation** | The total capital cost of all selected recovery projects cannot exceed the cumulative budget released across the entire planning horizon. |
| **Relevant Input Fields** | `total_cost: float` ($c_j$), `budget_envelopes: List[float]` ($B_t$). |
| **Physical / Scaled Units** | Integer scaled INR currency. |
| **Constraint Classification** | **Inviolable Hard Constraint.** (Derives naturally from summing Constraint 1 when $\eta = 1.0$). |
| **Source Document & Section** | `PHASE6D_CALENDAR_COST_INDEXING_PROOF.md` §4.2 Item 3; `PHASE6D_PROJECT_SCHEDULING_FORMULATION.md` §4.4. |
| **Milestone 1 Service** | `CashFlowSolvencyService`. |
| **Validation & Test Strategy** | Test scenario where $\sum c_j > B_{\text{total}}$. Prove solver selects a subset whose sum $\le B_{\text{total}}$, maximizing MCPI. |

---

### Constraint 3: Project Selection and Scheduling Consistency (Execution Atomicity)

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $\sum_{t=E_j}^{T - d_j + 1} x_{j, t} = w_j \le 1, \quad \forall j \in \mathcal{P}, \quad w_j \in \{0, 1\}, \quad x_{j, t} \in \{0, 1\}$ |
| **Plain-Language Explanation** | A candidate project is executed at most once. If selected ($w_j = 1$), it must be assigned exactly one calendar start period $t$. If rejected ($w_j = 0$), it cannot start in any period ($x_{j, t} = 0 \; \forall t$). |
| **Relevant Input Fields** | `earliest_start_period` ($E_j$), `duration_periods` ($d_j$), `planning_horizon` ($T$). |
| **Physical / Scaled Units** | Dimensionless boolean indicators. |
| **Constraint Classification** | **Inviolable Hard Constraint.** (Physical law of project construction; no fractional or duplicate projects). |
| **Source Document & Section** | `PHASE6D_PROJECT_SCHEDULING_FORMULATION.md` §4.1; `PHASE6D_PRECEDENCE_CONSTRAINT_PROOF.md` §2. |
| **Milestone 1 Service** | `ProjectDependencyService`. |
| **Validation & Test Strategy** | Verify that no solution contains $\sum_t x_{j, t} > 1$ or $x_{j, t} = 1$ when $w_j = 0$. |

---

### Constraint 4: Structural Dependency Selection Co-Requisite (DEF-6D-04 Remediation)

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $w_j \le w_i, \quad \forall (i, j) \in \mathcal{E}_{\text{mandatory}}$ |
| **Plain-Language Explanation** | If successor project $j$ is selected for execution ($w_j = 1$), its prerequisite predecessor project $i$ must also be selected ($w_i = 1$). A successor project can never be constructed without its prerequisite. |
| **Relevant Input Fields** | `dependencies: List[DependencyEdge]`. |
| **Physical / Scaled Units** | Dimensionless boolean indicators. |
| **Constraint Classification** | **Inviolable Hard Constraint.** (Approved structural correction under DEF-6D-04). |
| **Source Document & Section** | [`docs/PHASE6D_PRECEDENCE_CONSTRAINT_PROOF.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_PRECEDENCE_CONSTRAINT_PROOF.md) §1, §2.1 Invariant 1; [`docs/PHASE6D_OPTIMIZATION_PROOF_EXHAUSTIVE.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_OPTIMIZATION_PROOF_EXHAUSTIVE.md) §2.2 Item 1. |
| **Milestone 1 Service** | `ProjectDependencyService.analyze_dependencies`. |
| **Validation & Test Strategy** | Create an edge $P_1 \to P_2$ where $P_2$ has high priority ($95$) and $P_1$ has low priority ($10$). Restrict budget so only one project can be funded. Prove solver cannot select $P_2$ without $P_1$. |

---

### Constraint 5: Discrete Timing Precedence with Completion-to-Start Lag

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $S_j \ge S_i + d_i + L_{ij}, \quad \text{enforced if } w_j = 1, \quad \forall (i, j) \in \mathcal{E}$ |
| **Plain-Language Explanation** | Successor project $j$ cannot begin construction until predecessor project $i$ has completely finished its execution ($S_i + d_i - 1$) plus an integer completion-to-start curing or inspection lag ($L_{ij}$). |
| **Relevant Input Fields** | `start_var[j]`, `start_var[i]`, `duration_periods` ($d_i$), `lag_periods` ($L_{ij} = \lceil L_{\text{days}} / \Delta t \rceil$). |
| **Physical / Scaled Units** | Integer discrete time periods. |
| **Constraint Classification** | **Inviolable Hard Constraint.** (Physical non-preemptive scheduling law). |
| **Source Document & Section** | `PHASE6D_PRECEDENCE_CONSTRAINT_PROOF.md` §2.1 Invariant 2, §3.2; `PHASE6D_OPTIMIZATION_PROOF_EXHAUSTIVE.md` §2.2 Item 3. |
| **Milestone 1 Service** | `ProjectDependencyService`, with lag conversion via `CalendarCostService.convert_lag_days_to_periods`. |
| **Validation & Test Strategy** | Test $P_1$ ($d_1 = 2$) $\to$ $P_2$ ($d_2 = 1$) with lag $L_{12} = 1$. If $P_1$ starts at $t = 1$, prove $P_2$ cannot start earlier than $t = 1 + 2 + 1 = 4$. |

---

### Constraint 6: Calendar Cost Expenditure Convolution

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $E_{j, t} = \sum_{s = \max(E_j, t - d_j + 1)}^t \gamma_{j, (t - s + 1)} \cdot x_{j, s}, \quad \forall j \in \mathcal{P}, \forall t \in \mathcal{T}$ |
| **Plain-Language Explanation** | When a project starts at period $s$, its capital expenditure in global calendar period $t \ge s$ corresponds exactly to its relative execution age expenditure $\gamma_{j, (t - s + 1)}$. Summing over active start windows maps project cash flow into the calendar. |
| **Relevant Input Fields** | `custom_gamma: List[float]` or `curve_type`, evaluated via `CalendarCostService.generate_gamma_profile`. |
| **Physical / Scaled Units** | Integer scaled INR currency. |
| **Constraint Classification** | **Inviolable Mathematical Definition / Hard Conservation Constraint.** |
| **Source Document & Section** | [`docs/PHASE6D_CALENDAR_COST_INDEXING_PROOF.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_CALENDAR_COST_INDEXING_PROOF.md) §2, §2.1, §3.2, §4.1. |
| **Milestone 1 Service** | `CalendarCostService.calculate_project_schedule`. |
| **Validation & Test Strategy** | Verify that for any scheduled project, $\sum_{t=1}^T E_{j, t} = c_j \cdot w_j$ to the exact scaled integer. |

---

### Constraint 7: Non-Preemptive Execution & Physical Duration

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $C_j^{\text{end}} = S_j + d_j - 1, \quad \forall j \in \mathcal{P} \text{ where } w_j = 1$ |
| **Plain-Language Explanation** | Once construction breaks on a project, work proceeds continuously without preemption for exactly $d_j$ periods. Concrete pouring and road paving cannot be paused indefinitely midway. |
| **Relevant Input Fields** | `duration_periods` ($d_j \ge 1$). |
| **Physical / Scaled Units** | Discrete integer periods. |
| **Constraint Classification** | **Inviolable Hard Constraint.** |
| **Source Document & Section** | `PHASE6D_PROJECT_SCHEDULING_FORMULATION.md` §2.2, §4.2; `PHASE6D_INFEASIBILITY_HARD_CONSTRAINT_AUDIT.md` §2 Item 2. |
| **Milestone 1 Service** | Modeled via CP-SAT interval variables `NewOptionalIntervalVar`. |
| **Validation & Test Strategy** | Check that interval size is constant $d_j$ for all active projects. |

---

### Constraint 8: Planning Horizon Deadline Boundaries

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $S_j \ge E_j \quad \text{and} \quad S_j + d_j - 1 \le T, \quad \forall j \in \mathcal{P} \text{ where } w_j = 1$ |
| **Plain-Language Explanation** | A project cannot commence before its earliest allowable release date ($E_j$, e.g., procurement lead time), and must fully complete on or before the final planning period $T$. |
| **Relevant Input Fields** | `earliest_start_period` ($E_j$), `planning_horizon` ($T$). |
| **Physical / Scaled Units** | Integer periods. |
| **Constraint Classification** | **Inviolable Hard Constraint.** |
| **Source Document & Section** | `PHASE6D_PROJECT_SCHEDULING_FORMULATION.md` §2.2, §2.3. |
| **Milestone 1 Service** | `CalendarCostService`. |
| **Validation & Test Strategy** | Attempt to schedule a project where $E_j + d_j - 1 > T$. Prove solver forces $w_j = 0$. |

---

### Constraint 9: District Policy Equity Floors with Dynamic Capacity Bounds

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $\sum_{j \in \mathcal{P}_d} c_j \cdot w_j \ge \min\left(\underline{\theta}_d \cdot B, \; \sum_{j \in \mathcal{P}_d} c_j\right), \quad \forall d \in \mathcal{D}$ |
| **Plain-Language Explanation** | Each administrative district $d$ is allocated at least its policy budget quota ($\underline{\theta}_d B$), unless its total submitted project volume is less than the quota, in which case the requirement clamps to 100% of submitted volume. |
| **Relevant Input Fields** | `district_equity_floors: Dict[str, float]`, `total_cost` ($c_j$), `district_id`. |
| **Physical / Scaled Units** | Integer scaled INR currency. |
| **Constraint Classification** | **Governance Hard Constraint.** (Internal policy constraint; never relaxed automatically). |
| **Source Document & Section** | [`docs/PHASE6D_OPTIMIZATION_PROOF_EXHAUSTIVE.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_OPTIMIZATION_PROOF_EXHAUSTIVE.md) §1.1, §2.2 Item 6, §3; [`docs/PHASE6D_EQUITY_UNKNOWN_BASELINE_CORRECTION.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_EQUITY_UNKNOWN_BASELINE_CORRECTION.md) §4. |
| **Milestone 1 Service** | `EquityCalculationService.calculate_district_target`. |
| **Validation & Test Strategy** | Reproduce Configuration 1–8 from `PHASE6D_OPTIMIZATION_PROOF_EXHAUSTIVE.md`. Prove configurations violating district floors are declared infeasible. |

---

### Constraint 10: Uncontacted Hazard Blackout Reserve Protection

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $\sum_{j \in \mathcal{P}} c_j \cdot w_j \le B - \sum_{d \in \mathcal{D}_{\text{blackout}}} \underline{\theta}_d \cdot B$ |
| **Plain-Language Explanation** | When a district has zero communication or reports ($|J_d| = 0$), 100% of its policy quota is locked in central reserve. The solver is mathematically prohibited from allocating this capital to connected urban projects. |
| **Relevant Input Fields** | `blackout_districts: List[str]`, `district_equity_floors: Dict[str, float]`. |
| **Physical / Scaled Units** | Integer scaled INR currency. |
| **Constraint Classification** | **Governance Hard Constraint & Policy Allocation Rule.** |
| **Source Document & Section** | `PHASE6D_EQUITY_UNKNOWN_BASELINE_CORRECTION.md` §4.2; `PHASE6D_EQUITY_RESERVE_ACCOUNTING_FINAL.md` §2.2 State 2. |
| **Milestone 1 Service** | `EquityCalculationService.calculate_uncontacted_blackout_reserve`. |
| **Validation & Test Strategy** | Define a 2-district portfolio with $B = 1000$. District A (blackout) has $\underline{\theta}_A = 0.30$. Prove District B projects can spend at most $700$. |

---

### Constraint 11: Mandatory Life-Safety Selection Mandate (RSK-M2-01 Approved Option A)

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $w_j = 1 \quad \text{and} \quad S_j \le T_{\text{safety\_max}}, \quad \forall j \in \mathcal{J}_{\text{mandatory}} \text{ (where } S_L \ge 0.85\text{)}$ |
| **Plain-Language Explanation** | Every project formally classified as mandatory life-safety (`TIER_1_MANDATORY`) must be selected and scheduled in early periods. If available budget, cash solvency, resource capacities, dependencies, or planning horizons cannot accommodate all mandatory projects, the solver must return `INFEASIBLE`. Constraints cannot be silently softened. |
| **Relevant Input Fields** | `is_tier1_mandatory: bool` (derived from `LifeSafetyTriageService`). |
| **Physical / Scaled Units** | Dimensionless boolean selection indicator ($w_j = 1$). |
| **Constraint Classification** | **Inviolable Executive Mandate (Hard Constraint).** |
| **Source Document & Section** | `PHASE6D_B_MILESTONE_2A_PROJECT_OWNER_DECISIONS.md` §1 Decision 1; `PHASE6D_LIFE_SAFETY_SCALE_RECONCILIATION.md` §1.2; `PHASE6D_INFEASIBILITY_HARD_CONSTRAINT_AUDIT.md` §2 Item 6. |
| **Milestone 1 Service** | `LifeSafetyTriageService`, `MCPIPrioritizationService`. |
| **Validation & Test Strategy** | Provide a portfolio where mandatory projects exceed available budget ($B$). Prove solver returns `INFEASIBLE` and produces structured root-cause diagnostics isolating the life-safety budget deficit. |

---

### Constraint 12: Renewable Workforce and Machinery Capacity Limits

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $\sum_{j \in \mathcal{P}} u_{j, r} \cdot y_{j, t} \le R_{r, t}, \quad \forall r \in \mathcal{R}, \forall t \in \mathcal{T}$ |
| **Plain-Language Explanation** | During any period $t$, total demand for specialized engineering crews or heavy equipment across all concurrently active projects cannot exceed available supply. |
| **Relevant Input Fields** | `resource_demands: Dict[str, int]`, `resource_capacities: Dict[str, List[int]]`. |
| **Physical / Scaled Units** | Integer resource units (crews, machines). |
| **Constraint Classification** | **Operational Hard Constraint.** |
| **Source Document & Section** | `PHASE6D_PROJECT_SCHEDULING_FORMULATION.md` §4.5. |
| **Milestone 1 Service** | Implemented via CP-SAT `AddCumulative` over `interval_var`. |
| **Validation & Test Strategy** | Provide two projects each requiring 5 excavators where total capacity is 6. Prove solver staggers them non-overlappingly. |

---

### Constraint 13: Indivisible Funding-Policy Assignment & Ring-Fencing (RSK-M2-05 & RSK-M2-06)

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $\sum_{f \in \mathcal{F}_j^{\text{eligible}}} z_{j, f} = w_j \quad \forall j \in \mathcal{P}$<br>$z_{j, f} = 0 \quad \forall f \notin \mathcal{F}_j^{\text{eligible}}$<br>$\sum_{j \in \mathcal{P}} c_j \cdot z_{j, f} \le F_f^{\max} \quad \forall f \in \mathcal{F}$<br>$\Phi_{f, t} = \eta \Phi_{f, t-1} + B_{f, t} - \sum_{j \in \mathcal{P}} c_j z_{j, f} x_{j, \dots} \ge 0, \quad \forall f \in \mathcal{F}, \forall t \in \mathcal{T}$ |
| **Plain-Language Explanation** | In accordance with approved decision RSK-M2-06, each selected project must be assigned wholly to exactly one eligible funding source. Splitting project cost across multiple funds is prohibited. Total cost assigned to fund $f$ cannot exceed $F_f^{\max}$. When multi-fund mode is enabled, each fund also maintains periodic solvency. |
| **Relevant Input Fields** | Per-fund budget caps $F_f^{\max}$, tranche allocations $B_{f, t}$, eligible fund lists $\mathcal{F}_j^{\text{eligible}}$, binary assignment $z_{j, f}$. |
| **Physical / Scaled Units** | Integer scaled currency (CCU). |
| **Constraint Classification** | **Internal Funding-Policy Constraint (Indivisible Assignment Mandate).** |
| **Source Document & Section** | `PHASE6D_B_MILESTONE_2A_PROJECT_OWNER_DECISIONS.md` §1 Decisions 3 & 4 (RSK-M2-05 & RSK-M2-06). |
| **Milestone 1 Service** | `CashFlowSolvencyService.evaluate_multi_fund_solvency`. |
| **Validation & Test Strategy** | Provide three projects of costs 40, 40, 20 and two funds of capacity 50 each. Verify solver correctly detects infeasibility under indivisible assignment (counterexample to Hall's condition). |

---

### Constraint 14: Unallocated Reserve & Contingency Pool Floor

| Attribute | Specification Detail |
| :--- | :--- |
| **Mathematical Equation** | $\Phi_T \ge R_{\text{contingency}} \quad \text{or} \quad \sum_{j \in \mathcal{P}} c_j \cdot w_j \le B - R_{\text{contingency}}$ |
| **Plain-Language Explanation** | A minimum central unallocated liquidity buffer is preserved across the horizon to protect against unexpected price inflation, secondary disaster waves, or monsoon delays. |
| **Relevant Input Fields** | `contingency_reserve_ratio: float` ($\rho_{\text{cont}} \in [0.0, 0.30]$). |
| **Physical / Scaled Units** | Integer scaled currency. |
| **Constraint Classification** | **Administrative Policy Lever.** |
| **Source Document & Section** | `PHASE6D_OPTIMIZATION_PROOF_EXHAUSTIVE.md` §1.1 (Central Contingency Pool $20\%$). |
| **Milestone 1 Service** | `EquityCalculationService`. |
| **Validation & Test Strategy** | Verify that solver never commits more than $(1 - \rho_{\text{cont}}) B$. |

---

## 3. Summary of Constraint Taxonomy & Solver Inviolability

| Tier | Category | Enforced Constraints | Solver Inviolability Policy |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **Physical & Mathematical Laws** | Constraints 1, 2, 3, 4, 5, 6, 7, 8 | **Absolute Inviolable Hard Constraints.** Zero automatic or human relaxation permitted. |
| **Tier 2** | **Executive Mandates & Policy Invariants** | Constraints 9, 10, 11, 12, 13, 14 | **Governance Hard Constraints.** Inviolable by solver. Cannot be silently relaxed. Alterable only via explicit ministerial override launching a new scenario run. |
