# DIRS Phase 6D-B — Milestone 2A: Risk, Assumption and Governance Register

**Document ID:** `DIRS-PHASE6D-B-M2A-RISK-01`  
**Classification:** OPERATIONS RESEARCH RISK REGISTER & GOVERNANCE AUDIT  
**Author:** Principal Software Architect, Operations Research Specialist & QA Lead  
**Date:** November 17, 2026  
**Status:** COMPLETE (MILESTONE 2A DESIGN SPECIFICATION)  
**Database Policy:** ZERO MIGRATIONS — Schema strictly frozen at `phase6b_recovery_foundation`  

---

## 1. Purpose & Scope

This document establishes the comprehensive risk, assumption, reproducibility, and interface governance register for the **DIRS Phase 6D-B Recovery Optimization Engine**. 

It details:
1. Formal solver status semantics and handling guarantees (prohibiting false proofs of infeasibility).
2. Edge-case and error taxonomy across all failure modes.
3. Deterministic execution and reproducibility policies.
4. Milestone 1 contract integration mapping and compatibility review.
5. Critical risks, technical assumptions, and unresolved policy questions requiring explicit project-owner decision before Milestone 2B coding begins.

---

## 2. Solver Status Handling & Invariant Guarantees

The CP-SAT engine maps solver outcomes directly to five mutually exclusive states.

| CP-SAT Status Code | Engine Status | Strict Semantic Definition | Invariant Governance Rule |
| :--- | :--- | :--- | :--- |
| `cp_model.OPTIMAL` | `OPTIMAL` | Global optimality mathematically proven. Objective value equals best dual bound ($Z = Z^*$). | May only be reported when CP-SAT confirms complete branch-and-bound convergence. **Never report `FEASIBLE` as `OPTIMAL`.** |
| `cp_model.FEASIBLE` | `FEASIBLE` | A valid schedule satisfying 100% of hard constraints was found, but optimality gap $> 0$ when time limit expired. | Reports best integer solution with explicit optimality gap: $\text{Gap} = \frac{\|Z_{\text{best}} - \text{Bound}\|}{Z_{\text{best}}}$. |
| `cp_model.INFEASIBLE` | `INFEASIBLE` | Mathematically proven that **no solution exists** satisfying all hard constraints simultaneously. | Triggers `InfeasibilityAdvisor` conflict analysis. Halts without writing partial schedule. **Never report `UNKNOWN` or Timeout as `INFEASIBLE`.** |
| `cp_model.MODEL_INVALID` | `MODEL_INVALID` | The model formulation contained malformed expressions, illegal variable bounds, or integer overflow. | Fails closed with structured validation error. Halts immediately. |
| `cp_model.UNKNOWN` | `TIMEOUT_UNKNOWN` | Solver terminated (due to time limit or memory exhaustion) before finding a feasible solution or proving infeasibility. | **A timeout must NEVER be represented as proof of infeasibility.** Explicitly reports: *"Search exhausted time limit without proving feasibility or infeasibility; problem may or may not admit a feasible solution."* |

---

## 3. Edge-Case & Exceptional Input Taxonomy

| Edge-Case Condition | Trigger Condition | Engine Behavior | Output Schema & Governance Action |
| :--- | :--- | :--- | :--- |
| **Empty Candidate Portfolio** | `candidates == []` | Graceful zero-operation exit | Status: `OPTIMAL`. Objective: $0.0$. Selected projects: $0$. Empty schedule list. |
| **No Eligible Projects (Horizon Exceeded)** | $\forall j: E_j + d_j - 1 > T$ | Pre-solve detection | Status: `OPTIMAL`. Objective: $0.0$. Selected projects: $0$. Explanatory notice in diagnostics. |
| **Precedence Dependency Cycle** | Directed cycle in DAG (e.g. $P_1 \to P_2 \to P_1$) | Pre-solve Kahn's algorithm fails | Pre-solve raises `CyclicDependencyError` with exact cycle path. CP-SAT model is **never constructed**. |
| **Infeasible Mandatory Safety Mandate** | $\mathcal{P}_{\text{Tier 1}}$ capital demand $> B_{\text{total}}$ | Budget insufficient for human life-safety | Pre-solve or CP-SAT proves `INFEASIBLE`. Infeasibility Advisor isolates life-safety budget deficit. Zero silent relaxation. |
| **Infeasible District Equity Floor** | Quota $\underline{\theta}_d B$ exceeds total submitted district spend | Prevented by dynamic capacity bound | Bound automatically clamps to $\min(\underline{\theta}_d B, \sum_{j \in J_d} c_j)$, guaranteeing no artificial infeasibility when absorption is low. |
| **Impossible Renewable Resource Demand** | $\exists r, t: \min_{j \in \text{Tier 1}} u_{j, r} > R_{r, t}$ | Peak machine/crew demand exceeds supply | CP-SAT returns `INFEASIBLE`. Advisor highlights resource $r$ bottleneck. Zero silent relaxation. |

