# PHASE 5F-A — Volunteer Assignment Optimization Formulation

**System:** Disaster Incident Response System (DIRS)  
**Phase:** 5F-A (Shelter & Volunteer Optimization: Research, Audit & Formulation)  
**Component:** Emergency Volunteer & First-Responder Dispatch Engine  
**Classification:** MATHEMATICAL SPECIFICATION & RESEARCH FORMULATION (PRE-IMPLEMENTATION)  
**Date:** 2026-09-22  

---

## 1. Problem Overview

During emergency response operations, citizen volunteers and NGO personnel with specialized competencies (first aid, swift-water rescue, logistics, general relief) mobilize to support ground response.

The Volunteer Assignment problem answers:
> *Given active disaster incidents requiring specific responder skills, and a pool of registered, verified volunteers with varying locations, competencies, and availability, what assignment matches qualified personnel to urgent incident tasks that minimizes response delay and unfilled critical needs while strictly preventing overwork, double-booking, and skill mismatches?*

---

## 2. Mathematical Sets, Indices, and Parameters

### 2.1 Sets & Indices
- $v \in V = \{1, 2, \dots, N_V\}$: Set of registered volunteers (`User` where `role == UserRole.VOLUNTEER`).
- $i \in I = \{1, 2, \dots, N_I\}$: Set of active disaster incidents requiring field personnel.
- $k \in K = \{\text{MEDICAL}, \text{RESCUE}, \text{LOGISTICS}, \text{GENERAL}\}$: Set of standardized skill categories.
- $t \in T$: Set of operational shifts (e.g., $T = \{\text{SHIFT\_1}\}$ for immediate dispatch, or $T = \{1, 2, 3\}$ for 24-hour cycle).

### 2.2 Volunteer Attributes & Capabilities
- $S_{vk} \in \{0, 1\}$: Binary skill qualification matrix ($1$ if volunteer $v$ possesses verified competency in category $k$).
  - For $k = \text{MEDICAL}$, strictly requires `VolunteerProfile.medical_certified == True` or verified medical credentials.
  - For $k = \text{RESCUE}$, strictly requires documented rescue skills.
- $E_v \in \{0, 1\}$: Verification status indicator:
  $$E_v = \begin{cases} 1 & \text{if } \text{VolunteerProfile.verification\_status} = \text{"VERIFIED"} \\ 0 & \text{otherwise (PENDING, REJECTED)} \end{cases}$$
- $A_{vt} \in \{0, 1\}$: Availability indicator ($1$ if volunteer $v$ is marked available for shift $t$, with `is_available == True`).
- $W_v^{\max} \in \mathbb{R}^+$: Maximum allowable active duty hours for volunteer $v$ per shift (hours, default: $8.0\text{ h}$).
- $\tau_v^{\max} \in \mathbb{R}^+$: Maximum acceptable transit time from volunteer's location to assignment site (minutes, default: $45.0\text{ min}$).

### 2.3 Incident Task Demand Parameters
- $d_{ikt} \in \mathbb{Z}^+$: Number of responders with skill $k$ required at incident $i$ during shift $t$ (tasks/persons).
- $h_{ikt} \in \mathbb{R}^+$: Duration of the assigned mission in hours (default: $4.0\text{ to } 8.0\text{ h}$).
- $P_i \in [1.0, 100.0]$: Incident priority score (`Incident.priority_score`, float).
- $\omega_i \in \{1, 2, 3, 5\}$: Severity multiplier based on `Incident.severity_level`:
  $$\omega_i = \begin{cases} 5 & \text{if } \text{severity} = \text{"CRITICAL"} \\ 3 & \text{if } \text{severity} = \text{"HIGH"} \\ 2 & \text{if } \text{severity} = \text{"MEDIUM"} \\ 1 & \text{if } \text{severity} = \text{"LOW"} \end{cases}$$

### 2.4 Network Transit Parameters (Consumed from Phase 5C)
- $\tau_{vi} \in \mathbb{R}^+$: Shortest-path travel time from volunteer's location to incident $i$ in minutes, computed via Phase 5C `RoadGraphEngine`.
- $\delta_{vi} \in \mathbb{R}^+$: Shortest-path travel distance from volunteer $v$ to incident $i$ in kilometers.
- $R_{vi} \in \{0, 1\}$: Reachability indicator from Phase 5C ($1$ if network path exists and $\tau_{vi} < \text{IMPASSABLE\_THRESHOLD}$, $0$ otherwise).

