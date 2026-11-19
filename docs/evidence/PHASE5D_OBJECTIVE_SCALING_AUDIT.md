# DIRS Phase 5D — Objective Scaling & Effective Weighting Forensic Audit

## 1. Implemented Objective Function
$$\text{Minimize } Z = \sum_{i \in I} \sum_{r \in R} \left[ \alpha_1 \cdot p_i \cdot s_i + \alpha_2 \cdot \frac{p_i^2}{10} \cdot s_i \right] u_{i,r} + \sum_{d \in D} \sum_{i \in I} \mathbb{I}(M_{d,i}=1) \left[ \alpha_3 \cdot t_{d,i} + \alpha_4 \cdot dist_{d,i} \right] y_{d,i}$$

where $\alpha_1 = 10.0, \alpha_2 = 5.0, \alpha_3 = 1.0, \alpha_4 = 0.2$.

---

## 2. Empirical Objective Breakdown (SCENARIO-5D-B: Severe Scarcity)
| Objective Term | Symbol & Coeff ($\alpha$) | Raw Value | Normalization Factor | Weighted Contribution | % of Total Objective |
|---|---|---|---|---|---|
| **Primary Unmet Cost** | $Z_{\text{unmet}}$ ($\alpha_1 = 10.0$) | $1,402,817.1$ | $1 / \text{SCALE}$ | $14,028,171.0$ | **30.06%** |
| **Quadratic Shortage Penalty** | $Z_{\text{penalty}}$ ($\alpha_2 = 5.0$) | $6,527,024.4$ | $1 / \text{SCALE}$ | $32,635,122.1$ | **69.93%** |
| **Shipment Travel Time** | $Z_{\text{time}}$ ($\alpha_3 = 1.0$) | $2,533.6$ | $1 / \text{SCALE}$ | $2,533.6$ | **0.0054%** |
| **Shipment Distance** | $Z_{\text{distance}}$ ($\alpha_4 = 0.2$) | $2,005.4$ | $1 / \text{SCALE}$ | $401.1$ | **0.0009%** |
| **Total Objective ($Z$)** | — | — | — | **$46,666,227.8$** | **100.00%** |

---

## 3. Effective Weighting & Hierarchy Analysis
- **Scarcity Regime (Supply < Demand):** Shortage penalties ($Z_{\text{unmet}} + Z_{\text{penalty}}$) constitute **99.994%** of the objective function, strictly dominating transportation penalties ($0.006\%$).
- **Unconstrained Regime (Supply > Demand):** When all demands are satisfied ($u_{i,r} = 0$), shortage terms reduce to zero ($Z_{\text{unmet}} = Z_{\text{penalty}} = 0$). The solver transitions smoothly to minimizing travel time and distance ($Z_{\text{time}} + Z_{\text{distance}}$), where travel time contributes **86.3%** and distance contributes **13.7%** to route selection.
- **Integer Scaling:** CP-SAT coefficients are scaled by `INTEGER_SCALE = 1000`. Solved objective value is scaled back: $Z_{\text{continuous}} = Z_{\text{integer}} / 1000.0$.
