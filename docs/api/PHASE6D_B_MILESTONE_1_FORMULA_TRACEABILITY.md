# DIRS PHASE 6D-B — FORMULA TRACEABILITY DIRECTORY
## Pure Mathematical Services Verification

**Project:** DIRS — Disaster Intelligence and Response System  
**Phase:** 6D-B (Recovery Prioritization, Equity-Constrained Allocation & Optimization Engine)  
**Milestone:** 1 — Domain Contracts and Pure Mathematical Services  
**Document:** Mathematical Formula Traceability & Policy Derivation  
**Date:** 2026-11-16  
**Status:** FULLY RECONCILED AGAINST PHASE 6D-A SPECIFICATIONS  

---

## 1. Vulnerability Scoring Formula Traceability (DEF-M1-01)

### 1.1. Authoritative Formula
Under Phase 6D-A, the authoritative demographic vulnerability headcount index is:
$$\psi = 1.0 \cdot N_{\text{GEN}} + 2.5 \cdot N_{\text{ACC}} + 3.0 \cdot N_{\text{MED}} + 4.5 \cdot N_{\text{MED\_ACC}}$$

- **Component Definitions:**
  - $N_{\text{GEN}}$: General population / unsegregated baseline members (weight: $1.00$).
  - $N_{\text{ACC}}$: Population with functional/mobility limitations requiring accessible recovery (weight: $2.50$).
  - $N_{\text{MED}}$: Population dependent on chronic medical lifelines (electricity-dependent medical devices, refrigeration, oxygen, dialysis) (weight: $3.00$).
  - $N_{\text{MED\_ACC}}$: Intersectional co-occurrence: individuals experiencing both accessible needs and chronic medical dependence (weight: $4.50$).
- **No Double-Counting Invariant:**
  - Each individual belongs to exactly one category:
    $$\sum_{\text{sub}} N_{\text{sub}} \le N_{\text{total}}$$
- **Code Implementation:**
  - `DemographicWeights` in `backend/app/recovery/services/vulnerability_scoring_service.py`:
    ```python
    @dataclass(frozen=True)
    class DemographicWeights:
        general_base: float = 1.00
        accessible_needs: float = 2.50
        chronic_medical: float = 3.00
        intersectional: float = 4.50
    ```

### 1.2. Incomplete Demographic Data & Lower-Bound Estimation
When field reconnaissance reports total affected population $N_{\text{total}}$ but demographic categorization is partial or absent:
- **Mandatory Policy Rule:** Missing subgroups are **never** treated as zero.
- **Unsegregated Remainder:**
  $$N_{\text{unseg}} = \max\left(0, N_{\text{total}} - (N_{\text{ACC}} + N_{\text{MED}} + N_{\text{MED\_ACC}})\right)$$
- **Conservative Lower Bound:**
  $$\psi_{\text{lower}} = 1.0 \cdot N_{\text{unseg}} + 2.5 \cdot N_{\text{ACC}} + 3.0 \cdot N_{\text{MED}} + 4.5 \cdot N_{\text{MED\_ACC}}$$
- **Status Flags:**
  - If $N_{\text{unseg}} > 0$: sets `is_lower_bound = True` and `uncertainty_flag = True`.
  - Monotonicity: For any fixed $N_{\text{total}}$, $\psi$ is monotonic non-decreasing with respect to identified vulnerability:
    $$\psi(N_{\text{ACC}} + N_{\text{MED}} > 0) \ge \psi(N_{\text{total}} \text{ unsegregated})$$

### 1.3. Two-Branch Vulnerability Normalization
Normalized vulnerability score $\phi_V \in [0.0, 1.0]$ is evaluated through two distinct policy branches:
- **Branch A — Known Verified Census Baseline ($P_{\text{census}} > 0$):**
  $$D_{\text{census}} = \max\left(100.0, 0.20 \cdot P_{\text{census}}\right), \quad \phi_V = \min\left(1.0, \frac{\psi}{D_{\text{census}}}\right)$$
- **Branch B — Unknown Census Baseline ($P_{\text{census}} \le 0$ or `None`):**
  $$D_{\text{ref}} = 500.0, \quad \phi_V = \min\left(1.0, \frac{\psi}{D_{\text{ref}}}\right)$$
  - Sets `baseline_status = "BASELINE_UNKNOWN"` and `uncertainty_flag = True`.
  - Zero or missing census data **never** divides by zero or null; $D_{\text{ref}} = 500.0$ provides statutory operational continuity until census verification is complete.
  - At $P_{\text{census}} = 2,500$, $0.20 \times 2,500 = 500.0$, demonstrating exact mathematical continuity between Branch A and Branch B upon reconciliation.

