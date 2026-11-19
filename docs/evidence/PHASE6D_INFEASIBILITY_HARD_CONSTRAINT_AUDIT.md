# DIRS Phase 6D-A — DEF-6D-06: Inviolable Constraints & Infeasibility Advisor Architecture
## Redesign of Diagnostics, Prohibition of Silent Relaxation, and Attributed Decision Governance

**Document ID:** `DIRS-PHASE6D-DOC-19`  
**Classification:** OPERATIONS RESEARCH ARCHITECTURE & AUDIT  
**Lead Authors:** Principal Optimization Systems Architect & Forensic Software Auditor  
**Date:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Executive Summary & Defect Remediation (DEF-6D-06)

In preliminary optimization solver designs, an "automated relaxation advisor" was proposed that would automatically soften constraints when an optimization run returned `INFEASIBLE`.

**Audit Finding (DEF-6D-06):**
Allowing an automated solver or algorithmic heuristic to silently relax constraints is extremely dangerous in disaster management:
1. If the solver silently relaxes dependency edges, it generates schedules where roofs are cast before foundations cure.
2. If it silently lowers budget caps, it commits public funds into deficit spending.
3. If it silently lowers safety thresholds ($\tau_L$), it revokes life-safety protections without executive knowledge.

**Remediation Mandate:**
- **Zero Silent Relaxation:** The solver and Infeasibility Advisor are strictly forbidden from relaxing any constraint automatically.
- **Inviolable Constraints Demarcation:** Mandatory dependencies, physical durations, resource conservation, budget solvency, and statutory safety mandates are absolute hard constraints.
- **Diagnostic Role Only:** When CP-SAT returns `INFEASIBLE`, the Infeasibility Advisor operates strictly as a forensic diagnostic reporting engine.
- **Attributed Government Decision Required:** Any alteration to planning horizons, budget allocations, or safety policies requires an explicit, cryptographically authenticated ministerial decision and launches an entirely **new optimization run**.

---

## 2. Inviolable Hard Constraints vs. Relaxable Policy Levers

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DIRS RECOVERY OPTIMIZATION CONSTRAINT TAXONOMY                  │
└────────────────────────────────────────────────────────────────────────────────────────┘

  TIER 1: INVIOLABLE HARD CONSTRAINTS (SOLVER & ADVISOR CAN NEVER RELAX)
  ──────────────────────────────────────────────────────────────────────
  1. Mandatory Project Precedence:
     w_j ≤ w_i   and   S_j ≥ S_i + d_i + L_ij   ∀ (i, j) ∈ E_mandatory
     (Physical laws of construction; no successor without predecessor).
  2. Non-Preemptive Execution / Atomicity:
     ∑_t x_{j, t} = w_j,   y_{j, t} = ∑_{τ=t-d_j+1}^t x_{j, τ}
     (A continuous concrete pour or bridge span cannot be paused midway).
  3. Single Start Period:
     ∑_{t=1}^T x_{j, t} ≤ 1   ∀ j ∈ P
  4. Fiscal Cash-Flow Solvency:
     Φ_t = η_t * Φ_{t-1} + B_t - E_t ≥ 0   ∀ t
     (DIRS cannot spend money it does not possess; zero deficit spending).
  5. Statutory Fund Ring-Fencing:
     Φ_{f, t} ≥ 0   ∀ f ∈ Funds, ∀ t
     (Multilateral aid cannot be illegally diverted to unauthorized accounts).
  6. Government-Approved Life-Safety Mandate:
     w_j = 1,  S_j ≤ T_safety_max   ∀ j ∈ P_Tier1
     (Executive mandate protecting human life cannot be overridden by an algorithm).

  TIER 2: DISCRETIONARY POLICY LEVERS (ALTERABLE ONLY BY ATTRIBUTED HUMAN OVERRIDE)
  ────────────────────────────────────────────────────────────────────────────────
  1. Planning Horizon Length: T can be extended (e.g., T = 8 periods → T = 12 periods).
  2. Supplementary Budget Tranches: Additional state disaster funds B_supp authorized.
  3. District Equity Quota (θ_d): Floor adjusted if district has capital absorption deficit.
  4. Non-Structural Material Transfers: Interstate mutual-aid logistics agreements.
