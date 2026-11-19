# DIRS — Capstone Evidence Extraction: Algorithms & Mathematical Optimization
## Module 06: Graph Precedence, CPM-PL, Vulnerability Rescoring & Google OR-Tools CP-SAT

**Document Identifier:** `DIRS-CAPSTONE-EVIDENCE-06`  
**Classification:** OFFICIAL / ACADEMIC CAPSTONE EVIDENCE  
**Degree Programme:** Bachelor of Technology (B.Tech) in Computer Science & Engineering  
**Institution:** VIT-AP University, Andhra Pradesh, India  
**Target Release:** DIRS v6.0 (Enterprise Hardened)  
**Audit Status:** STRICT READ-ONLY FORENSIC EXTRACTION  
**Evidence Sources:** `backend/app/recovery/`, `backend/app/recovery/optimization/recovery_cpsat_solver.py`, `backend/app/recovery/services/`  

---

## 1. Algorithm Domain A: Infrastructure Dependency & Precedence Analysis

- **Implementation File:** `backend/app/recovery/services/project_dependency_service.py`
- **Domain Objective:** Model civil reconstruction projects as a directed acyclic graph (DAG), compute schedule boundaries, identify the Critical Path, and prevent circular dependencies.

### 1.1 Mathematical Graph Formulation
Let $G = (V, E)$ represent the infrastructure precedence graph, where:
- $V = \{p_1, p_2, \dots, p_n\}$ is the set of civil reconstruction project nodes, each having an integer execution duration $d_j \ge 1$.
- $E = \{(p_i, p_j, \delta_{ij})\}$ is the set of directed precedence edges, indicating that project $p_j$ cannot commence until project $p_i$ has finished and an optional lag period $\delta_{ij} \ge 0$ has elapsed:
$$t_j \ge t_i + d_i + \delta_{ij} \quad \forall (p_i, p_j, \delta_{ij}) \in E$$
where $t_j$ is the start period of project $p_j$.

### 1.2 Kahn's Topological Sort & Cycle Detection
To establish a valid construction order, the system applies **Kahn’s Algorithm**:
1. Compute the in-degree $\text{deg}^-(v)$ for every project node $v \in V$.
2. Initialize queue $Q$ with all nodes where $\text{deg}^-(v) = 0$.
3. While $Q$ is not empty:
   - Dequeue node $u$; append $u$ to topological ordering $L$.
   - For each outgoing edge $(u, v) \in E$, decrement $\text{deg}^-(v) \leftarrow \text{deg}^-(v) - 1$.
   - If $\text{deg}^-(v) == 0$, enqueue $v \to Q$.
4. **Cycle Condition:** If $|L| < |V|$, the graph contains one or more circular dependencies.

- **Computational Complexity:** $O(|V| + |E|)$ time and $O(|V|)$ auxiliary space.

### 1.3 Critical Path Method with Project Lag (CPM-PL)
Once the topological order $L$ is established, DIRS computes the exact project boundaries:

#### Forward Pass (Early Bounds)
Traversing $L$ in topological order:
$$ES_j = \begin{cases} 
1 & \text{if } \text{Pred}(j) = \emptyset \\
\max_{i \in \text{Pred}(j)} \left( EF_i + \delta_{ij} \right) & \text{otherwise}
\end{cases}$$
$$EF_j = ES_j + d_j - 1$$
where $ES_j$ is the Early Start period and $EF_j$ is the Early Finish period. The total project horizon is $T_{\max} = \max_{j \in V} (EF_j)$.

#### Backward Pass (Late Bounds)
Traversing $L$ in reverse topological order from $T_{\max}$:
$$LF_i = \begin{cases} 
T_{\max} & \text{if } \text{Succ}(i) = \emptyset \\
\min_{j \in \text{Succ}(i)} \left( LS_j - \delta_{ij} - 1 \right) & \text{otherwise}
\end{cases}$$
$$LS_i = LF_i - d_i + 1$$
where $LF_i$ is the Late Finish period and $LS_i$ is the Late Start period.

#### Float Calculation & Critical Path Invariant
For every project node $j \in V$, the **Total Float** $TF_j$ is defined as:
$$TF_j = LS_j - ES_j = LF_j - EF_j$$
- **Critical Path Definition:** A project node is on the Critical Path if and only if:
$$\text{is\_critical}(j) \iff TF_j == 0$$
- In the frontend precedence visualizer, critical nodes are highlighted with red glowing borders (`#EF4444`), alerting civil defense planners that any delay on these projects will directly delay overall municipal recovery.