---

## 3. Decision Variables

Every variable utilized in the formulation and objective is explicitly documented below:

| Variable | Domain | Units | Mathematical Definition | Relationship to Source Data |
|---|---|---|---|---|
| $y_{vikt}$ | $\{0, 1\}$ | binary | Assignment indicator: $1$ if volunteer $v$ is assigned to task of skill $k$ at incident $i$ during shift $t$, $0$ otherwise. | Primary dispatch decision. |
| $u_{ikt}$ | $\mathbb{Z}^+$ | tasks | Shortfall count of unfilled responder demands for skill $k$ at incident $i$ in shift $t$. | Unfilled task tracking variable. |
| $z_{vt}$ | $\{0, 1\}$ | binary | Deployment indicator: $1$ if volunteer $v$ is mobilized for any task during shift $t$, $0$ otherwise. | Volunteer activation decision. |

---

## 4. Hard Constraints

### 4.1 Skill Eligibility & Verification Enforcement
An unverified or unqualified volunteer cannot be assigned to a task requiring specialized skill $k$:
$$y_{vikt} \le S_{vk} \cdot E_v \quad \forall v \in V, \forall i \in I, \forall k \in K, \forall t \in T$$
If $S_{vk} = 0$ or $E_v = 0$, $y_{vikt} = 0$ is enforced as a hard structural constraint.

### 4.2 Shift Availability Enforcement
Volunteers can only be assigned during shifts when they are confirmed available:
$$y_{vikt} \le A_{vt} \quad \forall v \in V, \forall i \in I, \forall k \in K, \forall t \in T$$

### 4.3 Mutual Exclusivity (No Double-Booking Across Incidents)
A volunteer can be deployed to at most **one** incident task during any given operational shift $t$:
$$\sum_{i \in I} \sum_{k \in K} y_{vikt} \le 1 \quad \forall v \in V, \forall t \in T$$

### 4.4 Reachability and Maximum Transit Feasibility
Volunteers cannot be dispatched across impassable or disconnected road networks, nor to incidents exceeding their maximum transit window $\tau_v^{\max}$:
$$y_{vikt} \le R_{vi} \quad \forall v \in V, \forall i \in I, \forall k \in K, \forall t \in T$$
$$y_{vikt} = 0 \quad \text{if } \tau_{vi} > \tau_v^{\max}$$

### 4.5 Workload Ceiling Constraint
The total mission hours deployed by volunteer $v$ cannot exceed their maximum allowable shift workload:
$$\sum_{i \in I} \sum_{k \in K} h_{ikt} \cdot y_{vikt} \le W_v^{\max} \quad \forall v \in V, \forall t \in T$$

### 4.6 Exact Task Demand Conservation Law
For every incident $i$, skill category $k$, and shift $t$, the sum of assigned qualified volunteers plus explicit unfilled demand exactly equals total task demand:
$$\sum_{v \in V} y_{vikt} + u_{ikt} = d_{ikt} \quad \forall i \in I, \forall k \in K, \forall t \in T$$
*Conservation Guarantee:* Every required responder position is strictly accounted for. Unfilled tasks are explicitly quantified for mutual-aid escalations.

### 4.7 Volunteer Deployment Reification
$$y_{vikt} \le z_{vt} \quad \forall i \in I, \forall k \in K$$
$$z_{vt} \le \sum_{i \in I} \sum_{k \in K} y_{vikt} \quad \forall v \in V, \forall t \in T$$
Enforces that $z_{vt} = 1 \iff \sum_{i, k} y_{vikt} > 0$.

---

## 5. Operational Feasibility Classification

- **`FULLY_FEASIBLE`**: $\sum_{i, k, t} u_{ikt} = 0$ (100% of required volunteer roles filled by qualified personnel).
- **`PARTIALLY_FEASIBLE`**: $\sum_{i, k, t} u_{ikt} > 0$ and $\sum_{v, i, k, t} y_{vikt} > 0$ (some tasks unfilled due to volunteer scarcity or skill gaps).
- **`INFEASIBLE`**: $\sum_{v, i, k, t} y_{vikt} = 0$ and $\sum_{i, k, t} d_{ikt} > 0$ (zero qualified, available, or reachable volunteers found).
