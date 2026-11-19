# DIRS Phase 6D-A — DEF-6D-02: Life-Safety Threshold Reproducibility & Formal Governance
## Synthetic Benchmark Definition, Confusion Matrices, and Policy Separation

**Document ID:** `DIRS-PHASE6D-DOC-15`  
**Classification:** OPERATIONS RESEARCH & ALGORITHMIC AUDIT  
**Lead Authors:** Principal Optimization Engineer & Forensic Software Auditor  
**Date:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Audit Disclosure & Status of Prior Sensitivity Table

In the preliminary Phase 6D-A validation report, a 5-tier sensitivity table was presented for threshold values $\tau_L \in [0.70, 0.95]$.

**Explicit Forensic Disclosure (DEF-6D-02):**
- The figures in that preliminary table were **illustrative theoretical projections** intended to demonstrate mathematical monotonicity, not outputs of an automated solver batch run.
- In this document, we provide the **exact, fully reproducible synthetic dataset definition**, explicit ground-truth definitions, confusion matrices, and hand-verifiable arithmetic for each threshold level.
- **Classification Status:** The threshold value $\tau_L = 0.85$ is formally retained as an **unvalidated executive policy parameter**, NOT a statutory civil engineering code standard.

---

## 2. Reproducible Synthetic Dataset Definition ($N = 100$)

To enable exact verification across research reviews, we specify an explicit, deterministic synthetic portfolio of $N = 100$ recovery projects generated under seed `seed=42`:

### 2.1 Facility Generation & Ground-Truth Hazard Distribution
The ground-truth structural state of each facility is classified by physical civil engineering criteria:
- **Ground Truth $Y_j = 1$ (True Critical Collapse Threat):** Severe load-bearing shear failure, foundation scour, or impending collapse threatening human occupancy.
- **Ground Truth $Y_j = 0$ (Non-Collapse Threat):** Moderate, minor, or cosmetic structural damage; safe for occupancy or urgent non-collapse utility repairs.

In the synthetic portfolio of $100$ projects:
- **True Critical Collapse Facilities ($Y = 1$):** Exactly $15$ projects.
- **True Non-Collapse Facilities ($Y = 0$):** Exactly $85$ projects.

### 2.2 Continuous Damage Hazard Score Distribution ($S_{L, j} \in [0.0, 1.0]$)
Each project $j$ is assigned an assessed continuous safety hazard score $S_{L, j}$ (derived from structural damage features and secondary hazard exposure):
1. **Critical Cluster ($15$ projects):** $S_L$ distributed in $[0.72, 0.98]$:
   - $S_L \in [0.70, 0.79]$: $2$ projects ($S_L = 0.74, 0.78$)
   - $S_L \in [0.80, 0.84]$: $2$ projects ($S_L = 0.81, 0.83$)
   - $S_L \in [0.85, 0.89]$: $4$ projects ($S_L = 0.86, 0.87, 0.88, 0.89$)
   - $S_L \in [0.90, 0.94]$: $4$ projects ($S_L = 0.91, 0.92, 0.93, 0.94$)
   - $S_L \in [0.95, 1.00]$: $3$ projects ($S_L = 0.96, 0.98, 1.00$)
2. **Non-Critical Cluster ($85$ projects):** $S_L$ distributed in $[0.10, 0.79]$ with slight sensor noise:
   - $S_L \in [0.10, 0.49]$: $45$ projects (minor / moderate)
   - $S_L \in [0.50, 0.69]$: $20$ projects (moderate)
   - $S_L \in [0.70, 0.79]$: $14$ projects (false alarm borderlines due to surface rubble)
   - $S_L \in [0.80, 0.84]$: $5$ projects (false alarm borderlines due to severe facade detachment)
   - $S_L \in [0.85, 0.89]$: $1$ project ($S_L = 0.86$ — heavy non-structural roof collapse)
   - $S_L \ge 0.90$: $0$ projects.

### 2.3 Financial Parameters
- Total available multi-period recovery budget: $B = 10,000$ Lakh INR.
- Early-period budget envelope ($B_1 + B_2$ tranches): $B_{\text{early}} = 3,500$ Lakh INR.
- Average capital cost per Tier 1 mandatory project: $\bar{c}_{\text{Tier 1}} = 120$ Lakh INR.

---

## 3. Explicit Confusion Matrices & Reproducible Sensitivity Arithmetic