### 1.4 Dry-Run Dependency Link Validator
- **API Endpoint:** `POST /api/v1/recovery/dependencies/validate-edge`
- **Behavior:** Accepts a candidate directed edge $(u, v)$ without modifying the database. It constructs an in-memory graph $G' = (V, E \cup \{(u, v)\})$ and executes cycle detection.
- **Output:** Returns `{"is_valid": true, "critical_path_affected": bool}` if acyclic; returns `{"is_valid": false, "cycle_path": ["PRJ-1", "PRJ-3", "PRJ-1"]}` if circular, completely preventing bad data injection.

---

## 2. Algorithm Domain B: Community Recovery Monitoring & Simulation

- **Implementation Files:** `backend/app/recovery/services/community_monitoring_service.py`, `vulnerability_scoring_service.py`, `recovery_simulation_service.py`
- **Domain Objective:** Track multi-sector rehabilitation progress, decay confidence over time, rescore vulnerability, and simulate recovery forward trajectories.

### 2.1 Exponential Confidence Decay Formula
Field assessment data degrades in reliability as time passes without re-inspection:
$$C(\Delta t) = C_0 \cdot \exp(-\lambda \cdot \Delta t)$$
where:
- $C_0 \in [0.0, 1.0]$ is the initial assessor confidence rating.
- $\Delta t = t_{\text{current}} - t_{\text{assessment}}$ is the elapsed time in days.
- $\lambda > 0$ is the sectoral decay rate coefficient (e.g., higher for transient floodwaters, lower for structural concrete damage).
- Verified Invariant: $C(\Delta t) \in [0.0, 1.0]$ monotonically non-increasing.

### 2.2 Vulnerability Rescoring Formulation ($\phi$)
- **API Endpoint:** `POST /api/v1/recovery/monitoring/vulnerability-rescore`
The composite vulnerability score $\phi_w \in [0.0, 1.0]$ for ward $w$ is computed as a normalized weighted multi-criteria index:
$$\phi_w = \sum_{k \in \mathcal{K}} w_k \cdot I_{w,k} \cdot \left( 1 + \alpha \cdot (1 - C_{w,k}) \right)$$
subject to $\sum_k w_k = 1.0$, where:
- $I_{w,k} \in [0.0, 1.0]$ is the normalized sector deficit (Housing destruction, Power outage, Potable water deficit, Healthcare disruption).
- $w_k$ is the policy weight assigned to sector $k$.
- $C_{w,k}$ is the decayed confidence score for observation $k$.
- $\alpha \ge 0$ is the uncertainty penalty factor: unverified or stale data artificially increases the calculated vulnerability risk, incentivizing re-inspection.

### 2.3 What-If Forward Recovery Simulation
- **API Endpoint:** `POST /api/v1/recovery/simulation/what-if`
- **Behavior:** A discrete forward simulation evaluating recovery trajectory over planning periods $t \in [1, H]$ under alternative resource allocation scenarios:
$$R_{w,k}(t+1) = \min\left(100.0, \; R_{w,k}(t) + \beta_k \cdot \min\left(1.0, \frac{\text{AllocatedBudget}_k(t)}{\text{RequiredBudget}_k}\right) \cdot \prod_{m \in \text{Bottlenecks}} \eta_m \right)$$
where $\beta_k$ is the recovery velocity coefficient and $\eta_m \in [0.0, 1.0]$ captures deficit penalties from scarce materials (e.g., concrete shortages or transformer deficits).
- **Invariants:** Guaranteed non-mutating (`is_non_mutating: true`); produces monotonic trajectories under non-negative resource allocations.

---

## 3. Algorithm Domain C: Google OR-Tools CP-SAT Recovery Optimization

- **Implementation Files:** `backend/app/recovery/optimization/recovery_cpsat_solver.py`, `backend/app/recovery/services/solvency_service.py`
- **Domain Objective:** Select and schedule an optimal portfolio of reconstruction projects over a multi-period horizon $T$ under periodic budgetary, material, and precedence constraints.

### 3.1 Mathematical Integer Programming Formulation

#### Decision Variables
- $x_{j,t} \in \{0, 1\}$: Binary variable equal to $1$ if project $j \in J$ starts exactly in period $t \in \{1, \dots, T - d_j + 1\}$, and $0$ otherwise.
- $y_j \in \{0, 1\}$: Binary project selection indicator:
$$y_j = \sum_{t=1}^{T - d_j + 1} x_{j,t} \quad \forall j \in J$$

