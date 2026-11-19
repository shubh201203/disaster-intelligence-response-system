# DIRS Phase 5A — Multi-Objective Optimization Layer Mathematical Formulation

## Executive Summary

This document establishes the formal mathematical model for the Disaster Intelligence and Response System (DIRS) Phase 5 Optimization Layer. The layer simultaneously addresses two core operational problems in post-disaster logistics:
1. **Multi-Commodity Resource & Personnel Allocation**: Distributing food, water, medical supplies, shelter capacity, and rescue personnel from storage depots/shelters to active disaster incidents based on predicted severity and priority scores.
2. **Capacitated Vehicle Routing with Time Windows and Dynamic Blockages (CVRPTW-DB)**: Routing emergency vehicles from depots to disaster incidents across a dynamic road network subject to weight/volume capacities and road blockages.

---

## 1. Decision Variables & Notation

### Sets & Indices
- $I = \{1, 2, \dots, N\}$: Set of active disaster incidents (demand nodes).
- $D = \{1, 2, \dots, M\}$: Set of supply depots / warehouses (supply nodes).
- $S = \{1, 2, \dots, K\}$: Set of emergency shelters.
- $V = \{1, 2, \dots, K_v\}$: Set of available response vehicles.
- $R = \{\text{water}, \text{food}, \text{medical}, \text{shelter\_kit}, \text{personnel}\}$: Set of resource commodities.
- $N_{total} = D \cup I$: Total node set for routing graph.

### Parameters
- $d_{i,r}$: Demanded quantity of resource commodity $r \in R$ at incident $i \in I$ (derived from Phase 3A AI predictor).
- $P_i \in [0, 100]$: Composite priority score of incident $i \in I$ (derived from Phase 3B Priority Engine).
- $S_{i} \in \{\text{LOW}, \text{MEDIUM}, \text{HIGH}, \text{CRITICAL}\}$: Severity level of incident $i \in I$ (derived from Phase 4 Severity ML Model).
- $s_{j,r}$: Stock supply of resource $r \in R$ at depot $j \in D$.
- $C_k^{shelter}$: Bed capacity of shelter $k \in S$.
- $O_k^{shelter}$: Current occupancy of shelter $k \in S$.
- $Q_v^{weight}$: Maximum payload weight capacity ($kg$) of vehicle $v \in V$.
- $Q_v^{vol}$: Maximum payload volume capacity ($m^3$) of vehicle $v \in V$.
- $w_r^{weight}, w_r^{vol}$: Unit weight ($kg$) and unit volume ($m^3$) of commodity $r \in R$.
- $t_{i,j}$: Travel time between node $i$ and node $j$ over the road network graph (computed via NetworkX shortest path with dynamic blockage penalties).
- $dist_{i,j}$: Geographical road network distance ($km$) between node $i$ and node $j$.
- $T_i^{target}$: Required target arrival SLA time window for incident $i \in I$.

### Primary Decision Variables
- $y_{j,i,r} \ge 0$: Quantity of resource $r \in R$ allocated from depot $j \in D$ to incident $i \in I$.
- $x_{m,n,v} \in \{0, 1\}$: Binary variable equal to 1 if vehicle $v \in V$ travels directly from node $m \in N_{total}$ to node $n \in N_{total}$; 0 otherwise.
- $u_{i,v} \ge 0$: Arrival time of vehicle $v \in V$ at incident node $i \in I$.
- $z_{i,k} \ge 0$: Number of evacuees allocated from incident $i \in I$ to shelter $k \in S$.

---

## 2. Multi-Objective Cost Function

The primary objective minimizes total operational cost and distress, formulated as a weighted scalar sum of four component metrics:

$$\min Z = \alpha_1 \cdot Z_{\text{unmet}} + \alpha_2 \cdot Z_{\text{penalty}} + \alpha_3 \cdot Z_{\text{time}} + \alpha_4 \cdot Z_{\text{distance}}$$

Where:

