# DIRS Phase 6D-A — Multi-Period Project Selection & Scheduling Problem (MP-RPSP)

**Document ID:** `DIRS-PHASE6D-DOC-04`  
**Classification:** OPERATIONS RESEARCH & MATHEMATICAL OPTIMIZATION  
**Author:** Principal Operations Research Scientist & Mathematical Optimization Engineer  
**Date:** November 16, 2026  
**Status:** COMPLETE (PHASE 6D-A DESIGN BASELINE)  

---

## 1. Problem Statement & Operational Scope

The Multi-Period Recovery Project Selection and Scheduling Problem (MP-RPSP) addresses the optimal sequencing and funding allocation of capital reconstruction public works across discrete planning periods $t \in \mathcal{T} = \{1, 2, \dots, T\}$.

Unlike classic Project Scheduling (RCPSP) which assumes all projects must be executed, disaster recovery requires **portfolio selection under strict budgetary and logistical bounds**: the total capital demand of all damaged facilities often exceeds available funding envelopes ($C_{\text{total}} \gg \sum B_t$). The optimization engine must simultaneously decide:
1. **Which projects to select** ($w_j \in \{0, 1\}$).
2. **In which period to commence each selected project** ($x_{j, t} \in \{0, 1\}$).
3. **How to respect technical precedence dependencies** ($i \to j$) with minimum lag periods.
4. **How to satisfy periodic capital envelopes, labor crews, and material supply limits**.

---

## 2. Mathematical Formulation

### 2.1 Sets and Indices
- $j \in \mathcal{P} = \{1, 2, \dots, N\}$: Set of candidate recovery projects.
- $t \in \mathcal{T} = \{1, 2, \dots, T\}$: Discrete planning periods (e.g. bi-weekly, monthly, quarterly) up to planning horizon $T$.
- $(i, j) \in \mathcal{E}_{\text{prec}}$: Directed edges representing finish-to-start precedence relations ($i$ must finish before $j$ can begin).
- $r \in \mathcal{R}$: Renewable resources (skilled masonry crews, structural engineers, heavy earth-moving equipment).
- $m \in \mathcal{M}$: Non-renewable or cumulative materials (cement, structural steel, ductile iron piping).
- $d \in \mathcal{D}$: Administrative districts or municipal zones.
- $\mathcal{P}_d \subseteq \mathcal{P}$: Projects located within district $d$.

### 2.2 Parameters
- $d_j \in \mathbb{Z}^+$: Duration of project $j$ expressed as an integer count of planning periods ($d_j \ge 1$).
- $c_{j, \delta} \in \mathbb{R}^+$: Capital cash-flow requirement for project $j$ during its $\delta$-th period of execution ($\delta \in \{1, 2, \dots, d_j\}$).
  - Derived from `RecoveryProject.time_indexed_cost_profile`.
  - Total lump-sum cost: $C_j = \sum_{\delta=1}^{d_j} c_{j, \delta}$.
- $B_t \in \mathbb{R}^+$: Capital expenditure budget limit available in period $t$.
- $u_{j, r} \in \mathbb{R}^+$: Demand for renewable resource $r$ per active execution period of project $j$.
- $R_{r, t} \in \mathbb{R}^+$: Total available capacity of renewable resource $r$ during period $t$.
- $q_{j, m} \in \mathbb{R}^+$: Total cumulative requirement of non-renewable material $m$ for project $j$.
- $M_{m, t} \in \mathbb{R}^+$: Cumulative material availability of material $m$ up to period $t$ (accounting for procurement lead times).
- $b_j = \text{MCPI}_j \in [0.0, 100.0]$: Priority benefit score of project $j$.
- $L_{ij} \in \mathbb{Z}_{\ge 0}$: Finish-to-start lag periods between predecessor $i$ and successor $j$.
- $E_j \in \mathcal{T}$: Earliest allowable start period (release date / procurement lead time boundary).
- $D_j \in \mathcal{T}$: Statutory or target milestone completion period.
- $\gamma \ge 0$: Social time-discount rate per period (e.g., $\gamma = 0.02$).
- $\underline{\theta}_d \in [0.0, 1.0]$: Minimum budget equity fraction guaranteed to district $d$.

### 2.3 Decision Variables
- $x_{j, t} \in \{0, 1\}$: Binary variable $= 1$ if project $j$ starts at the beginning of period $t$, $0$ otherwise.
  - Feasible domain: $t \in [E_j, T - d_j + 1]$.
- $y_{j, t} \in \{0, 1\}$: Binary variable $= 1$ if project $j$ is actively in execution during period $t$, $0$ otherwise.
- $z_{j, t} \in \{0, 1\}$: Binary variable $= 1$ if project $j$ completes at the end of period $t$, $0$ otherwise.
- $w_j \in \{0, 1\}$: Binary portfolio selection variable $= 1$ if project $j$ is completed within horizon $T$, $0$ otherwise.

---

## 3. Objective Function Formulations: Comparison & Selection

Three multi-objective formulations were evaluated:

### 3.1 Option A: Weighted Additive Objective (Selected Baseline)
Maximizes total time-discounted recovery benefit minus delay and unmet critical need penalties:
$$\max Z = \sum_{j \in \mathcal{P}} \sum_{t=E_j}^{T - d_j + 1} \frac{b_j}{(1 + \gamma)^{t - 1}} \cdot x_{j, t} - \sum_{j \in \mathcal{P}} \mu_j \cdot (1 - w_j)$$
Where:
- $\frac{b_j}{(1 + \gamma)^{t - 1}}$ rewards early project commencement (accelerating recovery).
- $\mu_j$ represents the unmet social penalty if project $j$ is rejected ($\mu_j = 0.5 \cdot b_j$).