```

---

## 3. Redesigned Infeasibility Diagnostic Engine

When Google OR-Tools CP-SAT terminates with `model.Solve(model) == cp_model.INFEASIBLE`:
1. The solver halts and does not write any partial or invalid schedule to the database.
2. The Infeasibility Advisor runs a deterministic conflict isolation pipeline:
   - **Step 1 (Precedence Cycle Scan):** Executes Kahn's algorithm on directed graph $G = (\mathcal{V}, \mathcal{E})$. If cycles exist ($|\mathcal{V}_{\text{sorted}}| < |\mathcal{V}|$), reports the exact cycle path (e.g., $P_1 \to P_2 \to P_3 \to P_1$).
   - **Step 2 (Horizon Feasibility Check):** Computes earliest completion of all critical path chains. If $\min \text{Makespan}(G) > T$, reports deadline violation.
   - **Step 3 (Early Cash-Flow Bottleneck Check):** Evaluates if $\sum_{j \in \mathcal{P}_{\text{Tier 1}}} \gamma_{j, 1} > B_1$.
   - **Step 4 (Resource Capacity Conflict):** Identifies specific material/heavy machinery categories where mandatory demand exceeds total supply.
3. The Advisor generates a structured, human-readable forensic report.

### 3.1 Diagnostic Report Schema
```json
{
  "solver_status": "INFEASIBLE",
  "conflict_category": "EARLY_BUDGET_DEFICIT_TIER_1",
  "root_cause_summary": "Initial period budget B_1 = 300 Lakh INR is insufficient to fund mandatory Tier 1 life-safety mobilization demands (450 Lakh INR required).",
  "conflicting_projects": [
    {"project_code": "REC-HOSP-01", "sector": "HEALTH", "period_1_cost": 250.0, "reason": "Tier 1 Mandatory (Imminent collapse)"},
    {"project_code": "REC-WASH-04", "sector": "WASH", "period_1_cost": 200.0, "reason": "Tier 1 Mandatory (Destroyed water main)"}
  ],
  "resource_shortfalls": [],
  "budget_shortfall": {
    "period_index": 1,
    "available_tranche": 300.0,
    "mandatory_demand": 450.0,
    "net_deficit": 150.0,
    "currency": "LAKH_INR"
  },
  "suggested_non_safety_alternatives": [
    "Option A: Authorize emergency supplementary state relief tranche of 150 Lakh INR in Period 1.",
    "Option B: Stagger non-conflicting mobilization of REC-WASH-04 to Period 2 if temporary water tankers are deployed."
  ],
  "required_human_decision": {
    "action_required": "MINISTERIAL_BUDGET_AMENDMENT",
    "authorized_role": "DISASTER_FINANCE_DIRECTOR",
    "endpoint": "/api/v1/recovery/optimization/schedule/solve"
  }
}
```

---

## 4. Fully Worked Infeasibility Example

### 4.1 Instance Definition
- Candidate Projects:
  - $P_1$ (Trauma Hospital Structural Shoring): Duration $d_1 = 2$, Tier 1 Mandatory ($S_{L, 1} = 0.92$), Period cost $\boldsymbol{\gamma}_1 = [250, 150]$ Lakh INR.
  - $P_2$ (Intake Dam Gate Replacement): Duration $d_2 = 2$, Tier 1 Mandatory ($S_{L, 2} = 0.88$), Period cost $\boldsymbol{\gamma}_2 = [200, 100]$ Lakh INR.
  - $P_3$ (Residential Debris Clearing): Duration $d_3 = 1$, Tier 3 ($S_{L, 3} = 0.40$), Period cost $\boldsymbol{\gamma}_3 = [80]$ Lakh INR.
- Precedence: No dependencies between $P_1$ and $P_2$.
- Budget Tranches:
  - Period 1 ($B_1$): $350$ Lakh INR.
  - Period 2 ($B_2$): $500$ Lakh INR.
- Policy Rule: Both $P_1$ and $P_2$ are Tier 1 Mandatory, requiring start at period $t = 1$.

### 4.2 Infeasibility Proof
1. Since $P_1$ and $P_2$ must both start at $t = 1$:
   $$C_{1, 1} = 250 \text{ Lakh INR}, \quad C_{2, 1} = 200 \text{ Lakh INR}$$
2. Total Period 1 Mandatory Capital Demand:
   $$E_1 = C_{1, 1} + C_{2, 1} = 250 + 200 = 450 \text{ Lakh INR}$$
3. Period 1 Cash Balance:
   $$\Phi_1 = B_1 - E_1 = 350 - 450 = -100 \text{ Lakh INR}$$
4. Inviolable Solvency Constraint:
   $$\Phi_1 \ge 0 \implies -100 \ge 0 \quad (\mathbf{CONTRADICTION — INFEASIBLE})$$

### 4.3 Advisor Action (No Silent Relaxation)
- **What a flawed solver would do:** Silently drop $P_2$ to Tier 2, or silently spend $450$ Lakh creating an unbacked debt of $100$ Lakh.
- **What DIRS Infeasibility Advisor does:**
  - Reports status `INFEASIBLE`.
  - Flags Period 1 cash deficit of $100$ Lakh INR.
  - Proposes human intervention:
    - *Alternative 1:* Minister authorizes an advance transfer of $100$ Lakh from Period 2 into Period 1 ($B_1 \to 450, B_2 \to 400$).
    - *Alternative 2:* Minister issues formal executive order staggering $P_2$ start to Period 2 while deploying interim mobile pumping units.
  - Logs diagnostic incident to audit trail.
  - Waits for human submission of new parameter payload.

---
*End of DIRS Phase 6D-A DEF-6D-06 Remediation Document.*
