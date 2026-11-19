# DIRS Phase 6D-A — Project Dependency DAG & Critical Path Method Architecture

**Document ID:** `DIRS-PHASE6D-DOC-06`  
**Classification:** OPERATIONS RESEARCH & GRAPH ALGORITHMS  
**Author:** Principal Operations Research Scientist & Geospatial Graph Architect  
**Date:** November 16, 2026  
**Status:** COMPLETE (PHASE 6D-A DESIGN BASELINE)  

---

## 1. Executive Summary

Disaster reconstruction involves complex physical and functional interdependencies: roads must be cleared before bridge reconstruction cranes can arrive; electrical transmission lines must be re-energized before water pumping stations can pressurize distribution mains.

This document specifies the graph architecture, cycle detection, Critical Path Method with Precedence Lags (CPM-PL), and failure cascade propagation governing Phase 6D.

---

## 2. Infrastructure Dependency DAG Architecture

Let $G = (\mathcal{V}, \mathcal{E})$ be the recovery dependency graph where:
- $\mathcal{V} = \mathcal{P}$: Nodes represent approved candidate recovery projects.
- $\mathcal{E} \subseteq \mathcal{V} \times \mathcal{V}$: Directed edges $(i, j)$ represent precedence relations where project $i$ is a mandatory predecessor of project $j$.
- Each edge $(i, j)$ carries attributes:
  - $\text{type} \in \{\text{FINISH\_TO\_START}, \text{START\_TO\_START}, \text{FINISH\_TO\_FINISH}\}$.
  - $L_{ij} \in \mathbb{Z}_{\ge 0}$: Precedence lag measured in discrete planning periods.
  - $\text{category} \in \{\text{HARD\_PHYSICAL}, \text{REGULATORY}, \text{POLICY\_PREFERENCE}\}$.

```mermaid
graph TD
    P1["P1: Access Road Debris Clearance<br>Duration: 1 period"] -->|Finish-to-Start (Lag=0)| P2["P2: Power Substation 33kV Repair<br>Duration: 2 periods"]
    P1 -->|Finish-to-Start (Lag=0)| P4["P4: Water Treatment Intake Main<br>Duration: 1 period"]
    P2 -->|Finish-to-Start (Lag=1)| P3["P3: Regional Trauma Hospital<br>Duration: 2 periods"]
    P4 -->|Finish-to-Start (Lag=0)| P3
    P2 -->|Finish-to-Start (Lag=0)| P5["P5: Industrial Feeder<br>Duration: 1 period"]
```

### 2.1 Technical Dependencies vs. Policy Preferences
To prevent solver over-constraining:
1. **Mandatory Technical Dependencies (`HARD_PHYSICAL`)**:
   Physical impossibilities (e.g. constructing a bridge deck before its piers exist, or operating a hospital without electricity). These enter the optimization formulation as hard mathematical constraints.
2. **Policy / Preference Dependencies (`POLICY_PREFERENCE`)**:
   Discretionary sequencing (e.g. repairing government offices before community centers). These are modeled as soft constraints or objective penalty terms, allowing the solver to trade them off against budget feasibility.

---

## 3. Cycle Detection & Graph Validation (Kahn's Algorithm)

To guarantee that $G$ is a Directed Acyclic Graph (DAG), every proposed dependency edge $(u, v)$ is validated via Kahn's Topological Sort algorithm:

### 3.1 Algorithm Specification
```python
def validate_dag_and_detect_cycles(
    nodes: List[str], edges: List[Tuple[str, str]]
) -> Tuple[bool, List[str], Optional[List[str]]]:
  """Executes Kahn's algorithm to detect cycles in infrastructure dependency networks.

  Returns (is_valid_dag, topological_order, cycle_nodes_if_any).
  """
  in_degree = {n: 0 for n in nodes}
  adj = {n: [] for n in nodes}

  for u, v in edges:
    if u == v:
      return False, [], [u]  # Self-loop detected
    adj[u].append(v)
    in_degree[v] += 1

  queue = [n for n, deg in in_degree.items() if deg == 0]
  topo_order = []

  while queue:
    curr = queue.pop(0)
    topo_order.append(curr)
    for neighbor in adj[curr]:
      in_degree[neighbor] -= 1
      if in_degree[neighbor] == 0:
        queue.append(neighbor)

  if len(topo_order) == len(nodes):
    return True, topo_order, None  # Valid DAG
  else:
    # Cycle exists! Extract nodes participating in cycle
    cycle_nodes = [n for n, deg in in_degree.items() if deg > 0]
    return False, [], cycle_nodes
```

