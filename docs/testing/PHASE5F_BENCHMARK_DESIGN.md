# PHASE 5F-A — Planned Implementation Benchmark Suite Design

**System:** Disaster Incident Response System (DIRS)  
**Phase:** 5F-A (Shelter & Volunteer Optimization: Research, Audit & Formulation)  
**Classification:** PLANNED IMPLEMENTATION BENCHMARK SPECIFICATION (PRE-IMPLEMENTATION)  
**Date:** 2026-09-22  

---

## 1. Benchmark Suite Objectives

The Phase 5F benchmark suite defines planned, reproducible, and deterministic problem instances to be evaluated once implementation is authorized:
1. **Computational Scalability:** Algorithmic latency across four operational disaster tiers ($N = 10, 25, 50, 100$).
2. **Solution Quality:** Objective value comparison against heuristic baselines.
3. **Solver Stability:** Memory consumption and branch-and-bound behavior in OR-Tools CP-SAT.

> [!IMPORTANT]
> **Pre-Implementation Notice:**
> The tables below describe **planned benchmark configurations and proposed performance targets**. No benchmarks have been executed, and no empirical runtimes or scalability metrics are claimed at this stage.

---

## 2. Planned Implementation Benchmark Tiers

### 2.1 Shelter Assignment Planned Benchmark Tiers

| Benchmark Tier | Incidents ($N_I$) | Shelters ($N_S$) | Total Displaced Population | Total Shelter Capacity | Expected CP-SAT Flow Variables | Proposed Target Latency Budget |
|---|---|---|---|---|---|---|
| **`DIRS-SHELTER-10`** | 10 | 5 | ~1,200 evacuees | 1,800 slots | 200 variables ($|I| \times |S| \times |G|$) | $\le 200\text{ ms}$ (target) |
| **`DIRS-SHELTER-25`** | 25 | 10 | ~3,500 evacuees | 5,000 slots | 1,000 variables | $\le 500\text{ ms}$ (target) |
| **`DIRS-SHELTER-50`** | 50 | 20 | ~8,000 evacuees | 12,000 slots | 4,000 variables | $\le 1,500\text{ ms}$ (target) |
| **`DIRS-SHELTER-100`**| 100 | 50 | ~20,000 evacuees | 28,000 slots | 20,000 variables | $\le 3,000\text{ ms}$ (target) |

### 2.2 Volunteer Assignment Planned Benchmark Tiers

| Benchmark Tier | Incidents ($N_I$) | Volunteers ($N_V$) | Total Task Demands | Active Shifts | Expected Binary Decision Variables | Proposed Target Latency Budget |
|---|---|---|---|---|---|---|
| **`DIRS-VOL-10`** | 10 | 25 | 20 tasks | 1 | 1,000 binary vars | $\le 100\text{ ms}$ (target) |
| **`DIRS-VOL-25`** | 25 | 50 | 50 tasks | 1 | 5,000 binary vars | $\le 300\text{ ms}$ (target) |
| **`DIRS-VOL-50`** | 50 | 100 | 120 tasks | 2 | 40,000 binary vars | $\le 1,200\text{ ms}$ (target) |
| **`DIRS-VOL-100`**| 100 | 250 | 300 tasks | 3 | 300,000 binary vars | $\le 3,500\text{ ms}$ (target) |

---

## 3. Performance Metrics & Timing Decomposition Protocol

To guarantee timing arithmetic transparency and eliminate decomposition discrepancies post-implementation:
Every benchmark run will record:
$$\text{Total Latency} = \text{Matrix Build} + \text{Model Construction} + \text{Solver Search} + \text{Solution Extraction} + \text{Orchestration Overhead}$$

### Required Benchmark Output Metrics (To be populated post-implementation):
- **`latency_min_ms`**, **`latency_median_ms`**, **`latency_p95_ms`**, **`latency_max_ms`** across $\ge 5$ repeated runs.
- **`objective_raw_value`**: Exact double-precision objective value.
- **`fulfillment_rate_pct`**: $\frac{\text{Assigned}}{\text{Total Demand}} \times 100\%$.
- **`critical_fulfillment_rate_pct`**: Fulfillment percentage specifically for `CRITICAL` incidents and life-safety tasks.
- **`mean_transit_time_min`**: Average network travel time for evacuees or responders.
- **`operational_status`**: `FULLY_FEASIBLE`, `PARTIALLY_FEASIBLE`, or `INFEASIBLE`.
