# DIRS Phase 6D-A — DEF-6D-01: Unknown Census Baseline & Equity Correction
## Removal of Density Imputation, Unknown Baseline Protocol, and Escrow Equity Guarantees

**Document ID:** `DIRS-PHASE6D-DOC-14`  
**Classification:** EQUITY MATHEMATICS & DATA GOVERNANCE AUDIT  
**Lead Authors:** Principal Disaster Recovery Systems Architect & Humanitarian Data Governance Specialist  
**Date:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Executive Summary & Defect Remediation

In earlier drafts of the Phase 6D-A equity architecture, a heuristic was proposed wherein wards with missing census data were imputed using the "provincial median ward population density."

**Audit Finding (DEF-6D-01):**
Imputing an unobserved provincial median density to an unknown community violates fundamental humanitarian data principles:
1. It fabricates demographic figures, creating false certainty.
2. It distorts the vulnerable population normalization denominator ($\phi_V$), potentially penalizing or artificially inflating priority.
3. If an uncontacted rural area with dense tribal settlements is imputed with an artificially low provincial median, its true human need is erased.

**Remediation Mandate:**
- **Provincial median ward density imputation is 100% removed.**
- Missing census baselines remain strictly labeled `UNKNOWN` (`census_baseline_population = NULL` or flagged `BASELINE_UNKNOWN`).
- **Never substitute zero.** (Substituting zero would divide by zero or mathematically nullify community existence).
- **Never substitute provincial medians or synthetic averages as observed population counts.**
- **Never reduce priority because a baseline is missing.**
- Preserve the architectural distinction between verified statutory census data and user-supplied operational estimates.
- Define exact mathematical behavior of equity constraints when denominators are unavailable.

---

## 2. Provenance: Verified Statutory Census vs. User-Supplied Operational Estimates

In DIRS, demographic denominators exist in two strictly segregated tiers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DEMOGRAPHIC PROVENANCE DEMARCATION                              │
└────────────────────────────────────────────────────────────────────────────────────────┘

  TIER A: STATUTORY VERIFIED CENSUS DATA
  ──────────────────────────────────────
  - Origin: Official Registrar General / National Statistical Office decennial census.
  - Integrity: Statutorily gazetted, cryptographically checksummed, immutable.
  - Status in DIRS: No statutory Census of India or GCC tabular dataset is bundled in 
    the repository runtime. 

  TIER B: USER-SUPPLIED OPERATIONAL BASELINE ESTIMATE
  ──────────────────────────────────────────────────
  - Origin: Entered at runtime by municipal disaster authorities or NGO field heads 
    into `RecoveryNeed.census_baseline_population`.
  - Integrity: Subject to local administrative error, boundary shifts, and projection bias.
  - Status in DIRS: Operational estimate used for double-count detection and quota floors.
  - Fallback State: If not provided by the user, status is strictly `UNKNOWN`.