---

## 4. Reproducibility & Deterministic Execution Policy

Post-disaster public audit standards require that running the optimization engine twice on identical inputs on the same platform must yield **identical outputs to the exact rupee and calendar period**.

### 4.1 Four Distinct Reproducibility Dimensions
To prevent scientific ambiguity, the platform explicitly separates:
1. **Input Identity:** Captured via cryptographic SHA-256 digest of the canonical JSON request payload. Proves that input data is identical byte-for-byte. (Does not prove identical solver outcome across different platforms).
2. **Configuration Reproducibility:** Exact logging of OR-Tools version (e.g. `v9.15.6755`), solver seed (`random_seed = 42`), worker count (`num_search_workers = 1`), and time limit.
3. **Deterministic Execution (Same-Platform):** Single-threaded search (`num_search_workers = 1`) on identical hardware, OS, and solver version guarantees identical search tree exploration and bitwise-identical integer solutions.
4. **Cross-Platform Reproducibility Disclaimer:** The platform explicitly disclaims bitwise-identical reproducibility across differing CPU architectures (x86_64 vs. ARM64) or across operating systems (Windows vs. Linux), as underlying compiler optimizations and standard math libraries may alter search order.

### 4.2 Reproducibility Configuration Matrix

| Parameter | Recommended Value | Operational Rationale | Non-Deterministic Trap to Avoid |
| :--- | :---: | :--- | :--- |
| **Search Worker Count (`num_search_workers`)** | **`1`** (for certified determinism) or `8` (for fast exploratory mode) | Single worker guarantees deterministic branch-and-bound search. Multi-worker race conditions alter intermediate heuristic trajectories. | Multi-worker mode is non-certified. Never promise bitwise determinism when `num_search_workers > 1`. |
| **Random Seed (`random_seed`)** | **`42`** (Configurable) | Seeds CP-SAT randomized variable selection and restart heuristics. | Random seed must be recorded in output metadata. |
| **Time Limit (`max_time_in_seconds`)** | **`60.0`** (Configurable) | Prevents runaway solver execution on large combinatorial instances. | Wall-clock runtime vs deterministic ticks must be logged. |
| **Input Fingerprinting** | **SHA-256 Digest** | Computes cryptographic digest of canonical JSON request. | Identifies input data; does not prove solver outcome. |
| **Solver Version Tracking** | **`ortools.sat.python.cp_model` version** | Records runtime version (e.g., `9.15.6755`). | Ensures mathematical reproducibility across environment upgrades. |
| **Random Seed (`random_seed`)** | **`42`** (Configurable) | Seeds CP-SAT randomized variable selection and restart heuristics. | Random seed must be recorded in output metadata. |
| **Time Limit (`max_time_in_seconds`)** | **`60.0`** (Configurable) | Prevents runaway solver execution on large combinatorial instances. | Search must record wall-clock runtime vs deterministic ticks. |
| **Input Fingerprinting** | **SHA-256 Digest** | Computes cryptographic SHA-256 digest of canonical canonicalized JSON input request. | Guarantees tamper-evident traceability between input data and optimization results. |
| **Solver Version Tracking** | **`ortools.sat.python.cp_model` version** | Records runtime version (e.g., `9.15.6755`). | Ensures mathematical reproducibility across environment upgrades. |

---

## 5. Milestone 1 Public Contract Integration

The optimizer imports and consumes Milestone 1 contracts strictly through authorized public interfaces. Zero internal mathematical formulas are duplicated.

| Optimizer Component | Milestone 1 Service Module | Exported Contracts / Classes Consumed | Function / Role in Optimizer |
| :--- | :--- | :--- | :--- |
| **Pre-Solve Graph Analysis** | `app.recovery.services.project_dependency_service` | `ProjectDependencyService`, `DependencyEdge`, `CyclicDependencyError` | Validates DAG acyclicity via Kahn's algorithm; evaluates topological order and transitive cascade reachability. |
| **Lag & Profile Timing** | `app.recovery.services.calendar_cost_service` | `CalendarCostService`, `DisbursementCurveType`, `PeriodBoundary` | Converts day lags to discrete period lags ($\lceil L / \Delta t \rceil$); generates normalized expenditure curves $\boldsymbol{\gamma}_j$. |
| **Objective Utility Scores** | `app.recovery.services.mcpi_prioritization_service` | `MCPIPrioritizationService`, `MCPIInput`, `MCPIResult` | Evaluates verified MCPI scores $\Pi_j$; establishes Stage 1 non-compensatory safety flags (`is_tier1_mandatory`). |
| **Life-Safety Triage** | `app.recovery.services.life_safety_triage_service` | `LifeSafetyTriageService`, `LifeSafetyInput`, `LifeSafetyResult` | Confirms triage index $S_L \ge 0.85$ for emergency facility mandates. |
| **District Equity Quotas** | `app.recovery.services.equity_calculation_service` | `EquityCalculationService`, `DistrictEquityTarget`, `PortfolioEquityAudit` | Evaluates dynamic district absorption bounds $\min(\underline{\theta}_d B, \sum c_j)$; audits post-solve equity distribution. |
| **Solvency Verification** | `app.recovery.services.cash_flow_solvency_service` | `CashFlowSolvencyService`, `FundTranchePlan`, `PeriodSolvencyStatus` | Performs post-solve verification of multi-period cash carry-forward recurrence ($\Phi_t \ge 0$). |