The Stage 1 Non-Compensatory Policy Rule classifies a project as `TIER_1_MANDATORY` if:
$$\hat{Y}_j(\tau_L) = \mathbb{I}(S_{L, j} \ge \tau_L)$$

### 3.1 Confusion Matrix Definitions
- **True Positive ($TP$):** $S_{L, j} \ge \tau_L$ AND $Y_j = 1$ (True collapse hazard correctly prioritized).
- **False Positive ($FP$):** $S_{L, j} \ge \tau_L$ AND $Y_j = 0$ (Non-collapse hazard incorrectly mandated into early periods).
- **False Negative ($FN$):** $S_{L, j} < \tau_L$ AND $Y_j = 1$ (True collapse hazard missed by Stage 1 filter; subject to competitive economic trade-offs).
- **True Negative ($TN$):** $S_{L, j} < \tau_L$ AND $Y_j = 0$ (Non-collapse hazard correctly routed to competitive MCPI optimization).
- **Budget Preemption ($C_{\text{Tier 1}}$):** $(TP + FP) \times 120$ Lakh INR.
- **Early Budget Utilization:** $\frac{C_{\text{Tier 1}}}{B_{\text{early}}} = \frac{C_{\text{Tier 1}}}{3500} \times 100\%$.

---

### 3.2 Threshold-by-Threshold Exact Evaluation

#### Case A: $\tau_L = 0.70$
- Qualifying projects with $S_L \ge 0.70$:
  - From Critical ($Y=1$): $2 + 2 + 4 + 4 + 3 = 15$ ($TP = 15$)
  - From Non-Critical ($Y=0$): $14 + 5 + 1 = 20$ ($FP = 20$)
- Confusion Matrix:
  $$TP = 15, \quad FP = 20, \quad FN = 0, \quad TN = 65$$
  - Total Mandated: $15 + 20 = 35$ projects.
  - False Negative Rate: $FN / 15 = 0 / 15 = \mathbf{0.0\%}$.
  - False Positive Count: $\mathbf{20}$ facilities preempt capital.
  - Early Budget Consumed: $35 \times 120 = 4,200$ Lakh INR.
  - Early Budget Ratio: $4,200 / 3,500 = \mathbf{120.0\%}$ (**INSUFFICIENT EARLY BUDGET — INFEASIBLE**).

#### Case B: $\tau_L = 0.80$
- Qualifying projects with $S_L \ge 0.80$:
  - From Critical ($Y=1$): $2 + 4 + 4 + 3 = 13$ ($TP = 13$, $FN = 2$)
  - From Non-Critical ($Y=0$): $5 + 1 = 6$ ($FP = 6$)
- Confusion Matrix:
  $$TP = 13, \quad FP = 6, \quad FN = 2, \quad TN = 79$$
  - Total Mandated: $13 + 6 = 19$ projects.
  - False Negative Rate: $2 / 15 = \mathbf{13.3\%}$ ($2$ critical facilities missed).
  - Early Budget Consumed: $19 \times 120 = 2,280$ Lakh INR.
  - Early Budget Ratio: $2,280 / 3,500 = \mathbf{65.1\%}$ (**FEASIBLE**).

#### Case C: $\tau_L = 0.85$ (Current Baseline Policy)
- Qualifying projects with $S_L \ge 0.85$:
  - From Critical ($Y=1$): $4 + 4 + 3 = 11$ ($TP = 11$, $FN = 4$)
  - From Non-Critical ($Y=0$): $1$ ($FP = 1$)
- Confusion Matrix:
  $$TP = 11, \quad FP = 1, \quad FN = 4, \quad TN = 84$$
  - Total Mandated: $11 + 1 = 12$ projects.
  - False Negative Rate: $4 / 15 = \mathbf{26.7\%}$ ($4$ borderline collapse threats routed to competitive MCPI).
  - False Positive Count: $1$ facility.
  - Early Budget Consumed: $12 \times 120 = 1,440$ Lakh INR.
  - Early Budget Ratio: $1,440 / 3,500 = \mathbf{41.1\%}$ (**BALANCED BASELINE**).

#### Case D: $\tau_L = 0.90$
- Qualifying projects with $S_L \ge 0.90$:
  - From Critical ($Y=1$): $4 + 3 = 7$ ($TP = 7$, $FN = 8$)
  - From Non-Critical ($Y=0$): $0$ ($FP = 0$)
