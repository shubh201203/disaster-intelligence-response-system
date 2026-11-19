# DIRS Phase 6D-A — Equity Reserve Accounting & Lifecycle Architecture
## Complete Accounting Lifecycle, Administrative Authority Triggers, and Non-Statutory Policy Rules

**Document ID:** `DIRS-PHASE6D-DOC-30`  
**Classification:** PUBLIC DISASTER FINANCE & ACCOUNTING AUDIT  
**Lead Authors:** Principal Disaster Public Finance Specialist & Forensic Software Auditor  
**Date:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Executive Summary & Legal Demarcation (Task 4)

This document formalizes the complete financial accounting lifecycle for regional recovery equity reserves in DIRS.

### 1.1 Four-Tier Authority Lexicon
To ensure legal and financial precision, all capital flows are categorized into four distinct authority tiers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        FINANCIAL AUTHORITY & ACCOUNTING LEXICON                        │
└────────────────────────────────────────────────────────────────────────────────────────┘

  TIER 1: STATUTORY FUNDING OBLIGATIONS (LEGAL ENACTMENTS)
  ────────────────────────────────────────────────────────
  - Binding statutory mandates under National/State Disaster Management Acts.
  - Governs inter-governmental transfers (e.g., SDRF / NDRF allocation formulas).
  - External boundary condition; DIRS does not originate statutory obligations.

  TIER 2: GOVERNMENT-APPROVED BUDGET ALLOCATIONS (EXECUTIVE ORDERS)
  ────────────────────────────────────────────────────────────────
  - Formally sanctioned capital ceiling B = ∑_{t=1}^T B_t approved by the State 
    Executive Committee (SEC) or Cabinet for a specific disaster recovery cycle.

  TIER 3: INTERNAL POLICY EQUITY RESERVES (PROPOSED POLICY RULES)
  ──────────────────────────────────────────────────────────────
  - Administrative planning parameters configured within DIRS: R_{target, d} = θ_d * B.
  - STATUS: Proposed administrative policy rule. NOT a statutory legal entitlement.

  TIER 4: SCENARIO CONTINGENCY BUFFERS (STOCHASTIC RESERVES)
  ─────────────────────────────────────────────────────────
  - Uncommitted cash balances Φ_t held to buffer against unexpected price inflation, 
    monsoon disruptions, or supply chain bottlenecks.
