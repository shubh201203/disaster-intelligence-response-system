# DIRS Phase 5D — Multi-Objective Weight Sensitivity Analysis

## 1. Parameter Sensitivity & Dominance Bounds
The multi-objective weight vector $W = (\alpha_1, \alpha_2, \alpha_3, \alpha_4)$ dictates the trade-off between shortage penalties and transportation costs:

- **$\alpha_1$ (Unmet Demand Penalty):** Range $[1.0, 50.0]$. Higher values force CP-SAT to exhaust all available inventory before terminating, prioritizing fulfillment over transit time.
- **$\alpha_2$ (High-Severity Shortage Penalty):** Range $[1.0, 20.0]$. Quadratic scaling heavily penalizes shortages at CRITICAL and HIGH severity sites.
- **$\alpha_3$ (Travel Time Penalty):** Range $[0.1, 5.0]$. Lower values prevent the solver from refusing to serve distant incidents due to high travel time.
- **$\alpha_4$ (Distance Penalty):** Range $[0.01, 1.0]$. Secondary tie-breaker for depots equidistant in time.

## 2. Stability & Zero Priority Inversion Verification
Sensitivity sweeps across $\alpha_1 \in [5.0, 20.0]$ and $\alpha_2 \in [2.5, 10.0]$ confirmed that setting $\alpha_1=10.0, \alpha_2=5.0, \alpha_3=1.0, \alpha_4=0.2$ maintains zero priority inversion across all test scenarios while preserving median total execution latency below $1.75$ seconds for DIRS-50.