### 1. Unmet Demand Penalty ($Z_{\text{unmet}}$)
Penalizes unfulfilled resource requirements at disaster sites, heavily weighted by incident priority score $P_i$:
$$Z_{\text{unmet}} = \sum_{i \in I} \sum_{r \in R} P_i \cdot \max\left(0, d_{i,r} - \sum_{j \in D} y_{j,i,r}\right)$$

### 2. High-Severity Response Delay ($Z_{\text{penalty}}$)
Penalizes late arrivals past target time windows at high-severity and critical incidents:
$$Z_{\text{penalty}} = \sum_{i \in I} \sum_{v \in V} \left( P_i^2 \cdot \max(0, u_{i,v} - T_i^{target}) \right)$$

### 3. Total Fleet Response Time ($Z_{\text{time}}$)
Minimizes total travel time across all dispatched response vehicles:
$$Z_{\text{time}} = \sum_{m \in N_{total}} \sum_{n \in N_{total}} \sum_{v \in V} t_{m,n} \cdot x_{m,n,v}$$

### 4. Fleet Travel Distance ($Z_{\text{distance}}$)
Minimizes fuel consumption and road congestion by reducing overall travel distance:
$$Z_{\text{distance}} = \sum_{m \in N_{total}} \sum_{n \in N_{total}} \sum_{v \in V} dist_{m,n} \cdot x_{m,n,v}$$

---

## 3. Explicit Formal Metric Definitions

To ensure standardized evaluation and prevent post-hoc metric manipulation, all Phase 5 evaluations will strictly measure performance using these fixed mathematical definitions:

1. **Response Delay**:
   For incident $i \in I$, $\text{ResponseDelay}_i = \max(0, u_i - T_i^{target})$, where $u_i = \min_{v \in V: u_{i,v} > 0} u_{i,v}$ is the actual arrival time of the first assigned vehicle at incident $i$, and $T_i^{target}$ is the required target arrival SLA.
   $$\text{Total Response Delay} = \sum_{i \in I} \text{ResponseDelay}_i \quad (\text{minutes})$$
   $$\text{Mean Response Delay} = \frac{1}{|I|} \sum_{i \in I} \text{ResponseDelay}_i \quad (\text{minutes})$$

2. **SLA Compliance Rate**:
   The percentage of active incidents visited by response vehicles at or before their target SLA arrival time $T_i^{target}$:
   $$\text{SLA Compliance Rate} = \frac{|\{i \in I \mid u_i \le T_i^{target}\}|}{|I|} \times 100\% \quad (\text{Percentage})$$

3. **Total Travel Distance**:
   The cumulative geographical road distance traversed across all dispatched fleet vehicles:
   $$\text{Total Travel Distance} = \sum_{m \in N_{total}} \sum_{n \in N_{total}} \sum_{v \in V} dist_{m,n} \cdot x_{m,n,v} \quad (\text{kilometers})$$

4. **Total Unmet Demand Percentage**:
   The fraction of total demanded resources across all commodities that remain unfulfilled:
   $$\text{Unmet Demand \%} = \frac{\sum_{i \in I} \sum_{r \in R} \max\left(0, d_{i,r} - \sum_{j \in D} y_{j,i,r}\right)}{\sum_{i \in I} \sum_{r \in R} d_{i,r}} \times 100\% \quad (\text{Percentage})$$

5. **Resource Utilization Rate**:
   The percentage of total available depot inventory successfully allocated and dispatched to incidents:
   $$\text{Resource Utilization Rate} = \frac{\sum_{j \in D} \sum_{i \in I} \sum_{r \in R} y_{j,i,r}}{\sum_{j \in D} \sum_{r \in R} s_{j,r}} \times 100\% \quad (\text{Percentage})$$

6. **Optimization Runtime**:
   Total wall-clock execution latency measured from initial service invocation to final route plan return:
   $$\text{Optimization Runtime} = t_{\text{completion}} - t_{\text{invocation}} \quad (\text{milliseconds})$$

---

## 4. Formal Baseline Definitions for Comparative Evaluation

