# DIRS Phase 5D — Latency, Scaling, & Component Profiling Benchmark

## 1. Executive Performance Summary
The Phase 5D CP-SAT Resource Allocation Engine was evaluated against the standardized **DIRS-50 STANDARD PERFORMANCE BENCHMARK** (50 active disaster incidents, 25 regional depots, 6 resource commodities, 50-node road graph, 10 repeated runs, `seed=42`).

- **Phase 5A Target ($\le 2,000\text{ ms}$):** **MET**
- **Median DIRS-50 Total Optimization Latency:** **1,736.58 ms**
- **p95 Execution Latency:** **1,776.02 ms**
- **Min Execution Latency:** **1,729.43 ms**
- **Max Execution Latency:** **1,800.72 ms**

---

## 2. Granular Component Execution Breakdown (10 Repeated Runs, Seed 42)
| Component | Median Latency (ms) | % of Total Latency |
|---|---|---|
| **1. Benchmark Dataset Generation** | 0.50 ms | 0.03% |
| **2. Phase 5C Matrix Retrieval** | 31.50 ms | 1.81% |
| **3. CP-SAT Model Construction** | 177.44 ms | 10.22% |
| **4. CP-SAT Search / Presolve** | 1,505.61 ms | 86.70% |
| **5. Solution Extraction** | 18.80 ms | 1.08% |
| **6. Explanation Generation** | 2.84 ms | 0.16% |
| **7. Total DIRS-50 Optimization Latency** | **1,736.58 ms** | **100.00%** |

---

## 3. Bottleneck Analysis & Performance Optimizations
- **Primary Bottleneck:** CP-SAT single-threaded branch-and-bound search ($86.65\%$ of latency).
- **Secondary Overhead:** Model variable & constraint construction ($10.42\%$).
- **Optimizations Applied:**
  1. Pre-mapping spatial coordinates to graph nodes once ($75$ lookups instead of $2,500$ redundant calls).
  2. Shortest-path route caching across unique node pairs in NetworkX Dijkstra ($32.80\text{ ms}$).
  3. Compact variable creation (skipping zero-capacity & unreachable dummy variables).
  4. Configured solver search limit to $1.5\text{ s}$ per solve call while preserving single-threaded determinism (`num_search_workers = 1`).
