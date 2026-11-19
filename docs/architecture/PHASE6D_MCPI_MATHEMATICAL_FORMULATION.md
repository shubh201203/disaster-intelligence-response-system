# DIRS Phase 6D-A — Multi-Criteria Recovery Priority Index (MCPI) Mathematical Formulation

**Document ID:** `DIRS-PHASE6D-DOC-03`  
**Classification:** OPERATIONS RESEARCH & MATHEMATICAL SPECIFICATION  
**Author:** Principal Operations Research Scientist & Mathematical Optimization Engineer  
**Date:** November 16, 2026  
**Status:** COMPLETE (PHASE 6D-A DESIGN BASELINE)  

---

## 1. Mathematical Formulation

Let $\mathcal{P} = \{1, 2, \dots, N\}$ denote the set of candidate post-disaster recovery projects submitted for prioritization. For each project $j \in \mathcal{P}$, the Multi-Criteria Recovery Priority Index $\text{MCPI}_j \in [0.0, 100.0]$ is defined as:

$$\text{MCPI}_j = 100 \cdot \sum_{k \in \mathcal{K}} w_k \cdot \phi_k(X_{k, j})$$

Where:
- $\mathcal{K} = \{L, C, V, D, E\}$ represents the set of five evaluation criteria:
  - $L$: Life-Safety Urgency
  - $C$: Critical Infrastructure Tier
  - $V$: Vulnerable Population Density
  - $D$: Dependency Cascade Centrality
  - $E$: Economic & Livelihood Restoration
- $w_k \in \mathbb{R}^+$: Calibrated criteria weight assigned to criterion $k$ ($\sum_{k} w_k = 1.0$).
- $X_{k, j}$: Raw attribute measurement of project $j$ under criterion $k$.
- $\phi_k(\cdot) \in [0.0, 1.0]$: Dimensionless normalization mapping function for criterion $k$.

> [!IMPORTANT]
> **Decoupling of Confidence Decay from Priority Scoring (DEF-6B-02 Alignment):**  
> In accordance with Phase 6B remediation DEF-6B-02, continuous exponential confidence decay is **strictly deferred to Phase 6F**. Data confidence ($C_{\text{obs}}$) and freshness status (`FRESH`, `MODERATE`, `STALE_AMBER`, `EXPIRED_RED`) **do NOT discount or reduce project priority scores**. Stale data from remote or neglected areas must never lead to deprioritization; instead, freshness status operates as a **governance gate flag** (`HOLD_PENDING_FIELD_REINSPECTION`) requiring physical verification prior to capital fund disbursement.

---

## 2. Normalization Functions & Measurement Scales

To combine heterogeneous physical indicators (rupees, person counts, graph out-degrees, categorical tiers) into a coherent index, each raw attribute $X_{k, j}$ is mapped via a calibrated normalization function $\phi_k(X_{k, j}) \in [0.0, 1.0]$.

### 2.1 Criterion $L$: Life-Safety Urgency ($\phi_L$)
Raw measurement $X_{L, j} \in \{0, 1, 2, 3, 4\}$ derives from certified field structural damage level and secondary hazard proximity:
$$\phi_L(X_{L, j}) = \begin{cases} 
1.00 & \text{if } X_{L, j} = 4 \text{ (DESTROYED with acute collapse/breach threat)} \\ 
0.75 & \text{if } X_{L, j} = 3 \text{ (SEVERE structural compromise of active facility)} \\ 
0.50 & \text{if } X_{L, j} = 2 \text{ (MODERATE impairment; no immediate collapse)} \\ 
0.25 & \text{if } X_{L, j} = 1 \text{ (MINOR superficial cladding or cosmetic damage)} \\ 
0.00 & \text{if } X_{L, j} = 0 \text{ (NONE; preventative upgrade or administrative)} 
\end{cases}$$