### Interface Compatibility Audit:
- **Zero Schema Incompatibilities:** All input types (`float`, `int`, `str`, `List`, `Dict`) align with Milestone 1 dataclasses.
- **No Circular Imports:** `app.recovery.optimization` imports `app.recovery.services`. `app.recovery.services` has zero imports from `app.recovery.optimization`.
- **Purity Preserved:** Optimization models operate strictly on transient dataclasses; no database models (`RecoveryProject`, etc.) are imported.

---

## 6. Risk Register & Ratified Decision Status

The following table catalogs critical risks, engineering assumptions, and governance questions, updated with the project owner's binding decisions.

| Risk / Assumption ID | Category | Description | Ratified Policy & Technical Treatment | Project-Owner Decision Status |
| :--- | :--- | :--- | :--- | :---: |
| **RSK-M2-01** | **Governance** | **Mandatory Life-Safety Enforcement Method:** Hard constraint ($w_j = 1 \implies \text{Infeasible if budget low}$) vs. Sequential Lexicographic Optimization. | **Option A Ratified:** Hard Constraint ($w_j = 1$). If budgets, resources, dependencies, or horizons conflict, solver returns `INFEASIBLE` with structured forensic diagnostics. Zero silent relaxation. | **APPROVED & RATIFIED** |
| **RSK-M2-02** | **Numerical** | **Early Start Acceleration Bonus:** Time-discounted bonus $\sum \omega_{j, t} x_{j, t}$ could theoretically conflict with pure MCPI maximization if improperly scaled. | Mathematically bound total acceleration bonus across all projects to $< 1$ basis point of MCPI, ensuring it acts strictly as an internal schedule tie-breaker with zero effect on selection $w_j$. | **RESOLVED (Mathematically Proven)** |
| **RSK-M2-03** | **Performance** | **Multi-Worker Determinism vs. Speed:** Multi-threaded search (`num_search_workers = 8`) does not guarantee bitwise determinism across differing hardware architectures. | **Option A Ratified:** Default `num_search_workers = 1`, fixed random seed, time limit, parameter logging, and canonical SHA-256 fingerprint. Cross-platform bitwise reproducibility explicitly disclaimed. Multi-worker optional as non-certified mode. | **APPROVED & RATIFIED** |
| **RSK-M2-04** | **Policy** | **District Equity Floor Hardness:** If a district submits high-cost projects that violate budget solvency, should the district equity constraint force `INFEASIBLE`? | Dynamic bound clamps to $\min(\underline{\theta}_d B, \sum_{j \in J_d} c_j)$. If even the clamped demand is solvently unachievable, returns `INFEASIBLE` with diagnostic root-cause reporting. Zero silent relaxation. | **RESOLVED (Inviolable Hard Constraint)** |
| **RSK-M2-05** | **Financial** | **Multi-Fund Tracking Scope:** Global multi-period cash solvency vs. per-fund ring-fencing constraints ($f \in \{\text{SDRF}, \text{NDRF}, \dots\}$). | **Option A Ratified:** Global multi-period solvency is default. Per-fund constraints activated only when explicit funding-source rules are provided. Classified as funding-policy constraints; zero statutory claims without legal citations; zero real-world banking claims. | **APPROVED & RATIFIED** |
| **RSK-M2-06** | **Financial** | **Funding Allocation Divisibility:** Can a recovery project's cost be split across multiple funding sources (Model A: Divisible) or must each project be funded wholly by exactly one source (Model B: Indivisible)? | **Model B (Indivisible Project Funding) Ratified by Project Owner:** Every project must be assigned wholly to exactly one eligible fund ($z_{j, f} \in \{0, 1\}$, $\sum_f z_{j, f} = w_j$). Splitting cost across funds is prohibited. Hall's Marriage Condition is recognized strictly as a necessary screening test, not a sufficient feasibility test. Complete feasibility is determined via integer assignment constraints in CP-SAT. | **APPROVED & RATIFIED** |