#### Objective Function
Maximize the total weighted socio-economic recovery impact minus execution delay penalties:
$$\max Z = \sum_{j \in J} W_j \cdot y_j - \sum_{j \in J} \sum_{t=1}^{T - d_j + 1} \left( \rho_j \cdot (t - 1) \cdot x_{j,t} \right)$$
where $W_j > 0$ is the multi-criteria recovery priority score and $\rho_j > 0$ is the urgency delay penalty.

#### Constraints
1. **Uniqueness Constraint:** Each candidate project can be executed at most once:
$$\sum_{t=1}^{T - d_j + 1} x_{j,t} \le 1 \quad \forall j \in J$$

2. **Precedence Constraint with Project Lag:**
If $(i, j, \delta_{ij}) \in E$, project $j$ cannot start until project $i$ completes plus lag $\delta_{ij}$, provided both are selected:
$$t_j \ge t_i + d_i + \delta_{ij} - M \cdot (1 - y_i) - M \cdot (1 - y_j)$$
where $M$ is a sufficiently large integer constant ($M \ge T$). In CP-SAT, this is modeled cleanly using reified interval constraints:
$$\text{NewOptionalIntervalVar}(t_j, d_j, t_j + d_j, y_j)$$

3. **Periodic Monetary Budget Limits (INR):**
In each planning period $\tau \in \{1, \dots, T\}$, the sum of costs of all projects active in period $\tau$ cannot exceed the available periodic budget $B_\tau$:
$$\sum_{j \in J} \sum_{t=\max(1, \tau - d_j + 1)}^{\tau} c_{j, (\tau - t + 1)} \cdot x_{j,t} \le B_\tau \quad \forall \tau \in \{1, \dots, T\}$$
where $c_{j, k}$ is the cost of project $j$ incurred during its $k$-th execution period.

4. **Periodic Civil Capability Unit (CCU) Limits:**
In each planning period $\tau$, the demand for specialized civil engineering units (CCUs) cannot exceed the municipal capacity $M_\tau$:
$$\sum_{j \in J} \sum_{t=\max(1, \tau - d_j + 1)}^{\tau} u_{j, (\tau - t + 1)} \cdot x_{j,t} \le M_\tau \quad \forall \tau \in \{1, \dots, T\}$$

5. **District Equity Constraints:**
For every geographic district $D_k$, at least a minimum fraction $\theta_k$ of baseline priority must be scheduled:
$$\sum_{j \in J_{D_k}} W_j \cdot y_j \ge \theta_k \cdot \sum_{j \in J_{D_k}} W_j$$

### 3.2 Dual-Ledger Solvency Verification & Post-Solve Accounting
DIRS enforces a strict **Dual-Ledger Accounting Principle**:
- **INR Liquidity Ledger:** Evaluated in exact Decimal arithmetic (preserving 2 decimal places as strings) to prevent floating-point rounding errors on billion-rupee budgets.
- **CCU Capacity Ledger:** Evaluated as exact non-negative integers.
- **Post-Solve Reconciliation:** Once CP-SAT yields a candidate solution, `SolvencyService` independently reconstructs cash flows and CCU allocations. If any period violates solvency, the schedule is suppressed with status:
$$\text{POST\_SOLVE\_RECONCILIATION\_FAILED}$$
This guarantees that solver numerical approximations cannot produce an illegal schedule.

### 3.3 4-Tier Infeasibility Diagnostic Core
When a scenario is mathematically unschedulable (e.g. an essential project's cost exceeds the combined horizon budget), CP-SAT returns `INFEASIBLE`. DIRS isolates the root cause using a 4-tier diagnostic pipeline:
1. **Tier 1 (Individual Project Feasibility):** Checks whether single projects exceed cumulative horizon budgets or duration exceeds $T$.
2. **Tier 2 (Precedence Feasibility):** Evaluates whether the CPM-PL critical path length exceeds horizon $T$.
3. **Tier 3 (Periodic Resource Over-Commitment):** Identifies specific periods $\tau$ where baseline mandatory demand exceeds capacity.
4. **Tier 4 (Minimal Unsatisfiable Core / MUC):** Extracts the smallest subset of constraints whose simultaneous enforcement creates infeasibility.

---

## 4. Other Implemented Intelligence & AI Capabilities

- **Grounded RAG Civil Defense Assistant (`backend/app/services/rag/`):** Indexes NDMA standard operating procedures and municipal guidelines in `knowledge_chunks`. When a user submits an emergency question, semantic embeddings retrieve the top matching chunks to generate grounded safety instructions without generative hallucination.
- **PostGIS Spatial Radius Queries (`backend/app/services/gis_service.py`):** Uses `ST_DWithin` spatial indexing on EPSG:4326 geometries to locate emergency shelters within $R$ meters of an incident centroid in $O(\log N)$ time via spatial R-Trees.