### 2.2 Criterion $C$: Critical Infrastructure Tier ($\phi_C$)
Categorical lifeline classification based on national infrastructure protection guidelines:
$$\phi_C(X_{C, j}) = \begin{cases} 
1.00 & \text{if } \text{Tier 1: Major Trauma Hospital, Regional Water Reservoir, Grid Substation} \\ 
0.75 & \text{if } \text{Tier 2: District Hospital, Arterial Evacuation Bridge, Drainage Pumping Station} \\ 
0.50 & \text{if } \text{Tier 3: Primary Health Clinic, Relief Shelter High School, Secondary Feeder} \\ 
0.25 & \text{if } \text{Tier 4: Primary Elementary School, Community Center, Market Yard} \\ 
0.05 & \text{if } \text{Tier 5: Administrative Offices, Parks, Decorative Public Spaces} 
\end{cases}$$

### 2.3 Criterion $V$: Vulnerable Population Density ($\phi_V$)
Derived from Phase 6C demographic conservation figures ($N_{\text{GEN}}, N_{\text{ACC}}, N_{\text{MED}}, N_{\text{MED\_ACC}}$) relative to total ward census baseline population $P_{\text{census}}$:
$$\text{Weighted Vulnerability Index } \psi_j = N_{\text{GEN}} + 2.5 \cdot N_{\text{ACC}} + 3.0 \cdot N_{\text{MED}} + 4.5 \cdot N_{\text{MED\_ACC}}$$
$$\phi_V(X_{V, j}) = \min\left(1.0, \; \frac{\psi_j}{\max(100, 0.20 \cdot P_{\text{census}})}\right)$$
- If ward population data is missing, the denominator defaults to the municipal median ward population ($10,000$), and the record is flagged for data gap audit.

### 2.4 Criterion $D$: Dependency Cascade Centrality ($\phi_D$)
Evaluated on the directed project dependency DAG $G = (\mathcal{V}, \mathcal{E})$:
Let $\text{OutDeg}(j) = |\{k \in \mathcal{V} \mid (j, k) \in \mathcal{E}\}|$ be the immediate successor count, and $\text{Cascade}(j) = |\{k \in \mathcal{V} \mid j \rightsquigarrow k\}|$ be the transitive downstream reachable set:
$$\phi_D(X_{D, j}) = \min\left(1.0, \; 0.4 \cdot \frac{\text{OutDeg}(j)}{\max_{i} \text{OutDeg}(i) + 1} + 0.6 \cdot \frac{\text{Cascade}(j)}{\max_{i} \text{Cascade}(i) + 1}\right)$$

### 2.5 Criterion $E$: Economic & Livelihood Restoration ($\phi_E$)
Measures direct livelihood enablement per million INR capital expenditure:
$$X_{E, j} = \frac{\text{Livelihood Households Restored}_j}{\text{Estimated Project Cost (in Lakh INR)}_j}$$
$$\phi_E(X_{E, j}) = \frac{X_{E, j} - X_{E, \min}}{X_{E, \max} - X_{E, \min} + \epsilon}$$
Normalized via linear min-max scaling bounded in $[0.0, 1.0]$.

---

## 3. Weight Constraints & Statutory Bounding Intervals

To prevent arbitrary political distortion while allowing legitimate regional policy adaptation, criteria weights are constrained by statutory optimization bounds:

$$\sum_{k \in \mathcal{K}} w_k = 1.0$$
$$w_k \in [\underline{w}_k, \bar{w}_k] \quad \forall k \in \mathcal{K}$$

| Criterion | Parameter | Default Research Weight | Lower Bound $\underline{w}_k$ | Upper Bound $\bar{w}_k$ | Statutory Rationale |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Life-Safety Urgency** | $w_L$ | **$0.30$** | $0.20$ | $0.45$ | Guarantees life-safety cannot be diluted below 20%. |
| **Infrastructure Criticality** | $w_C$ | **$0.25$** | $0.15$ | $0.35$ | Safeguards essential lifelines over secondary assets. |
| **Vulnerable Populations** | $w_V$ | **$0.20$** | $0.10$ | $0.30$ | Protects equity and marginalized communities. |
| **Dependency Cascade** | $w_D$ | **$0.15$** | $0.05$ | $0.25$ | Ensures bottlenecks are resolved early. |
| **Economic Restoration** | $w_E$ | **$0.10$** | $0.05$ | $0.25$ | Supports economic recovery without overtaking safety. |

