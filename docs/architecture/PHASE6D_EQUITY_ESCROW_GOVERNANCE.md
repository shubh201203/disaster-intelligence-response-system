# DIRS Phase 6D-A — DEF-6D-11: Equity Escrow Governance & Legal Terminology
## Four-Tier Financial Authority Demarcation, Policy Reserve Mechanics, and Unspent Capital Lifecycle

**Document ID:** `DIRS-PHASE6D-DOC-25`  
**Classification:** PUBLIC FINANCE & FINANCIAL LEGAL GOVERNANCE  
**Lead Authors:** Principal Disaster Public Finance Specialist & Forensic Software Auditor  
**Date:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Executive Summary & Legal Terminology Correction (DEF-6D-11)

In earlier documentation drafts, the district equity floor $\sum_{j \in J_d} c_j w_j \ge \underline{\theta}_d B$ and its associated escrow mechanism were repeatedly described as "statutory funding obligations" or "statutory escrow."

**Audit Finding (DEF-6D-11):**
In public disaster finance, the term **"statutory"** carries precise legal meaning:
- A *statutory obligation* is a binding mandate enacted by parliament or a state legislature (such as the Disaster Management Act of 2005 or Finance Commission SDRF allocation keys).
- The parameter $\underline{\theta}_d$ configured within DIRS is **NOT a statutory legal enactment**.
- Calling an internal, configurable algorithmic constraint "statutory" fabricates legal authority, misrepresents administrative powers, and invents non-existent legal entitlements for specific wards or districts.

**Remediation Mandate:**
1. **Purge "Statutory" Label for Algorithmic Quotas:** Re-label $\underline{\theta}_d$ as an **Internal Policy Equity Target** or **Administrative Allocation Quota**.
2. **Establish Four-Tier Financial Authority Lexicon:** Strictly distinguish statutory allocations, government-approved budget envelopes, internal policy reserves, and contingency buffers.
3. **Formalize Reserve Lifecycle:** Define exact mathematical and administrative procedures when a policy reserve cannot be disbursed due to missing baselines, absent reports, project shortages, or horizon expiration.

---

## 2. Four-Tier Financial Authority Lexicon

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DIRS PUBLIC FINANCE AUTHORITY HIERARCHY                         │
└────────────────────────────────────────────────────────────────────────────────────────┘

  TIER 1: STATUTORY FUNDING ALLOCATIONS (LEGAL ENACTMENTS)
  ────────────────────────────────────────────────────────
  - Authority: National Finance Commission, State Disaster Response Fund (SDRF) statutes.
  - Nature: Legally mandated annual inter-governmental revenue transfers.
  - Status in DIRS: Macro-budget inputs passed into the system as external financial boundaries.

  TIER 2: GOVERNMENT-APPROVED BUDGET ALLOCATIONS (EXECUTIVE ORDERS)
  ────────────────────────────────────────────────────────────────
  - Authority: Formal financial sanction order issued by the State Executive Committee (SEC).
  - Nature: Approved capital ceiling for a specific disaster event: B = ∑ B_t.
  - Status in DIRS: Parameter `budget_envelopes` in `RecoveryOptimizationRequest`.

  TIER 3: INTERNAL POLICY EQUITY RESERVES (DIRS CONFIGURATION LEVERS)
  ──────────────────────────────────────────────────────────────────
  - Authority: Administrative planning parameter selected by the Relief Commissioner.
  - Nature: Configurable target fraction θ_d reserving capital for equitable regional coverage.
  - Legal Status: Non-statutory, administratively adjustable policy preference.

  TIER 4: SCENARIO-BASED CONTINGENCY RESERVES (STOCHASTIC BUFFERS)
  ───────────────────────────────────────────────────────────────
  - Authority: Algorithmic mathematical buffer for price inflation or secondary monsoons.
  - Nature: Uncommitted liquidity reserve Φ_t held to absorb material cost escalations.
