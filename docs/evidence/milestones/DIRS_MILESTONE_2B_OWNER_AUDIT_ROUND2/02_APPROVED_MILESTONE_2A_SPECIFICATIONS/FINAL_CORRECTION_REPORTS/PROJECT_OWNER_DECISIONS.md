# DIRS Phase 6D-B — Milestone 2A: Project-Owner Decisions and Governance Record

**Document ID:** `DIRS-PHASE6D-B-M2A-DECISIONS-01`  
**Classification:** PROJECT GOVERNANCE & ARCHITECTURAL DECISION RECORD  
**Author:** Principal Software Architect, Operations Research Specialist & QA Lead  
**Date:** November 17, 2026  
**Status:** APPROVED & RATIFIED BY PROJECT OWNER  
**Database Policy:** ZERO MIGRATIONS — Schema strictly frozen at `phase6b_recovery_foundation`  

---

## 1. Formal Project-Owner Decisions

This document formally records the three binding architectural decisions rendered by the project owner on November 17, 2026, regarding Milestone 2A of DIRS Phase 6D-B.

---

### Decision 1: RSK-M2-01 — Mandatory Life-Safety Priority Enforcement

| Parameter | Ratified Policy |
| :--- | :--- |
| **Approved Option** | **Option A (Inviolable Hard Selection Mandate)** |
| **Mathematical Policy** | Every candidate recovery project formally classified as critical life-safety ($S_L \ge 0.85$, designated `TIER_1_MANDATORY`) must be selected and funded in the schedule: $$w_j = 1 \quad \forall j \in \mathcal{J}_{\text{mandatory}}$$ |
| **Infeasibility Rule** | If hard budget limits, periodic cash-flow solvency, resource capacity, technical dependencies, or planning horizon constraints cannot accommodate 100% of the mandatory projects, the solver must return `INFEASIBLE`. |
| **Prohibition on Silent Relaxation** | The solver, orchestrator, and diagnostics are strictly forbidden from relaxing mandatory life-safety constraints to manufacture a feasible schedule. |
| **Diagnostic Requirement** | The engine must generate structured, forensic root-cause diagnostics isolating the exact resource, budget, or dependency bottleneck causing the life-safety infeasibility. |
| **Input Error Distinction** | Invalid inputs (such as malformed schemas, negative durations, or dependency cycles) must be rejected with validation errors (`MODEL_INVALID` or `CyclicDependencyError`) and must **never** be misclassified as mathematical infeasibility. |

---

### Decision 2: RSK-M2-03 — Reproducibility and Deterministic Execution

| Parameter | Ratified Policy |
| :--- | :--- |
| **Approved Option** | **Option A (Certified Deterministic Single-Worker Default)** |
| **Default Solver Configuration** | - `num_search_workers = 1` (guarantees deterministic search trajectory).<br>- Fixed deterministic solver seed (`random_seed = 42` by default, caller configurable).<br>- Explicit solver time limit (`max_time_in_seconds`, default 60.0s). |
| **Audit Metadata Recording** | Every optimization response must capture:<br>1. Google OR-Tools version (e.g. `9.15.6755`).<br>2. Exact solver search parameters.<br>3. Cryptographic SHA-256 fingerprint of the canonical JSON input request.<br>4. Objective value, best dual bound, optimality gap, solver status, and wall-clock runtime. |
| **Multi-Worker Execution Mode** | Parallel multi-worker search (`num_search_workers > 1`) is supported as an optional, separate, non-certified execution mode for interactive exploration. |
| **Cross-Platform Disclaimer** | The system explicitly disclaims bitwise-identical reproducibility across differing CPU architectures (x86_64 vs. ARM64), different operating systems (Windows vs. Linux), or across different OR-Tools versions, as underlying compiler optimizations and standard math libraries may alter search order. |

---

### Decision 3: RSK-M2-05 — Multi-Fund Constraints and Legal Terminology

| Parameter | Ratified Policy |
| :--- | :--- |
| **Approved Option** | **Option A with Strict Legal Terminology Correction** |
| **Default Solvency Behavior** | Global multi-period cash solvency ($\Phi_t \ge 0$) across the consolidated budget envelope is the primary standard solver mode. |
| **Activation Rule** | Per-fund ring-fencing constraints ($f \in \{\text{SDRF}, \text{NDRF}, \text{MULTILATERAL}, \text{NGO\_CSR}\}$) are activated **only** when explicit funding-source budget limits and project eligibility matrices are provided in the optimization request. |
| **Legal Terminology Correction** | In accordance with project governance, multi-fund constraints must **NOT** be described as "statutory" requirements unless an authoritative legislative act and section are supplied. They are formally classified as **Internal Funding-Policy Allocation Constraints**. |
| **Zero Real-World Banking Claim** | Funding ring-fencing operates strictly as a mathematical optimization constraint over virtual accounts. No real-world banking escrow, bank accounts, or treasury transaction mechanisms are implied. |

---

### Decision 4: RSK-M2-06 — Indivisible Project Funding

| Parameter | Ratified Policy |
| :--- | :--- |
| **Approved Option** | **Model B (Indivisible Project Funding)** |
| **Mathematical Policy** | Every recovery project must be assigned wholly to exactly one eligible funding source. Splitting one project's capital cost across multiple funding sources is strictly prohibited. |
| **Decision Authority** | The explicit project-owner approval is the authoritative mandate. It is not merely inferred from the existing `VARCHAR(100)` database column. |
| **Binary Assignment Formulation** | For every project $j \in \mathcal{J}$ and funding source $f \in \mathcal{F}$:<br>- Binary decision variable: $z_{j, f} \in \{0, 1\}$.<br>- Exactly one eligible fund selected if project is selected: $$\sum_{f \in \text{EligibleFunds}[j]} z_{j, f} = w_j \quad \forall j \in \mathcal{J}$$<br>- Ineligible fund assignments forced to zero: $$z_{j, f} = 0 \quad \forall f \notin \text{EligibleFunds}[j]$$ |
| **Fund Capacity Enforcement** | Total project capital is assigned entirely to its selected funding source: $$\sum_{j \in \mathcal{J}} c_j \cdot z_{j, f} \le F_f^{\max} \quad \forall f \in \mathcal{F}$$ |
| **Screening vs Feasibility** | Hall's Marriage Condition may be used in pre-solve **only as a necessary-condition screening test** (`NECESSARY_CONDITION_VIOLATION`). It must **never** be treated as a sufficient feasibility test for indivisible assignment. Complete funding feasibility must be determined using integer assignment constraints in the future CP-SAT implementation. |
| **Mathematical Implications & Complexity** | Feasibility is equivalent to the **Generalized Assignment Problem (GAP) / Multiple Knapsack Problem (MKP)**, which is strongly NP-complete. |

---

## 2. Inviolable Governance Principles

1. **Frozen Implementations Intact:** All source code and test suites in Phases 1–6C and Milestone 1 remain strictly frozen.
2. **Approved Deviations Maintained:**
   - `DEV-M1-01`: Exact raw float comparisons instead of $10^{-4}$ tolerance grouping.
   - `DEV-M1-02`: Ascending `project_id` as the final non-substantive deterministic arbiter instead of SHA-256.
3. **Zero Database Migrations:** No migrations, no schema modifications, no database writes during optimization runs.