---

## 4. Confidence Discounting & Missing Data Treatment

The composite index incorporates survey confidence decay:
$$\Omega_j = \begin{cases} 
1.00 & \text{if assessment freshness is } \text{FRESH } (\mathcal{C} \ge 75\%) \\ 
0.90 & \text{if assessment freshness is } \text{MODERATE } (50\% \le \mathcal{C} < 75\%) \\ 
0.75 & \text{if assessment freshness is } \text{STALE\_AMBER } (25\% \le \mathcal{C} < 50\%) \\ 
0.25 & \text{if assessment freshness is } \text{EXPIRED\_RED } (\mathcal{C} < 25\%) 
\end{cases}$$

- **Missing Criterion Handling**: If an assessment lacks data for criterion $k$, the system **does not impute a zero** (which unjustly penalizes poorly reported remote areas). Instead:
  1. The system assigns the median observed score for that sector across the district: $\phi_k(X_{k, j}) = \text{Median}_{i \in \text{Sector}(j)} \phi_k(X_{k, i})$.
  2. The overall project data confidence is downgraded to `STALE_AMBER` ($\Omega_j = 0.75$).
  3. A mandatory re-inspection task is automatically scheduled.

---

## 5. Deterministic Tie-Breaking & Override Architecture

### 5.1 Deterministic Lexicographic Tie-Breaking
When two candidate projects achieve identical MCPI scores ($|\text{MCPI}_a - \text{MCPI}_b| < 10^{-4}$):
1. **First Tie-Breaker**: Highest normalized Life-Safety Urgency $\phi_L$.
2. **Second Tie-Breaker**: Highest Vulnerable Population Density $\phi_V$.
3. **Third Tie-Breaker**: Highest Transitive Downstream Cascade $\text{Cascade}(j)$.
4. **Fourth Tie-Breaker**: Lowest Estimated Capital Cost $C_j$ (cost-effectiveness).
5. **Final Deterministic Arbiter**: Cryptographic SHA-256 hash of `project_code` (guarantees mathematical determinism across platform restarts).

### 5.2 Human Engineering Override Gate
An authorized Government Engineer (`role = "GOVT"`) may override an MCPI ranking:
- **Permitted Actions**: `ESCALATE_TIER`, `DE_ESCALATE_TIER`, `PIN_TO_PERIOD_1` (Emergency Direct Sanction).
- **Audit Logging**: Any override requires mandatory justification text ($\ge 20$ chars) and logs original score, override score, operator ID, and timestamp to `RecoveryOverrideLog`.

---

## 6. Fully Worked Numerical Synthetic Example

Consider three candidate recovery projects under default baseline weights:

### Data Matrix (Synthetic):

| Project | Description | Sector | Cost (Lakh INR) | $X_L$ (Damage) | $X_C$ (Tier) | Vulnerability Split ($N_{\text{GEN}}, N_{\text{ACC}}, N_{\text{MED}}, N_{\text{MED\_ACC}}$) | Out-Deg / Cascade | Freshness |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$P_A$** | District Trauma Hospital | HEALTH | $120.0$ | $3$ (Severe) | Tier 1 | $(200, 40, 50, 15)$ in Ward pop $15,000$ | $3$ / $6$ | FRESH ($1.0$) |
| **$P_B$** | Commercial Ring Road Bridge | TRANSPORT | $250.0$ | $2$ (Moderate) | Tier 2 | $(50, 5, 2, 0)$ in Ward pop $25,000$ | $5$ / $9$ | FRESH ($1.0$) |
| **$P_C$** | Rural Dalit Settlement Water Main | WASH | $35.0$ | $4$ (Destroyed) | Tier 3 | $(120, 30, 25, 10)$ in Ward pop $4,000$ | $1$ / $2$ | MODERATE ($0.9$) |

### Normalization Calculations:
1. **Life-Safety $\phi_L$**:
   - $P_A$: Severe $\to \phi_L = 0.75$
   - $P_B$: Moderate $\to \phi_L = 0.50$
   - $P_C$: Destroyed $\to \phi_L = 1.00$
