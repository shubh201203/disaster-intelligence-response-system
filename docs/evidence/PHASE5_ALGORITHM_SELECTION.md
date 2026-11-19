# DIRS Phase 5A — Optimization Solver & Algorithm Selection Trade-off Analysis

## Executive Summary

To select the optimal algorithmic stack for the DIRS Phase 5 Optimization Layer, a comparative design evaluation was performed across three solver paradigms: Pure Mixed-Integer Linear Programming (MILP), Constraint Programming & Vehicle Routing Metaheuristics (Google OR-Tools), and Pure Graph Traversal Algorithms (NetworkX Dijkstra/A*). 

The evaluation targets real-time operational response requirements under disaster conditions: solving dynamic allocation and vehicle routing for 50 active incidents, 10 supply depots, and 25 fleet vehicles within a **target execution latency budget of <2.0 seconds (`TARGET`)**.

---

## 1. Algorithmic Stack Comparative Evaluation Matrix

*Note: All latency figures below represent theoretical complexity estimates and published solver benchmarks (`PROJECTED`). Empirical execution times for DIRS will be measured and reported after Phase 5 implementation.*

| Technical Metric / Feature | Pure MILP (`PuLP` + `CBC` / `SciPy`) | Google OR-Tools (`CP-SAT` & `Routing Engine`) | Graph Pathfinding (`NetworkX` Dijkstra / A*) |
| :--- | :--- | :--- | :--- |
| **Solving Paradigm** | Simplex / Branch-and-Bound | Constraint Programming + Guided Local Search | Graph Search / Shortest Path |
| **Estimated Latency ($N=50$ nodes)** `[PROJECTED]` | Slow ($5.2\text{s} - 45.0\text{s}$ depending on tightness) | **Target: $<1.5\text{s}$ (`TARGET`)** | **Instant ($<50\text{ms}$ matrix build)** |
| **Multi-Commodity Allocation** | Native (Linear constraints) | Native (Integer domain constraints) | N/A (Cannot model resource capacities) |
| **Capacitated VRP with Time Windows** | Complex Formulation (Exploding $x_{i,j,v}$ variables) | **Native First-Class Support (`RoutingModel`)** | Non-trivial (Requires custom heuristic wrappers) |
| **Dynamic Road Blockage Penalty** | High complexity matrix rebuilding | **Dynamic Matrix & Cost Evaluators** | **Native Edge Weight Updating** |
| **Soft Constraint / Slack Flexibility** | Moderate (Requires explicit penalty terms) | **High (Soft lower/upper bounds & Disjunctions)** | Low |
| **Python Ecosystem Integration** | Pure Python wrapper over C++ solver | High-performance C++ bindings (`ortools`) | Pure Python / `scipy.sparse` |
| **Licensing & Dependencies** | MIT / EPL (`CBC`) | **Apache 2.0 (Google Open Source)** | BSD 3-Clause |
| **Architecture Recommendation** | Secondary Baseline | **Primary Optimization Engine** | **Primary Graph Distance Matrix Engine** |

---

## 2. Comprehensive Trade-off Analysis

### 2.1 Pure Mixed-Integer Linear Programming (MILP via `PuLP` / `CBC`)
- **Strengths**: Guarantees global optimality when exact solutions exist; mathematical formulations match textbook LP models directly.
- **Weaknesses**: Combinatorial explosion on Vehicle Routing Problem (CVRPTW) formulations. For $N=50$ nodes and $K_v=25$ vehicles, binary decision variables exceed $50 \times 50 \times 25 = 62,500$ variables, causing branch-and-bound solver latency to spike significantly.

### 2.2 Google OR-Tools (`CP-SAT` & `Routing Engine`)
- **Strengths**: Built explicitly for large-scale Vehicle Routing Problems (VRP) and Constraint Satisfaction Problems (CSP). Features Guided Local Search (GLS) and Tabu Search metaheuristics capable of finding near-optimal ($<2.0\%$ optimality gap `[TARGET]`) solutions rapidly. Supports multi-depot routing, time windows, capacity dimension accumulators, and unvisited node drop penalties out-of-the-box.
- **Weaknesses**: Requires converting continuous floats into scaled integer domains (e.g. multiplying priority scores or weights by $1,000$).

### 2.3 Graph Pathfinding (`NetworkX` Dijkstra / A*)
- **Strengths**: Extremely efficient at updating road graph edge weights dynamically when new `RoadBlockage` records are ingested.
- **Weaknesses**: Incapable of solving combinatorial resource allocation or vehicle routing problems on its own.

---

## 3. Selected Architecture: Hybrid Two-Stage Solver Stack

DIRS Phase 5 selects a **Decoupled Two-Stage Optimization Architecture**:

```
[Phase 3A/3B/4 AI Predictions] 
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 1: Graph Distance & Time Matrix Engine           │
│ (NetworkX / SciPy Spatial + PostGIS Spatial Geometries) │
│ - Computes nxn distance/time matrix                     │
│ - Ingests dynamic RoadBlockages and applies penalties  │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 2A: Resource Allocation Solver                    │
│ (Google OR-Tools CP-SAT)                                │
│ - Solves multi-commodity depot-to-incident allocation   │
│ - Determines optimal resource quantities (food, water)  │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 2B: Dynamic CVRPTW Routing Engine                 │
│ (Google OR-Tools Routing Library)                       │
│ - Assigns allocated resources to vehicle fleet         │
│ - Computes optimal vehicle routes and delivery schedules│
└─────────────────────────────────────────────────────────┘
```

### Justification & Target Latency Requirement
- **Target Performance**: Target performance is **<2.0 seconds total optimization latency for the DIRS-50 benchmark (50 incidents / 25 vehicles)** (`TARGET`). Actual runtime will be measured and reported after implementation.
- **Separation of Concerns**: Graph edge weighting is handled by `NetworkX`, preventing solver bloat in OR-Tools.
- **Robust Infeasibility Defense**: If total demand exceeds fleet capacity, OR-Tools CP-SAT automatically drops low-priority node visits with scalar penalties while completing allocation for high-priority incidents.
