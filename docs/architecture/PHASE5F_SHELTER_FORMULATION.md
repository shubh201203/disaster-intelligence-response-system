# PHASE 5F-A — Shelter Assignment Optimization Formulation

**System:** Disaster Incident Response System (DIRS)  
**Phase:** 5F-A (Shelter & Volunteer Optimization: Research, Audit & Formulation)  
**Component:** Emergency Shelter Evacuation & Capacity Assignment Engine  
**Classification:** MATHEMATICAL SPECIFICATION & RESEARCH FORMULATION (PRE-IMPLEMENTATION)  
**Date:** 2026-09-22  

---

## 1. Problem Overview

During major disaster events, displaced populations at active incident locations must be rapidly assigned and evacuated to emergency shelters.

The Shelter Assignment problem answers:
> *Given active incidents with displaced populations and demographic requirements, and a network of emergency shelters with differing capacities, amenities, and operational statuses, what evacuation assignment minimizes life-safety risk and evacuation travel time while strictly respecting shelter capacities, road reachability, accessibility requirements, and medical compatibility?*

---

## 2. Mathematical Sets, Indices, and Parameters

### 2.1 Sets & Indices
- $i \in I = \{1, 2, \dots, N_I\}$: Set of active disaster incidents requiring shelter evacuation.
- $s \in S = \{1, 2, \dots, N_S\}$: Set of emergency shelters registered in the disaster response grid.
- $g \in G = \{\text{GEN}, \text{ACC}, \text{MED}, \text{MED\_ACC}\}$: Mutually exclusive demographic categories of evacuees.

### 2.2 Demographic Partitioning & Source Mapping
To mathematically eliminate double counting, the total displaced population $p_i$ at incident $i$ (`Incident.people_affected`) is partitioned into mutually exclusive demographic groups:
1. $p_{i, \text{MED\_ACC}} \in \mathbb{Z}^+$: Evacuees requiring **both** medical aid and physical accessibility.
2. $p_{i, \text{ACC}} \in \mathbb{Z}^+$: Evacuees requiring physical accessibility features only (`vulnerable_count` minus overlap).
3. $p_{i, \text{MED}} \in \mathbb{Z}^+$: Evacuees requiring on-site medical triage/aid only (`injuries` minus overlap).
4. $p_{i, \text{GEN}} \in \mathbb{Z}^+$: General evacuees with standard shelter requirements:
   $$p_{i, \text{GEN}} = p_i - \left( p_{i, \text{MED\_ACC}} + p_{i, \text{ACC}} + p_{i, \text{MED}} \right)$$

*Demographic Partition Invariant:*
$$p_i \equiv \sum_{g \in G} p_{ig} \quad \forall i \in I$$

### 2.3 Priority & Severity Parameters
- $P_i \in [1.0, 100.0]$: Priority score of incident $i$ (`Incident.priority_score`, continuous float).
- $\omega_i \in \{1, 2, 3, 5\}$: Priority multiplier based on `Incident.severity_level`:
  $$\omega_i = \begin{cases} 5 & \text{if } \text{severity} = \text{"CRITICAL"} \\ 3 & \text{if } \text{severity} = \text{"HIGH"} \\ 2 & \text{if } \text{severity} = \text{"MEDIUM"} \\ 1 & \text{if } \text{severity} = \text{"LOW"} \end{cases}$$

### 2.4 Shelter Capacity & Capability Parameters
- $K_s \in \mathbb{Z}^+$: Total design capacity of shelter $s$ (`Shelter.total_capacity`, persons).
- $O_s^{\text{curr}} \in \mathbb{Z}^+$: Pre-existing occupancy at shelter $s$ (`Shelter.current_occupancy`, persons).
- $C_s \in \mathbb{Z}^+$: Effective remaining capacity of shelter $s$ (persons):
  $$C_s = \begin{cases} \max(0, K_s - O_s^{\text{curr}}) & \text{if } \text{status}_s = \text{"OPEN"} \\ 0 & \text{if } \text{status}_s \in \{\text{"FULL"}, \text{"CLOSED"}\} \end{cases}$$
- $A_s \in \{0, 1\}$: Binary indicator if shelter $s$ has verified physical accessibility features (`has_accessibility`).
- $M_s \in \{0, 1\}$: Binary indicator if shelter $s$ has on-site medical aid station (`Shelter.has_medical`).
- $\Omega_{sg} \in \{0, 1\}$: Shelter-to-group capability compatibility matrix:
  $$\Omega_{s, \text{GEN}} = 1 \quad \forall s \in S$$
  $$\Omega_{s, \text{ACC}} = A_s \quad \forall s \in S$$
  $$\Omega_{s, \text{MED}} = M_s \quad \forall s \in S$$
  $$\Omega_{s, \text{MED\_ACC}} = A_s \cdot M_s \quad \forall s \in S$$