### 3.2 Error Codes & Invariant Checks
1. `ERR_SELF_LOOP`: $u == v$.
2. `ERR_NODE_NOT_FOUND`: $u \notin \mathcal{V} \lor v \notin \mathcal{V}$.
3. `ERR_NEGATIVE_LAG`: $L_{uv} < 0$.
4. `ERR_DUPLICATE_EDGE`: Edge $(u, v)$ already exists.
5. `ERR_CYCLIC_DEPENDENCY`: Proposed edge completes a directed cycle.

---

## 4. Critical Path Method with Precedence Lags (CPM-PL)

Disaster recovery project graphs frequently contain disconnected components (e.g. independent rural vs coastal project clusters). Traditional CPM fails when multiple start or end nodes exist. Phase 6D resolves this via **Virtual Source & Terminal Augmentation**:

### 4.1 Augmented Network Formulation
1. Add virtual source $S_0$ with duration $D(S_0) = 0$. For all $v \in \mathcal{V}$ with $\text{in\_degree}(v) = 0$, add edge $(S_0, v)$ with $L = 0$.
2. Add virtual terminal $T_*$ with duration $D(T_*) = 0$. For all $u \in \mathcal{V}$ with $\text{out\_degree}(u) = 0$, add edge $(u, T_*)$ with $L = 0$.

### 4.2 Forward Pass (Earliest Times)
$$\text{ES}(S_0) = 0, \quad \text{EF}(S_0) = 0$$
$$\text{ES}_j = \max_{i \in \text{Pred}(j)} \left(\text{EF}_i + L_{ij}\right) \quad \forall j \in \mathcal{V} \cup \{T_*\}$$
$$\text{EF}_j = \text{ES}_j + d_j$$
Total Project Makespan: $T_{\max} = \text{EF}(T_*)$.

### 4.3 Backward Pass (Latest Times)
$$\text{LF}(T_*) = T_{\max}, \quad \text{LS}(T_*) = T_{\max}$$
$$\text{LF}_i = \min_{j \in \text{Succ}(i)} \left(\text{LS}_j - L_{ij}\right) \quad \forall i \in \mathcal{V} \cup \{S_0\}$$
$$\text{LS}_i = \text{LF}_i - d_i$$

### 4.4 Float / Slack & Critical Path Extraction
- **Total Float**: $\text{TF}_j = \text{LS}_j - \text{ES}_j = \text{LF}_j - \text{EF}_j$.
- **Free Float**: $\text{FF}_j = \min_{k \in \text{Succ}(j)} (\text{ES}_k - L_{jk}) - \text{EF}_j$.
- **Critical Path Nodes**: $\mathcal{V}_{\text{crit}} = \{j \in \mathcal{V} \mid \text{TF}_j = 0\}$.

---

## 5. Fully Worked Synthetic CPM-PL Example

Consider a 5-project recovery cluster:

### Project Parameters:
- $P_1$ (Road Clearing): $d_1 = 1$, Pred: none
- $P_2$ (Power Substation): $d_2 = 2$, Pred: $P_1$ ($L = 0$)
- $P_3$ (Trauma Hospital): $d_3 = 2$, Pred: $P_2$ ($L = 1$), $P_4$ ($L = 0$)
- $P_4$ (Water Intake): $d_4 = 1$, Pred: $P_1$ ($L = 0$)
- $P_5$ (Industrial Feeder): $d_5 = 1$, Pred: $P_2$ ($L = 0$)

### Step-by-Step CPM Calculations:

#### 1. Forward Pass:
- $P_1$: $\text{ES}_1 = 0 \implies \text{EF}_1 = 0 + 1 = 1$.
- $P_2$: $\text{ES}_2 = \text{EF}_1 + 0 = 1 \implies \text{EF}_2 = 1 + 2 = 3$.
- $P_4$: $\text{ES}_4 = \text{EF}_1 + 0 = 1 \implies \text{EF}_4 = 1 + 1 = 2$.
- $P_3$: Multiple predecessors ($P_2, P_4$):
  $$\text{ES}_3 = \max(\text{EF}_2 + 1, \; \text{EF}_4 + 0) = \max(3 + 1, \; 2 + 0) = \max(4, 2) = 4$$
  $$\text{EF}_3 = 4 + 2 = 6$$
- $P_5$: $\text{ES}_5 = \text{EF}_2 + 0 = 3 \implies \text{EF}_5 = 3 + 1 = 4$.
- Makespan: $T_{\max} = \max(\text{EF}_3, \text{EF}_5) = \max(6, 4) = 6\text{ periods}$.

#### 2. Backward Pass:
- $T_*$: $\text{LF} = 6$.
- $P_3$: $\text{LF}_3 = 6 \implies \text{LS}_3 = 6 - 2 = 4$.
- $P_5$: $\text{LF}_5 = 6 \implies \text{LS}_5 = 6 - 1 = 5$.
- $P_2$: Multiple successors ($P_3$ with $L=1$, $P_5$ with $L=0$):
  $$\text{LF}_2 = \min(\text{LS}_3 - 1, \; \text{LS}_5 - 0) = \min(4 - 1, \; 5 - 0) = \min(3, 5) = 3$$
  $$\text{LS}_2 = 3 - 2 = 1$$
- $P_4$: $\text{LF}_4 = \text{LS}_3 - 0 = 4 \implies \text{LS}_4 = 4 - 1 = 3$.
- $P_1$: Multiple successors ($P_2, P_4$):
  $$\text{LF}_1 = \min(\text{LS}_2 - 0, \; \text{LS}_4 - 0) = \min(1 - 0, \; 3 - 0) = \min(1, 3) = 1$$
  $$\text{LS}_1 = 1 - 1 = 0$$

### CPM Table & Critical Path Schedule:

| Project | Duration $d$ | Predecessors (Lag) | Early Start ($\text{ES}$) | Early Finish ($\text{EF}$) | Late Start ($\text{LS}$) | Late Finish ($\text{LF}$) | Total Float ($\text{TF}$) | Free Float ($\text{FF}$) | Critical Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$P_1$** | $1$ | None | **$0$** | **$1$** | **$0$** | **$1$** | **$0$** | $0$ | **CRITICAL** |
| **$P_2$** | $2$ | $P_1$ ($0$) | **$1$** | **$3$** | **$1$** | **$3$** | **$0$** | $0$ | **CRITICAL** |
| **$P_3$** | $2$ | $P_2$ ($1$), $P_4$ ($0$) | **$4$** | **$6$** | **$4$** | **$6$** | **$0$** | $0$ | **CRITICAL** |
| **$P_4$** | $1$ | $P_1$ ($0$) | $1$ | $2$ | $3$ | $4$ | $2$ | $2$ | Non-Critical |
| **$P_5$** | $1$ | $P_2$ ($0$) | $3$ | $4$ | $5$ | $6$ | $2$ | $2$ | Non-Critical |

**Critical Path**: $\mathbf{P_1 \longrightarrow P_2 \overset{L=1}{\longrightarrow} P_3}$ (Makespan = 6 periods).

---

## 6. Failure Cascade Propagation Model

When an unexpected event (aftershock, contractor default, labor strike) delays project $i$ by $\Delta d_i$:
1. If $\Delta d_i \le \text{TF}_i$, the delay is absorbed by project slack; downstream milestones are unaffected.
2. If $\Delta d_i > \text{TF}_i$, the project becomes critical, pushing out the total makespan by $\Delta d_i - \text{TF}_i$.
3. **Downstream Recursive Shift**:
   $$\text{ES}_k^{\text{new}} = \max\left(\text{ES}_k^{\text{old}}, \; \text{EF}_i^{\text{new}} + L_{ik}\right) \quad \forall k \in \text{Reachable}(i)$$
   The system emits an automated cascade warning identifying all downstream public works affected by the slip.