### 3.2 Option B: Lexicographic (Preemptive) Multi-Objective
1. **Tier 1 (Priority 1)**: Maximize life-safety emergency projects: $\max \sum_{j \in \mathcal{P}_{\text{emergency}}} w_j$.
2. **Tier 2 (Priority 2)**: Minimize critical infrastructure delay: $\min \sum_{j \in \mathcal{P}_{\text{infra}}} \sum_t t \cdot x_{j, t}$.
3. **Tier 3 (Priority 3)**: Maximize general recovery benefit: $\max \sum_{j \in \mathcal{P}} b_j \cdot w_j$.

### 3.3 Option C: $\epsilon$-Constraint Method
Maximizes recovery benefit while constraining total budget and equity bounds as parameterized $\epsilon$-constraints.

**Methodological Conclusion**:
The **Weighted Additive Objective with Lexicographic Safety Pre-Filtering** is selected. It provides the optimal balance of computational tractability in OR-Tools CP-SAT, complete transparency, and strict adherence to non-compensatory life-safety invariants.

---

## 4. Constraint Equations

### 4.1 Single Execution & Portfolio Selection
A project is executed at most once, and only if selected:
$$\sum_{t=E_j}^{T - d_j + 1} x_{j, t} = w_j \le 1 \quad \forall j \in \mathcal{P}$$

### 4.2 Active Execution Linkage
Project $j$ is actively consuming resources in period $t$ if and only if it commenced between $t - d_j + 1$ and $t$:
$$y_{j, t} = \sum_{\tau = \max(E_j, t - d_j + 1)}^{t} x_{j, \tau} \quad \forall j \in \mathcal{P}, \forall t \in \mathcal{T}$$

### 4.3 Multi-Predecessor DAG Precedence with Lag
For every directed edge $(i, j) \in \mathcal{E}_{\text{prec}}$:
1. If project $j$ is selected, predecessor $i$ **must** also be selected:
   $$w_j \le w_i \quad \forall (i, j) \in \mathcal{E}_{\text{prec}}$$
2. The start period of $j$ must succeed the completion of $i$ plus finish-to-start lag $L_{ij}$:
   $$\sum_{t=E_j}^{T - d_j + 1} t \cdot x_{j, t} \ge \sum_{t=E_i}^{T - d_i + 1} (t + d_i - 1 + L_{ij}) \cdot x_{i, t} - M(1 - w_j) \quad \forall (i, j) \in \mathcal{E}_{\text{prec}}$$
   where $M = T + 1$.

### 4.4 Multi-Period Capital Expenditure Envelopes
Total capital disbursed across all active projects in period $t$ cannot exceed the available budget envelope $B_t$:
$$\sum_{j \in \mathcal{P}} \sum_{\tau = \max(E_j, t - d_j + 1)}^{t} c_{j, t - \tau + 1} \cdot x_{j, \tau} \le B_t \quad \forall t \in \mathcal{T}$$

### 4.5 Renewable Workforce & Machinery Limits
In each period $t$, total demand for renewable resource $r$ cannot exceed capacity $R_{r, t}$:
$$\sum_{j \in \mathcal{P}} u_{j, r} \cdot y_{j, t} \le R_{r, t} \quad \forall r \in \mathcal{R}, \forall t \in \mathcal{T}$$

### 4.6 Cumulative Non-Renewable Material Availability
Accounting for procurement lead times, total cumulative material consumed through period $t$ cannot exceed delivered inventory $M_{m, t}$:
$$\sum_{j \in \mathcal{P}} q_{j, m} \cdot \left(\sum_{\tau=E_j}^t x_{j, \tau}\right) \le M_{m, t} \quad \forall m \in \mathcal{M}, \forall t \in \mathcal{T}$$

### 4.7 Geographic & District Equity Floor
Each administrative district $d \in \mathcal{D}$ is guaranteed a minimum fraction $\underline{\theta}_d$ of total expended capital:
$$\sum_{j \in \mathcal{P}_d} C_j \cdot w_j \ge \underline{\theta}_d \cdot \sum_{j \in \mathcal{P}} C_j \cdot w_j \quad \forall d \in \mathcal{D}$$

---

## 5. Mathematical Proof of Constraint Consistency

Let us verify the dimensional and physical consistency of the formulation:
1. **Time Indexing**: In constraint 4.4, when project $j$ starts at $\tau$, its active age at period $t \ge \tau$ is $\delta = t - \tau + 1$. Since $t - d_j + 1 \le \tau \le t$, we have $1 \le \delta \le d_j$. The cost index $c_{j, \delta}$ is always evaluated within its valid domain $\{1, \dots, d_j\}$.
2. **Lag Invariant**: In constraint 4.3, predecessor $i$ completes at period $t_i^{\text{finish}} = \tau_i + d_i - 1$. The earliest start of $j$ is $\tau_j = t_i^{\text{finish}} + 1 + L_{ij} = \tau_i + d_i + L_{ij}$. The inequality $\tau_j \ge \tau_i + d_i - 1 + L_{ij}$ strictly prevents premature initiation.
3. **Carry-Forward Budget Extension**: If unspent funds carry forward to the next period with retention rate $\alpha \in [0.0, 1.0]$, the budget recurrence is:
   $$\tilde{B}_t = B_t + \alpha \cdot (\tilde{B}_{t-1} - \text{Expenditure}_{t-1})$$
   ensuring strict financial conservation without unbounded accumulation.