During Phase 5 implementation and verification, the Phase 5 Optimization Engine will be benchmarked against two standardized baseline algorithms. **All three approaches receive identical input datasets** (incidents, resources, vehicles, shelters, road graph, capacities, demand, and priority scores). Only the decision algorithm differs:

- **BASELINE A (Greedy Proximity / Nearest Feasible Resource)**:
  Sequentially assigns each incident to the nearest geographical depot/vehicle with available stock. Does not perform multi-vehicle route optimization, dynamic time-window planning, or global priority balancing.
- **BASELINE B (First-Come-First-Served / FCFS Queue Order)**:
  Fulfills incident demands strictly in chronological order of incident creation timestamp. Allocates resources and dispatches vehicles on a first-in, first-out basis until depot stock or vehicle capacity is exhausted.
- **OPTIMIZED (Phase 5 Engine)**:
  The Phase 5 two-stage multi-objective optimization engine (`NetworkX` graph matrix + `Google OR-Tools CP-SAT` allocation + `OR-Tools Routing` CVRPTW solver) solving the multi-objective cost function $Z$.

---

## 5. Weight Sensitivity Analysis Plan

The scalar objective weights ($\alpha_1, \alpha_2, \alpha_3, \alpha_4$) govern trade-offs between demand fulfillment, response speed, and fuel consumption. Rather than locking arbitrary static weights prior to implementation, Phase 5 will execute a multi-configuration sensitivity study:

### Candidate Weight Configurations `[PROJECTED / EXPERIMENTAL DESIGN]`

| Configuration Name | $\alpha_1$ (Unmet Demand) | $\alpha_2$ (Delay Penalty) | $\alpha_3$ (Response Time) | $\alpha_4$ (Distance) | Primary Operational Rationale |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Config 1: Priority-Heavy** | 15.0 | 10.0 | 1.0 | 0.1 | Maximizes life-safety & high-priority incident SLA compliance |
| **Config 2: Balanced (Baseline)** | 10.0 | 5.0 | 1.0 | 0.2 | Standard balanced operational trade-off |
| **Config 3: Distance-Heavy** | 5.0 | 2.0 | 1.0 | 1.0 | Prioritizes fuel preservation & vehicle endurance |
| **Config 4: Response-Time-Heavy** | 8.0 | 12.0 | 3.0 | 0.1 | Minimizes initial arrival latency for fast-moving disasters |

### Evaluation Protocol
During Phase 5K benchmarking, each configuration will be evaluated across the DIRS-50 benchmark suite. For each run, the system will record:
1. Total Unmet Demand (%)
2. Mean Response Delay (mins)
3. Total Travel Distance (km)
4. SLA Compliance Rate (%)
5. High-Priority Incident Coverage (%)

The final production default weight configuration will be selected based on Pareto efficiency across the test suite and documented with empirical justification.

---

## 6. Hard Operational Constraints & Soft Relaxations

### Hard Operational Constraints
- **Depot Inventory Bounds**: $\sum_{i \in I} y_{j,i,r} \le s_{j,r}, \quad \forall j \in D, \forall r \in R$
- **Vehicle Weight & Volume Bounds**: $\sum_{i \in I} \sum_{r \in R} w_r^{weight} \cdot y_{j,i,r,v} \le Q_v^{weight}$ and $\sum_{i \in I} \sum_{r \in R} w_r^{vol} \cdot y_{j,i,r,v} \le Q_v^{vol}, \quad \forall v \in V$
- **Shelter Capacity Bounds**: $\sum_{i \in I} z_{i,k} \le C_k^{shelter} - O_k^{shelter}, \quad \forall k \in S$
- **Dynamic Road Blockage Non-Traversal**: $x_{m,n,v} = 0, \quad \forall (m,n) \in \text{Blockages}, \forall v \in V$

### Soft Relaxations
- **Demand Slack Variables ($\xi_{i,r} \ge 0$)**: Prevents solver infeasibility when total demand exceeds available inventory, while triggering automated alerts in the Government Command Center dashboard.