### 2.5 Road Network Parameters (Consumed from Phase 5C)
- $t_{is} \in \mathbb{R}^+$: Shortest-path travel time from incident $i$ to shelter $s$ in minutes, from Phase 5C `DistanceTimeMatrix`.
- $d_{is} \in \mathbb{R}^+$: Shortest-path travel distance from incident $i$ to shelter $s$ in kilometers.
- $R_{is} \in \{0, 1\}$: Reachability indicator from Phase 5C ($1$ if path exists and $t_{is} < \text{IMPASSABLE\_THRESHOLD}$, $0$ otherwise).

---

## 3. Decision Variables

Every variable utilized in the constraints and objective is explicitly defined below:

| Variable | Domain | Units | Mathematical Definition | Relationship to Source Data |
|---|---|---|---|---|
| $x_{isg}$ | $\mathbb{Z}^+$ | persons | Number of evacuees of demographic group $g$ from incident $i$ assigned to shelter $s$. | Decision variable for shelter intake. |
| $x_{is}$ | $\mathbb{Z}^+$ | persons | Total evacuees from incident $i$ assigned to shelter $s$: $x_{is} = \sum_{g \in G} x_{isg}$. | Aggregated flow for travel cost. |
| $u_{ig}$ | $\mathbb{Z}^+$ | persons | Unassigned evacuee shortfall of demographic group $g$ at incident $i$. | Unmet demand tracking variable. |
| $u_i$ | $\mathbb{Z}^+$ | persons | Total unassigned evacuees at incident $i$: $u_i = \sum_{g \in G} u_{ig}$. | Total incident shortfall. |
| $y_s$ | $\{0, 1\}$ | binary | Activation indicator variable: $1$ if shelter $s$ hosts $\ge 1$ evacuee, $0$ otherwise. | Facility activation decision. |

---

## 4. Hard Constraints

### 4.1 Shelter Physical Capacity Constraint
Total evacuees assigned across all incidents and all demographic groups cannot exceed remaining capacity:
$$\sum_{i \in I} \sum_{g \in G} x_{isg} \le C_s \cdot y_s \quad \forall s \in S$$
If a shelter is `CLOSED` or `FULL`, $C_s = 0$, guaranteeing zero intake.

### 4.2 Exact Demographic Population Conservation Law
For every incident $i$ and demographic group $g$, every displaced individual must be either assigned to a shelter or accounted for in the explicit unmet variable:
$$\sum_{s \in S} x_{isg} + u_{ig} = p_{ig} \quad \forall i \in I, \forall g \in G$$

Summing across all $g \in G$ recovers total incident population conservation:
$$\sum_{s \in S} x_{is} + u_i = p_i \quad \forall i \in I$$
*Conservation Guarantee:* Zero population leakage, zero phantom evacuees, and zero double counting.

### 4.3 Shelter Capability & Compatibility Constraint
Evacuees of demographic group $g$ can only be assigned to shelters providing the required capability:
$$x_{isg} \le p_{ig} \cdot \Omega_{sg} \quad \forall i \in I, \forall s \in S, \forall g \in G$$
- If shelter $s$ lacks accessibility ($A_s = 0$), then $\Omega_{s, \text{ACC}} = 0$ and $\Omega_{s, \text{MED\_ACC}} = 0$, forcing $x_{is, \text{ACC}} = 0$ and $x_{is, \text{MED\_ACC}} = 0$.
- If shelter $s$ lacks medical aid ($M_s = 0$), then $\Omega_{s, \text{MED}} = 0$ and $\Omega_{s, \text{MED\_ACC}} = 0$, forcing $x_{is, \text{MED}} = 0$ and $x_{is, \text{MED\_ACC}} = 0$.

### 4.4 Road Network Reachability & Blockage Exclusion
If Phase 5C indicates shelter $s$ is unreachable from incident $i$ ($R_{is} = 0$), all assignments are forbidden:
$$x_{isg} \le p_{ig} \cdot R_{is} \quad \forall i \in I, \forall s \in S, \forall g \in G$$

### 4.5 Shelter Activation Reification
$$x_{is} \le C_s \cdot y_s \quad \forall i \in I, \forall s \in S$$
$$y_s \le \sum_{i \in I} x_{is} \quad \forall s \in S$$
Enforces that $y_s = 1 \iff \sum_i x_{is} > 0$.

---

## 5. Operational Feasibility Classification

- **`FULLY_FEASIBLE`**: $\sum_{i \in I} u_i = 0$ (100% of affected populations assigned).
- **`PARTIALLY_FEASIBLE`**: $\sum_{i \in I} u_i > 0$ and $\sum_{i \in I} \sum_{s \in S} x_{is} > 0$ (regional capacity exhausted; shortfalls flagged).
- **`INFEASIBLE`**: $\sum_{i \in I} \sum_{s \in S} x_{is} = 0$ and $\sum_{i \in I} p_i > 0$ (all candidate shelters closed, full, or blocked).