```

---

## 3. Policy Equity Reserve Mechanics & Boundary Conditions

Let $B$ denote the total government-approved capital budget across planning horizon $T$.  
Let $\underline{\theta}_d \in [0.0, 1.0]$ denote the administrative equity quota configured for District $d \in \mathcal{D}$ ($\sum_d \underline{\theta}_d \le 1.0$).  
The targeted policy reserve is:
$$R_{\text{target}, d} = \underline{\theta}_d \cdot B$$

The system enforces this reserve while rigorously handling four realistic edge conditions:

---

### 3.1 Case A: Census Baseline is Unknown ($P_{\text{census}, d} = \text{UNKNOWN}$)
- **Operational Reality:** The district's population count is unconfirmed due to missing archival records.
- **Reserve Handling:** The policy reserve $R_{\text{target}, d}$ is **NOT cancelled or reduced**.
- **Financial Status:** Held as an **Administrative Policy Encumbrance** ($R_{\text{held}, d} = R_{\text{target}, d}$).
- **Solver Behavior:** The solver is prohibited from spending $R_{\text{held}, d}$ on other districts. Capital is released for individual projects as field assessments verify local ward populations.

---

### 3.2 Case B: District Reports are Completely Absent (Communication / Road Blackout)
- **Operational Reality:** Zero damage reports or project proposals have been ingested from District $d$ ($|J_d| = 0$).
- **Legal & Administrative Rule:** Absence of data in a known hazard zone does **not** create a legal forfeit.
- **Financial Status:** Designated as an **Uncontacted Hazard Reserve** ($R_{\text{blackout}, d} = \underline{\theta}_d B$).
- **Lifecycle:**
  - Capital remains frozen in the state disaster account.
  - The solver optimizes the remaining unencumbered budget: $B_{\text{active}} = B - \sum_{d \in \text{Blackout}} R_{\text{blackout}, d}$.
  - An emergency aerial reconnaissance mission is triggered to re-establish communication.

---

### 3.3 Case C: No Eligible Projects / Capital Absorption Deficit
- **Operational Reality:** Total capital cost of all submitted projects in District $d$ is less than the administrative reserve:
  $$\sum_{j \in J_d} c_j < R_{\text{target}, d}$$
- **Legal Rule:** An internal policy quota **cannot compel the state to fund non-existent or wasteful projects**.
- **Remediation:**
  - The solver selects $100\%$ of qualifying, verified projects in District $d$:
    $$w_j = 1 \quad \forall j \in J_d$$
  - The unabsorbed surplus:
    $$\Delta R_d = R_{\text{target}, d} - \sum_{j \in J_d} c_j$$
    is labeled an **Administrative Surplus Reserve**. It is transferred to the State General Disaster Reserve for reallocation via formal Ministerial order.

---

### 3.4 Case D: Reserve Cannot Be Spent Within the Planning Horizon ($t > T$)
- **Operational Reality:** Due to severe contractor shortages or extreme monsoon delays, projects in District $d$ cannot break ground before horizon deadline $T$.
- **Financial Expiration Protocol:**
  - Internal policy reserves **expire at $t = T$** and do not constitute an indefinite legal liability.
  - Unspent balances are handled via standard public financial rules:
    $$\Phi_{\text{unspent}} = R_{\text{held}, d} - \text{Expenditure}_d$$
  - In municipal accounting, $\Phi_{\text{unspent}}$ rolls over into the subsequent fiscal year's SDRF opening balance or is de-obligated by the State Finance Department.

---

## 4. Summary Matrix: Financial Reserve Lifecycle

| Operational Scenario | Reserve Classification | Financial Action | Legal Authority Required for Reallocation |
| :--- | :--- | :--- | :--- |
| **Normal Operations** | Active Project Capital | Progress payments released against milestone certificates. | Routine departmental sanction order. |
| **Unknown Baseline** | Administrative Policy Encumbrance | Held in reserve; projects scheduled on provisional basis. | District Collector operational validation. |
| **Blackout Zone** | Uncontacted Hazard Reserve | **100% frozen;** blocked from urban reallocation. | Formal SEC declaration lifting disaster status. |
| **Absorption Deficit** | Administrative Surplus Reserve | Excess capital released back to state central pool. | Disaster Finance Director administrative memo. |
| **Horizon Expiration** | Expired Fiscal Balance | De-obligated or rolled over to next fiscal cycle. | State Legislative / Treasury roll-over rules. |

---
*End of DIRS Phase 6D-A DEF-6D-11 Remediation Document.*
