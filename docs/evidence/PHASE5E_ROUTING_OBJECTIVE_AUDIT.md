# PHASE 5E — Routing Objective Function Scaling Audit

**Benchmark:** DIRS-ROUTE-25 (SYNTHETIC CALIBRATED ROUTING BENCHMARK)  
**Solver Engine:** Google OR-Tools `RoutingModel` (Routing Library 9.15.6755)

---

## 1. Objective Mathematical Formulation

The primary routing optimization objective minimizes a multi-term cost function balancing service-level agreement (SLA) timeliness, emergency response latency, physical travel burden, and fleet activation:

min Z_route = beta_1 * sum(late_minutes_i) + beta_2 * sum(travel_time_v) + beta_3 * sum(distance_v) + beta_4 * sum(u_v)

Where:
- S is the set of serviced incident stops.
- u_v in {0, 1} indicates whether vehicle v is activated.
- late_minutes_i = max(0, arrival_time_i - latest_arrival_min_i).
- Critical incidents receive a 3x multiplier on late arrival penalties and soft upper-bound violation slacks.

---

## 2. Objective Weights and Scaling Audit

All variables in OR-Tools `RoutingModel` operate with integer representation scaled by `ROUTE_SCALE = 100`.

| Parameter | Description | Numerical Value | Scaling | Scaled Parameter | Role in Dispatch |
|---|---|---|---|---|---|
| beta_1 | Late Arrival Penalty | 1000 | x 100 | 100,000 | Dominates solver search; guarantees high SLA compliance |
| beta_2 | Response / Travel Time Cost | 10 | x 100 | 1,000 | Minimizes transit duration for emergency goods |
| beta_3 | Travel Distance Cost | 1 | x 100 | 100 | Discourages circuitous detours |
| beta_4 | Vehicle Activation Cost | 100 | x 100 | 10,000 | Promotes route consolidation while respecting capacity |

### Objective Hierarchy Analysis on DIRS-ROUTE-25 (Empirical Measured)
In the optimal solution for DIRS-ROUTE-25:
- Late Penalty Contribution: 0.0% (0.0 late minutes achieved by OR-Tools)
- Response / Travel Time Contribution: 609.67 * 10 = 6,096.7 (82.7% of active objective)
- Distance Contribution: 472.33 * 1 = 472.33 (6.4% of active objective)
- Vehicle Usage Contribution: 8 * 100 = 800.0 (10.9% of active objective)
- Total Objective: 7,369.03

In contrast, Baseline A incurred 47.86 late minutes (Objective: 56,451.08), and Baseline B incurred 236.94 late minutes (Objective: 245,839.48), demonstrating how beta_1 penalizes delivery dispatch delays beyond requested time windows.