```

---

## 2. Complete Accounting Lifecycle Across Six Operational States

Let $B$ be the government-approved recovery budget. Let $\underline{\theta}_d \in [0.0, 1.0]$ be the administrative equity quota for District $d$, with target reserve $R_{\text{target}, d} = \underline{\theta}_d \cdot B$.

### 2.1 State 1: Unknown Census Baseline ($P_{\text{census}, d} = \text{UNKNOWN}$)
- **Accounting Treatment:** Reserve is classified as an **Administrative Policy Encumbrance** ($R_{\text{encumbered}, d} = R_{\text{target}, d}$).
- **Ledger Behavior:** Capital is credited to District $d$'s virtual account. Individual verified projects are scheduled and funded using absolute headcount scaling ($\psi / 500$).
- **De-encumbrance Trigger:** When municipal authorities validate the census baseline, remaining encumbered funds transition to standard project allocations.

---

### 2.2 State 2: District Blackout / Zero Submitted Projects ($|J_d| = 0$)
- **Accounting Treatment:** Classified as an **Uncontacted Hazard Reserve** ($R_{\text{blackout}, d} = \underline{\theta}_d \cdot B$).
- **Ledger Behavior:** $100\%$ of $R_{\text{blackout}, d}$ is **frozen in the central treasury**.
- **Prohibition on Diversion (Policy Rule):** The optimization solver is mathematically blocked from reallocating $R_{\text{blackout}, d}$ to well-connected urban districts.
- **Release Trigger:** Physical access restoration or aerial damage assessment. If field reconnaissance confirms zero physical damage, the reserve is formally de-frozen by Ministerial memo.

---

### 2.3 State 3: Insufficient Eligible Project Absorption ($\sum_{j \in J_d} c_j < R_{\text{target}, d}$)
- **Accounting Treatment:** 
  - Capital required for all qualifying projects is committed: $E_d = \sum_{j \in J_d} c_j$.
  - The unabsorbed remainder $\Delta R_d = R_{\text{target}, d} - E_d$ is classified as an **Administrative Absorption Surplus**.
- **Policy Rule:** The platform **never forces wasteful capital spending** to meet an arbitrary quota.
- **Release Authority:** $\Delta R_d$ is held until the mid-term recovery review (Period $t = \lfloor T/2 \rfloor$). If no new project proposals emerge, the Disaster Finance Director may de-encumber $\Delta R_d$ back to the State General Disaster Pool via administrative memo.

---

### 2.4 State 4: Unspent Reserve at Planning Horizon Expiry ($t > T$)
- **Accounting Treatment:** Unspent cash balances are classified as **Expired Fiscal Balances** ($\Phi_{\text{unspent}, d}$).
- **Public Finance Reality:** Internal policy reserves do not constitute indefinite legal liabilities.
- **Resolution:** At horizon deadline $T$, all unspent, uncommitted reserves lapse in accordance with state treasury rules. They do not automatically roll over into local municipal accounts.

---

### 2.5 State 5: Early Reserve Release (Emergency Reallocation)
- **Condition:** A severe secondary catastrophe (e.g., dam breach or secondary earthquake) strikes District $b$ during Period $t_k$.
- **Accounting Procedure:**
  - Relief Commissioner issues an **Emergency Administrative Reallocation Order**.
  - Uncommitted surplus reserves from District $d$ ($\Delta R_d$) are transferred to District $b$.
  - **Audit Logging:** Action `RESERVE_EMERGENCY_REALLOCATION` is written to `RecoveryOverrideLog`, recording the originating official, statutory justification, and financial ledger shift.

---

### 2.6 State 6: Rollover into Subsequent Approved Budget
- **Condition:** Recovery operations transition from Phase 6 (Medium-term reconstruction) to long-term multi-year development.
- **Accounting Procedure:**
  - Closing cash balance $\Phi_T$ is audited.
  - Carried forward into the next fiscal cycle's opening disaster fund balance as:
    $$\text{OpeningBalance}_{\text{Year } 2} = \eta_{\text{fiscal}} \cdot \Phi_T$$
    where $\eta_{\text{fiscal}} \in [0.95, 1.00]$ accounts for state administrative close-out fees.

---

## 3. Summary Accounting Lifecycle Matrix

| Operational State | Reserve Classification | Solver Action | Disbursement Authority | Rollover / Expiration Rule |
| :--- | :--- | :--- | :--- | :--- |
| **Unknown Baseline** | Policy Encumbrance | Schedules projects via $\psi / 500$. | Provisional until field baseline validated. | Active through horizon $T$. |
| **Blackout Zone** | Uncontacted Hazard Reserve | **100% frozen;** excluded from active solver pool. | Blocked until reconnaissance complete. | Requires formal SEC release order. |
| **Absorption Deficit** | Administrative Surplus | Funds $100\%$ of qualifying projects ($w_j=1$). | Automatic for projects; surplus held. | Surplus released at Period $\lfloor T/2 \rfloor$. |
| **Horizon Expiry ($t > T$)** | Expired Fiscal Balance | Solver execution complete. | Frozen; zero new tenders permitted. | Lapses to State Treasury pool. |
| **Early Release** | Emergency Reallocation | System initiates new optimization run. | Ministerial Executive Order required. | Immediate transfer to target district. |
| **Fiscal Rollover** | Closing Liquid Balance | Output: final surplus $\Phi_T$. | State Accountant General audit sign-off. | Credits Opening Balance of next cycle. |

---
*End of DIRS Phase 6D-A Task 4 Lifecycle Document.*