2. **Criticality $\phi_C$**:
   - $P_A$: Tier 1 $\to \phi_C = 1.00$
   - $P_B$: Tier 2 $\to \phi_C = 0.75$
   - $P_C$: Tier 3 $\to \phi_C = 0.50$
3. **Vulnerability $\phi_V$**:
   - $P_A$: $\psi_A = 200 + 2.5(40) + 3(50) + 4.5(15) = 200 + 100 + 150 + 67.5 = 517.5$. Cap $= 0.20(15,000) = 3,000$. $\phi_V = 517.5 / 3,000 = 0.1725$.
   - $P_B$: $\psi_B = 50 + 2.5(5) + 3(2) + 0 = 68.5$. Cap $= 0.20(25,000) = 5,000$. $\phi_V = 68.5 / 5,000 = 0.0137$.
   - $P_C$: $\psi_C = 120 + 2.5(30) + 3(25) + 4.5(10) = 120 + 75 + 75 + 45 = 315.0$. Cap $= 0.20(4,000) = 800$. $\phi_V = 315.0 / 800 = 0.3938$.
4. **Dependency $\phi_D$** (assuming $\max \text{OutDeg} = 5, \max \text{Cascade} = 9$):
   - $P_A$: $0.4(3/6) + 0.6(6/10) = 0.20 + 0.36 = 0.560$.
   - $P_B$: $0.4(5/6) + 0.6(9/10) = 0.333 + 0.540 = 0.873$.
   - $P_C$: $0.4(1/6) + 0.6(2/10) = 0.067 + 0.120 = 0.187$.
5. **Economic $\phi_E$**:
   - Let evaluated $\phi_E(P_A) = 0.40, \phi_E(P_B) = 0.90, \phi_E(P_C) = 0.60$.

### Composite Score Evaluation:
$$\text{MCPI}_j = 100 \cdot (0.30 \phi_L + 0.25 \phi_C + 0.20 \phi_V + 0.15 \phi_D + 0.10 \phi_E)$$

- **Project $P_A$ (Trauma Hospital)**:
  $$\text{Raw}_A = 0.30(0.75) + 0.25(1.00) + 0.20(0.1725) + 0.15(0.560) + 0.10(0.40)$$
  $$\text{Raw}_A = 0.2250 + 0.2500 + 0.0345 + 0.0840 + 0.0400 = 0.6335$$
  $$\mathbf{\text{MCPI}_A = 63.35 \quad (\text{Rank 1})}$$
  *(Governance Status: Verified Fresh — Approved for immediate scheduling).*

- **Project $P_B$ (Commercial Bridge)**:
  $$\text{Raw}_B = 0.30(0.50) + 0.25(0.75) + 0.20(0.0137) + 0.15(0.873) + 0.10(0.90)$$
  $$\text{Raw}_B = 0.1500 + 0.1875 + 0.0027 + 0.1310 + 0.0900 = 0.5612$$
  $$\mathbf{\text{MCPI}_B = 56.12 \quad (\text{Rank 3})}$$
  *(Governance Status: Verified Fresh — Eligible for competitive optimization).*

- **Project $P_C$ (Rural Water Main)**:
  $$\text{Raw}_C = 0.30(1.00) + 0.25(0.50) + 0.20(0.3938) + 0.15(0.187) + 0.10(0.60)$$
  $$\text{Raw}_C = 0.3000 + 0.1250 + 0.0788 + 0.0281 + 0.0600 = 0.5919$$
  $$\mathbf{\text{MCPI}_C = 59.19 \quad (\text{Rank 2})}$$
  *(Governance Status: `HOLD_PENDING_FIELD_REINSPECTION` due to MODERATE age; priority score remains unpenalized at $59.19$, ranking ahead of commercial bridge $P_B$. Furthermore, because $X_L = 4$ [Destroyed], Stage 1 Lexicographic Safety Filter elevates $P_C$ to `TIER_1_MANDATORY` due to absolute lifelines necessity).*