```

---

## 3. Mathematical Treatment of Vulnerability $\phi_V$ Under Unknown Baselines

In Phase 6D, the normalized vulnerable population index $\phi_V(X_{V, j}) \in [0.0, 1.0]$ assesses the concentration of vulnerable persons ($N_{\text{vulnerable}}^{\text{weighted}}$) relative to total community exposure.

### 3.1 Known Operational Baseline Case
When $P_{\text{census}, d}$ is explicitly provided and validated:
$$\psi_j = N_{\text{GEN}, j} + 2.5 \cdot N_{\text{ACC}, j} + 3.0 \cdot N_{\text{MED}, j} + 4.5 \cdot N_{\text{MED\_ACC}, j}$$
$$\phi_V(X_{V, j}) = \min\left(1.0, \; \frac{\psi_j}{\max(100, \; 0.20 \cdot P_{\text{census}, d})}\right)$$

### 3.2 Unknown Baseline Case ($P_{\text{census}, d} = \text{UNKNOWN}$)
When $P_{\text{census}, d}$ is null, unverified, or missing:
- **Rule 1 (No Imputation):** The system **does not invent a denominator**.
- **Rule 2 (Absolute Need Count Scaling):** When the baseline denominator is unknown, $\phi_V$ transitions from a *concentration ratio* to a *saturating absolute headcount function*:
  $$\phi_V(X_{V, j}) = \min\left(1.0, \; \frac{\psi_j}{\psi_{\text{ref}}}\right)$$
  where $\psi_{\text{ref}} = 1,000$ weighted vulnerable persons represents a regionally established operational saturation point.
- **Rule 3 (Uncertainty Penalty Prohibition):** The computed score is **never downgraded or penalized** due to the missing denominator. Instead, the project record is tagged:
  ```json
  {
    "vulnerability_calculation_mode": "ABSOLUTE_HEADCOUNT_SATURATION",
    "census_baseline_status": "UNKNOWN",
    "verification_flag": "FLAG_FIELD_CENSUS_RECONCILIATION_REQUIRED"
  }
  ```
- **Rule 4 (Field Verification Trigger):** An automated reconnaissance task is dispatched to the district administration to verify local electoral or ration-card rolls.

---

## 4. District Equity Floor Under Incomplete or Blackout Data

The District Equity Floor constraint ensures that vulnerable districts are not starved of capital by well-connected urban centers:
$$\sum_{j \in J_d} c_j \cdot w_j \ge \underline{\theta}_d \cdot B, \quad \forall d \in \mathcal{D}$$

### 4.1 The Complete Communication Blackout Scenario
Suppose District $d$ is situated directly in the cyclone eye wall or earthquake rupture zone. Cellular networks are collapsed, roads are washed out, and zero damage reports have been ingested ($|J_d| = 0$).

**Perverse Solver Trap (Without DEF-6D-01 Correction):**
Under standard linear optimization, because District $d$ has submitted 0 projects, setting $w_j = 0$ for District $d$ allows the solver to spend District $d$'s statutory budget quota ($\underline{\theta}_d B$) on secondary urban projects in District $a$ and District $b$, permanently stripping recovery capital from the most severely impacted zone.

### 4.2 The Anti-Bias Escrow Reservation Protocol

When District $d$ has an unknown population baseline and zero or incomplete project submissions:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        STATUTORY ESCROW EQUITY PRESERVATION                            │
└────────────────────────────────────────────────────────────────────────────────────────┘

  1. Mandatory District Budget Quota:
     B_quota(d) = θ_d * B

  2. Submitted Project Volume:
     C_submitted(d) = ∑_{j ∈ J_d} c_j

  3. Allocation Logic:
     IF C_submitted(d) ≥ B_quota(d):
        Active Solver Constraint: ∑_{j ∈ J_d} c_j * w_j ≥ B_quota(d)
     
     ELSE IF C_submitted(d) < B_quota(d) AND District_Status == RECONNAISSANCE_BLACKOUT:
        Active Solver Constraint:
           - Fund 100% of verified submitted projects: w_j = 1  ∀ j ∈ J_d
           - Escrow Unallocated Remainder: B_escrow(d) = B_quota(d) - C_submitted(d)
           - FROZEN LIQUIDITY: B_escrow(d) CANNOT be reallocated to other districts!
```

**Mathematical Invariant:**
$$\sum_{j \in \mathcal{P}} c_j \cdot w_j + \sum_{d \in \mathcal{D}_{\text{blackout}}} B_{\text{escrow}, d} \le B$$
By reserving $B_{\text{escrow}, d}$ in a locked escrow pool, the solver preserves capital for uncontacted communities until field verification missions restore communication.

---

## 5. Summary Table: Baseline Status Governance

| Field State | Mathematical Treatment | Priority Effect | Governance Flag | Escrow Action |
| :--- | :--- | :--- | :--- | :--- |
| **Verified Census Baseline** | $\phi_V = \min(1.0, \frac{\psi}{0.2 P_{\text{census}}})$ | Standard concentration score. | `BASELINE_VERIFIED` | Standard budget optimization. |
| **User Operational Estimate** | $\phi_V = \min(1.0, \frac{\psi}{0.2 P_{\text{operational}}})$ | Standard concentration score. | `OPERATIONAL_ESTIMATE` | Soft ceiling warning if exceeded. |
| **Baseline UNKNOWN** | $\phi_V = \min(1.0, \frac{\psi}{\psi_{\text{ref}}})$ | **Zero penalty.** Absolute need evaluated. | `BASELINE_UNKNOWN` | Escrow quota $\underline{\theta}_d B$ locked against reallocation. |
| **Zero Reports (Blackout)** | $|J_d| = 0$ | N/A (Projects pending ingestion). | `HAZARD_ZONE_BLACKOUT` | **100% of $\underline{\theta}_d B$ locked in escrow;** drone reconnaissance triggered. |

---
*End of DIRS Phase 6D-A DEF-6D-01 Remediation Document.*