---

## 2. Multi-Criteria Priority Index (MCPI) Traceability (DEF-M1-02)

### 2.1. Formula & Administrative Policy Status
$$\text{MCPI}_j = 100 \times \left( w_L \phi_{L, j} + w_C \phi_{C, j} + w_V \phi_{V, j} + w_D \phi_{D, j} + w_E \phi_{E, j} \right)$$
- **Configurable Administrative Policy Weights:**
  - $w_L = 0.30$ (Life Safety)
  - $w_C = 0.25$ (Infrastructure Criticality)
  - $w_V = 0.20$ (Demographic Vulnerability)
  - $w_D = 0.15$ (Dependency Importance)
  - $w_E = 0.10$ (Economic Impact)
- **Administrative Status:** These weights are configurable administrative policy assumptions, **NOT** statutory mandates.
- **Strict Validation:** Weights must be non-negative and sum to $1.0$ within numerical tolerance ($10^{-6}$).

### 2.2. Confidence & Freshness Independence
- **Rule:** Data freshness and confidence decay do **NOT** act as negative priority multipliers. Confidence represents observation reliability, not justification for deprioritizing distressed communities (DEF-6B-02 / Phase 6D-A).

### 2.3. Stable Deterministic Tie-Breaking & Specification Deviations
Per project-owner directives, the tie-breaking implementation departs from Section 5.1 of `PHASE6D_MCPI_MATHEMATICAL_FORMULATION.md` via two approved implementation exceptions recorded in [`docs/PHASE6D_B_MILESTONE_1_SPECIFICATION_DEVIATION_REGISTER.md`](file:///c:/Users/shubh/Downloads/DIRS/docs/PHASE6D_B_MILESTONE_1_SPECIFICATION_DEVIATION_REGISTER.md):
- **DEV-M1-01 (Exact Float Comparisons):** Replaces the frozen $10^{-4}$ tolerance threshold with exact unrounded 64-bit IEEE double float evaluation, ensuring small substantive differences are never overridden.
- **DEV-M1-02 (Stable Project ID Arbiter):** Replaces cryptographic SHA-256 hashing with ascending `project_id` as the final non-substantive ordering.

The authoritative ordering hierarchy is:
1. **Tier 1 Mandatory Safety:** Mandatory projects (`is_tier1_mandatory == True`) always precede non-mandatory projects.
2. **MCPI Composite Score:** Descending order (exact float).
3. **Primary Substantive Tie-Breaker:** $\phi_{\text{life\_safety}}$ descending (exact float).
4. **Secondary Substantive Tie-Breaker:** $\phi_{\text{vulnerability}}$ descending (exact float).
5. **Tertiary Substantive Tie-Breaker:** Transitive cascade count descending (exact integer).
6. **Quaternary Substantive Tie-Breaker:** Estimated cost ascending (exact float; lower cost first).
7. **Stable Non-Substantive Final Arbiter:** Project ID (`project_id`) ascending (alphabetical). Only invoked if criteria 1–6 are mathematically identical.

### 2.4. Priority Tier Status & Non-Compensatory Filter
- **Authoritative Priority Designation:** The only authoritative priority tier established in Phase 6D-A is `TIER_1_MANDATORY` for critical life-safety breaches ($S_L \ge 0.85$).
- **Inactive Optional Policy Proposals:** Numerical score tiers ($\ge 70, \ge 50, \ge 30, < 30$) are strictly **inactive optional proposals** requiring project-owner approval before activation. They do not govern active portfolio sorting.
- **Non-Compensatory Filter:** When $S_L \ge \tau_L = 0.85$, the project is flagged `is_tier1_mandatory = True` and elevated into `TIER_1_MANDATORY` regardless of MCPI score, preventing compensatory trade-offs from compromising life-safety.

---

## 3. Life-Safety Triage & Engineering Disclaimers (Verification B)

### 3.1. Formulation
$$S_L = 0.70 \cdot \phi_{\text{damage}} + 0.20 \cdot H_{\text{secondary}} + 0.10 \cdot \Omega_{\text{occupancy}}$$
- All components bounded in $[0.0, 1.0]$.
- Discrete structural damage ratings map to: NONE ($0.0$), MINOR ($0.25$), MODERATE ($0.50$), SEVERE ($0.75$), COLLAPSED/DESTROYED ($1.00$).

### 3.2. Mandatory Engineering & Licensure Disclaimers
The triage threshold $\tau_L = 0.85$ is explicitly documented in code and metadata:
- **NOT an empirical civil engineering collapse probability** or structural limit-state calculation.
- **Does NOT constitute structural engineering certification** or building habitability clearance.
- **Does NOT treat administrative GOVT verification** as professional engineering licensure.

---

## 4. Internal Policy District Equity & Liquidity Separation (DEF-M1-03 & Verification C)

### 4.1. Terminology Reconciliation
All occurrences of "statutory district target", "statutory equity target", and "escrow" have been replaced with:
- **"Internal policy district equity floor"** ($\underline{\theta}_d \cdot B$)
- **"Configurable district allocation target"** ($E_d^{\text{target}} = \min(\underline{\theta}_d B, \sum c_j)$)
- **"Policy ring-fencing" / "Unabsorbed policy reserve"** ($\Delta R_d = \max(0, \underline{\theta}_d B - \sum c_j)$)

### 4.2. Formulations
- **Policy Floor:** $E_d^{\text{floor}} = \underline{\theta}_d \times B$
- **Dynamic Capacity Bound:**
  $$E_d^{\text{target}} = \min\left(\underline{\theta}_d \times B, \sum_{j \in J_d} c_j\right)$$
- **Unabsorbed Policy Reserve:**
  $$\Delta R_d = \max\left(0, \underline{\theta}_d \times B - \sum_{j \in J_d} c_j\right)$$
- **Uncontacted Blackout Reserve:**
  $$R_{\text{blackout}} = \sum_{d \in D_{\text{blackout}}} \underline{\theta}_d \times B$$
  *(Classified strictly as an internal policy allocation constraint and approved mathematical reserve rule. No external statute is cited; does not represent an actual financial escrow or commercial banking transfer).*

### 4.3. Equity Reserve vs. Spendable Liquidity Accounting Separation
- **Policy Ring-Fencing:** An unabsorbed reserve $\Delta R_d$ represents an internal administrative policy allocation boundary. It is **NOT** an actual financial escrow account, bank deposit, fund transfer, or cash restriction. No financial persistence or banking integration exists in Milestone 1.
- **Cash Liquidity:** Tracked through discrete multi-period carry-forward:
  $$\Phi_t = \eta \cdot \Phi_{t-1} + B_t - E_t \ge 0$$
- Unabsorbed equity reserves are NOT automatically spendable cash liquidity.

---

## 5. Calendar Model & Multi-Period Time Discretization (Verification A)

### 5.1. Engineering Justification for 30-Day Periods
- **Implementation Convention:** The 30-day period ($\Delta t = 30$ days) is an engineering implementation convention for mathematical tractability, **NOT** a Phase 6A statutory or mathematical mandate.
- **Disbursement Cycle Alignment:** Public disaster recovery budgets, state treasury drawdowns, and contractor progress billings occur in monthly/bi-monthly tranches.
- **Solver Intractability Avoidance:** A daily model over a 3–5 year recovery horizon produces $1,000–1,825$ discrete periods, resulting in combinatorial variable explosions in CP-SAT/MILP solvers without operational improvement.
- **Configurability:** Period length $\Delta t$ is fully configurable in all service signatures.

### 5.2. Boundary & Timestamp Conversion Conventions
- **UTC Half-Open Interval:** Period $t \in \{1, \dots, T\}$ covers:
  $$[T_0 + (t-1)\Delta t, \; T_0 + t\Delta t)$$
- **Timestamp to Period:**
  $$t = \left\lfloor \frac{D - T_0}{\Delta t} \right\rfloor + 1$$
- **Dependency Lag Conversion (Ceiling Rule):**
  $$L_{\text{periods}} = \left\lceil \frac{L_{\text{days}}}{\Delta t} \right\rceil$$
- **Boundary Verification Table:**
  - $0$ days $\to$ Period 1 (lag: $0$ periods)
  - $1$ day $\to$ Period 1 (lag: $1$ period)
  - $29$ days $\to$ Period 1 (lag: $1$ period)
  - $30$ days $\to$ Period 2 (lag: $1$ period)
  - $31$ days $\to$ Period 2 (lag: $2$ periods)
  - $60$ days $\to$ Period 3 (lag: $2$ periods)
- **Partial Final Period Treatment:** If project duration exceeds planning horizon ($s_j + D_j - 1 > T$), costs within periods $1..T$ are accounted for, and `is_fully_reconciled` is flagged `False`.