- Confusion Matrix:
  $$TP = 7, \quad FP = 0, \quad FN = 8, \quad TN = 85$$
  - Total Mandated: $7 + 0 = 7$ projects.
  - False Negative Rate: $8 / 15 = \mathbf{53.3\%}$ ($8$ true collapse hazards missed).
  - Early Budget Consumed: $7 \times 120 = 840$ Lakh INR.
  - Early Budget Ratio: $840 / 3,500 = \mathbf{24.0\%}$ (**ELEVATED SAFETY RISK**).

#### Case E: $\tau_L = 0.95$
- Qualifying projects with $S_L \ge 0.95$:
  - From Critical ($Y=1$): $3$ ($TP = 3$, $FN = 12$)
  - From Non-Critical ($Y=0$): $0$ ($FP = 0$)
- Confusion Matrix:
  $$TP = 3, \quad FP = 0, \quad FN = 12, \quad TN = 85$$
  - Total Mandated: $3$ projects.
  - False Negative Rate: $12 / 15 = \mathbf{80.0\%}$ ($12$ true collapse hazards missed).
  - Early Budget Consumed: $3 \times 120 = 360$ Lakh INR.
  - Early Budget Ratio: $360 / 3,500 = \mathbf{10.3\%}$ (**PATHOLOGICALLY PERMISSIVE**).

---

## 4. Comprehensive Reproducible Comparison Matrix

| Threshold $\tau_L$ | $TP$ | $FP$ | $FN$ | $TN$ | Total Mandated | Precision | Recall | Early Budget Spent ($B_1+B_2$) | Solvency & Feasibility Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **$0.70$** | $15$ | $20$ | $0$ | $65$ | $35$ | $42.9\%$ | $100.0\%$ | $4,200$ Lakh ($120\%$) | **INFEASIBLE:** Exceeds early cash envelopes by $700$ Lakh. |
| **$0.80$** | $13$ | $6$ | $2$ | $79$ | $19$ | $68.4\%$ | $86.7\%$ | $2,280$ Lakh ($65.1\%$) | **FEASIBLE:** Strong protection; absorbs $65\%$ of liquidity. |
| **$0.85$** | **$11$** | **$1$** | **$4$** | **$84$** | **$12$** | **$91.7\%$** | **$73.3\%$** | **$1,440$ Lakh ($41.1\%$)** | **BALANCED BASELINE:** High precision ($91.7\%$); cash solvent. |
| **$0.90$** | $7$ | $0$ | $8$ | $85$ | $7$ | $100.0\%$ | $46.7\%$ | $840$ Lakh ($24.0\%$) | **DANGEROUS:** Misses over half ($53.3\%$) of collapse hazards. |
| **$0.95$** | $3$ | $0$ | $12$ | $85$ | $3$ | $100.0\%$ | $20.0\%$ | $360$ Lakh ($10.3\%$) | **UNACCEPTABLE:** Ignores $80\%$ of critical structures. |

---

## 5. Strict Separation: Policy Change vs. Solver Relaxation

A critical principle of DIRS governance is that **the optimization solver must NEVER silently lower the safety threshold $\tau_L$ to escape an infeasible run**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        SEPARATION OF POWERS: POLICY VS. SOLVER                         │
└────────────────────────────────────────────────────────────────────────────────────────┘

  OPERATION TYPE 1: FORMAL EXECUTIVE POLICY CHANGE
  ────────────────────────────────────────────────
  - Actor: Authorized Ministerial Official (Disaster Finance Director / Relief Commissioner).
  - Scope: Changing global threshold parameter (e.g., from τ_L = 0.85 to τ_L = 0.80).
  - Mechanism: Formal API request with cryptographic authentication and signed executive order.
  - Traceability: Written to `RecoveryOverrideLog` with mandatory statutory rationale.
  - Execution: Initiates an entirely NEW, independent optimization run.

  OPERATION TYPE 2: SOLVER CONSTRAINT RELAXATION (INADMISSIBLE FOR SAFETY)
  ────────────────────────────────────────────────────────────────────────
  - Actor: Automated CP-SAT solver algorithm or Infeasibility Relaxation Advisor.
  - Rule: The solver is STRICTLY FORBIDDEN from altering τ_L or dropping Tier 1 mandatory 
    projects from early execution periods.
  - Action on Infeasibility: The solver terminates with status `INFEASIBLE`. The Advisor 
    reports: "Early budget B_early = 3500 Lakh is insufficient to fund 35 mandatory 
    Tier 1 projects (4200 Lakh required). Human policy intervention required."
```

---
*End of DIRS Phase 6D-A DEF-6D-02 Remediation Document.*
