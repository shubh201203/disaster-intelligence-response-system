# DIRS Phase 6D-A — DEF-6D-04: Project Selection & Precedence Proof
## Selection Co-requisites, Big-M Tightness, Reified CP-SAT Formulations, and Worked Verification

**Document ID:** `DIRS-PHASE6D-DOC-17`  
**Classification:** MATHEMATICAL OPTIMIZATION & PROOF AUDIT  
**Lead Authors:** Principal Operations Research Scientist & Mathematical Optimization Engineer  
**Date:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Defect Identification & Structural Correction (DEF-6D-04)

In early project scheduling formulations, precedence between tasks was expressed purely via start times:
$$\sum_{t=1}^T t \cdot x_{j, t} \ge \sum_{t=1}^T t \cdot x_{i, t} + d_i + L_{ij} - M(1 - w_j)$$

**Audit Finding (DEF-6D-04):**
This equation alone allows a catastrophic logical error:
- If a successor project $j$ is highly attractive (high MCPI, low cost), the solver could set $w_j = 1$ and schedule it, while setting $w_i = 0$ (omitting the mandatory predecessor $i$), provided the big-$M$ relaxation is triggered or if $w_i$ is uncoupled from $w_j$!
- In physical reconstruction, **a successor project CANNOT be constructed if its mandatory prerequisite is not constructed**. For example, one cannot pave a bridge deck ($j$) if the bridge pier foundation ($i$) is never built!

**Remediation Mandate:**
For every mandatory directed dependency edge $(i, j) \in \mathcal{E}_{\text{mandatory}}$:
$$w_j \le w_i$$
This fundamental selection constraint guarantees that selecting successor $j$ strictly forces predecessor $i$ to be selected.

---

## 2. Complete Mathematical Formulation of Project Precedence

Let:
- $\mathcal{P} = \{1, \dots, N\}$: Set of candidate recovery projects.
- $\mathcal{E} \subset \mathcal{P} \times \mathcal{P}$: Directed precedence edges $(i, j)$, where project $i$ must finish before project $j$ can start.
- $w_j \in \{0, 1\}$: Binary project selection decision variable.
- $x_{j, t} \in \{0, 1\}$: Binary project start decision variable at discrete period $t \in \{1, \dots, T - d_j + 1\}$.
- $d_j \in \mathbb{Z}^+$: Integer duration of project $j$ in discrete planning periods.
- $L_{ij} \in \mathbb{Z}_{\ge 0}$: Non-negative completion-to-start lag periods between predecessor $i$ and successor $j$.
- $T \in \mathbb{Z}^+$: Global planning horizon length.

### 2.1 The Two Governing Precedence Invariants

For every directed precedence relationship $(i, j) \in \mathcal{E}$:

#### Invariant 1: Mandatory Selection Implication
$$w_j \le w_i$$
- If $w_j = 1 \implies w_i = 1$ (Predecessor MUST be selected).
- If $w_i = 0 \implies w_j = 0$ (If predecessor is unselected, successor is FORBIDDEN).
- If $w_i = 1 \implies w_j \in \{0, 1\}$ (Predecessor may be selected on its own merit without forcing successor).

#### Invariant 2: Discrete Timing Precedence with Lag
Let $S_j = \sum_{t=1}^{T - d_j + 1} t \cdot x_{j, t}$ be the scheduled start period of project $j$.
When both projects are selected ($w_i = 1, w_j = 1$):
$$S_j \ge S_i + d_i + L_{ij}$$

---

## 3. Solver Implementation Pathways: Big-M vs. CP-SAT Reified Constraints

### 3.1 MILP Big-M Formulation and Exact Tightness Proof
In standard Mixed-Integer Linear Programming:
$$\sum_{t=1}^{T - d_j + 1} t \cdot x_{j, t} \ge \sum_{t=1}^{T - d_i + 1} t \cdot x_{i, t} + d_i + L_{ij} - M \cdot (1 - w_j)$$

**Proof of Tight Big-$M$ Constant:**
- When $w_j = 1$: Because $w_j \le w_i$, we also have $w_i = 1$. Both projects have well-defined start periods: $\sum t x_{j, t} = S_j \ge 1$ and $\sum t x_{i, t} = S_i \ge 1$. The term $M(1 - w_j) = 0$, enforcing the exact physical precedence:
  $$S_j \ge S_i + d_i + L_{ij}$$
- When $w_j = 0$: $x_{j, t} = 0 \; \forall t$, so the left-hand side is $0$.
  The maximum possible value of the right-hand side occurs when predecessor $i$ is selected and starts at its latest possible period $t_{\max} = T - d_i + 1$:
  $$\text{RHS}_{\max} = (T - d_i + 1) + d_i + L_{ij} - M = T + 1 + L_{ij} - M$$
  For the constraint $0 \ge \text{RHS}_{\max}$ to be universally satisfied:
  $$M \ge T + L_{ij} + 1$$
- **Exact Tightly Bounded Value:**
  $$M_{ij} = T + L_{ij} + 1$$
  Using $M_{ij}$ instead of an arbitrary large number (e.g. $10^6$) produces the tightest possible convex hull, preventing numerical instability and slow LP-relaxation bounds.

### 3.2 Google OR-Tools CP-SAT Reified Interval Formulation (Preferred)
In Google OR-Tools CP-SAT, interval variables and Boolean reification provide a formulation that completely eliminates big-$M$ relaxations:

```python
# Create optional interval variables for projects
start_var = {}
interval_var = {}
for j in projects:
  start_var[j] = model.NewIntVar(1, T - d[j] + 1, f"start_{j}")
  # Optional interval present only if project is selected (w[j] == 1)
  interval_var[j] = model.NewOptionalIntervalVar(
      start_var[j], d[j], start_var[j] + d[j], w[j], f"interval_{j}"
  )

# Mandatory Precedence Edge (i, j) with lag L_ij
for i, j, L_ij in dependencies:
  # 1. Structural Selection Co-requisite
  model.Add(w[j] <= w[i])

  # 2. Timing Precedence: Enforced if successor is selected
  # (Since w[j] == 1 implies w[i] == 1, both start variables are valid)
  model.Add(start_var[j] >= start_var[i] + d[i] + L_ij).OnlyEnforceIf(w[j])
```
*Advantage:* CP-SAT uses native boolean propagation. If $w_j = 1$, the timing constraint is activated. If $w_j = 0$, the constraint is ignored without any big-$M$ numerical degradation.

---

## 4. Comprehensive Worked Verification Examples

Consider a planning horizon $T = 12$ periods.
Let Predecessor Project $P_1$ have duration $d_1 = 3$ periods.
Let Successor Project $P_2$ have duration $d_2 = 2$ periods.
Let dependency lag $L_{12} = 1$ period (e.g., concrete curing or inspection delay).
Tightly calibrated $M = 12 + 1 + 1 = 14$.

---

### Case 1: Both Projects Selected ($w_1 = 1, w_2 = 1$)
- **Selection Check:** $w_2 \le w_1 \implies 1 \le 1$ (**SATISFIED**).
- **Timing Constraint:**
  $$S_2 \ge S_1 + d_1 + L_{12} - 14(1 - 1) \implies S_2 \ge S_1 + 3 + 1 \implies S_2 \ge S_1 + 4$$
- If Predecessor $P_1$ starts at period $S_1 = 2$:
  - $P_1$ executes during periods $t \in \{2, 3, 4\}$.
  - Earliest completion period of $P_1$ is $t = 4$.
  - Lag period $L_{12} = 1$ occupies period $t = 5$.
  - Successor $P_2$ start must satisfy $S_2 \ge 2 + 3 + 1 = 6$.
  - $P_2$ starts at $S_2 = 6$, executing during periods $t \in \{6, 7\}$.
- **Verification:** Feasible, non-overlapping, physical lag respected.

---

### Case 2: Neither Project Selected ($w_1 = 0, w_2 = 0$)
- **Selection Check:** $w_2 \le w_1 \implies 0 \le 0$ (**SATISFIED**).
- **Timing Constraint:**
  $$0 \ge 0 + 3 + 1 - 14(1 - 0) \implies 0 \ge 4 - 14 \implies 0 \ge -10 \quad (\text{TRUE})$$
- **Verification:** Feasible; neither project consumes resources or executes.

---

### Case 3: Predecessor Selected, Successor Deselected ($w_1 = 1, w_2 = 0$)
- **Selection Check:** $w_2 \le w_1 \implies 0 \le 1$ (**SATISFIED**).
- **Timing Constraint:**
  Let $P_1$ start at period $S_1 = 1$. $w_2 = 0 \implies \sum t x_{2, t} = 0$.
  $$0 \ge 1 + 3 + 1 - 14(1 - 0) \implies 0 \ge 5 - 14 \implies 0 \ge -9 \quad (\text{TRUE})$$
- **Verification:** Feasible; predecessor executes freely without requiring dependent successor to be built.

---

### Case 4: Successor Requested while Predecessor is Unavailable ($w_2 = 1, w_1 = 0$)
- **Selection Check:**
  $$w_2 \le w_1 \implies 1 \le 0 \quad (\mathbf{VIOLATION — INFEASIBLE})$$
- **Verification:** The selection constraint immediately blocks this illegal combination at the root node of branch-and-bound, preventing the solver from ever scheduling $P_2$ without $P_1$.

---

### Case 5: Multiple Predecessors (Fork-and-Join DAG)
Suppose Project $P_3$ ($d_3 = 2$) requires **both** $P_1$ ($d_1 = 3, L_{13} = 1$) and $P_2$ ($d_2 = 4, L_{23} = 0$):
$$\mathcal{E} = \{(1, 3), (2, 3)\}$$

- **Selection Constraints:**
  $$w_3 \le w_1 \quad \text{AND} \quad w_3 \le w_2$$
  If $w_3 = 1$, both $w_1 = 1$ and $w_2 = 1$ are strictly forced.
- **Timing Constraints:**
  $$S_3 \ge S_1 + d_1 + L_{13} = S_1 + 3 + 1 = S_1 + 4$$
  $$S_3 \ge S_2 + d_2 + L_{23} = S_2 + 4 + 0 = S_2 + 4$$
- Let $P_1$ start at $S_1 = 1$ (finishes at $4$, lag to $5 \implies$ ready at $6$).
- Let $P_2$ start at $S_2 = 3$ (finishes at $7$, ready at $7$).
- Successor $P_3$ start constraint:
  $$S_3 \ge \max(1 + 4, \; 3 + 4) = \max(5, 7) = 7$$
  $$S_3 \ge 7$$
- **Verification:** $P_3$ can start at period $7$, waiting for the slower predecessor ($P_2$) to complete. Exact fork-and-join synchronization proven.

---

### Case 6: Dependency with Zero Lag ($L_{12} = 0$)
- $P_1$ ($d_1 = 2$) starts at $S_1 = 4$.
- Finishes at period $t = 5$.
- Timing constraint with $L_{12} = 0$:
  $$S_2 \ge S_1 + d_1 + 0 = 4 + 2 + 0 = 6$$
- $P_2$ can start immediately in period $6$.
- **Verification:** Consecutive contiguous execution without delay.

---
*End of DIRS Phase 6D-A DEF-6D-04 Remediation Document.*
