"""
DIRS Phase 5C — Graph Engine & Matrix Generation Performance Benchmark Script
Measures actual graph construction, shortest path, and matrix generation latency across 10, 50, 100, 500, 1000 nodes.
"""
import sys
import os
import time
import statistics
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph

def benchmark_graph_scale(num_nodes: int, repetitions: int = 15) -> Dict[str, Any]:
    construct_times: List[float] = []
    shortest_path_times: List[float] = []
    matrix_gen_times: List[float] = []

    for r in range(repetitions):
        # 1. Graph Construction Time
        t0 = time.perf_counter()
        engine = create_chennai_benchmark_graph(num_nodes=num_nodes, seed=42 + r)
        t1 = time.perf_counter()
        construct_times.append((t1 - t0) * 1000.0)

        # 2. Shortest Path Time (Central Depot to Kovalam)
        t2 = time.perf_counter()
        engine.compute_shortest_path("HUB_CENTRAL", "HUB_KOVALAM")
        t3 = time.perf_counter()
        shortest_path_times.append((t3 - t2) * 1000.0)

        # 3. Matrix Generation Time (Sample 10 Origins x 10 Destinations)
        nodes = list(engine.graph.nodes.keys())
        origins = nodes[:min(10, len(nodes))]
        destinations = nodes[min(5, len(nodes)-1):min(15, len(nodes))]
        
        t4 = time.perf_counter()
        engine.generate_matrix(origins, destinations)
        t5 = time.perf_counter()
        matrix_gen_times.append((t5 - t4) * 1000.0)

    def stats(data: List[float]):
        s = sorted(data)
        median = statistics.median(s)
        p95_idx = int(math.ceil(0.95 * len(s))) - 1
        p95 = s[min(p95_idx, len(s)-1)]
        return round(median, 3), round(p95, 3)

    import math
    c_med, c_p95 = stats(construct_times)
    sp_med, sp_p95 = stats(shortest_path_times)
    m_med, m_p95 = stats(matrix_gen_times)

    return {
        "num_nodes": num_nodes,
        "construct_median_ms": c_med,
        "construct_p95_ms": c_p95,
        "shortest_path_median_ms": sp_med,
        "shortest_path_p95_ms": sp_p95,
        "matrix_median_ms": m_med,
        "matrix_p95_ms": m_p95
    }

def run_benchmarks():
    print("=" * 80)
    print("DIRS PHASE 5C GRAPH ENGINE & MATRIX LATENCY BENCHMARK REPORT")
    print("=" * 80)
    print("Target Requirement (Phase 5A): <2.0s total optimization latency for DIRS-50 [TARGET]")
    print("-" * 80)

    scales = [10, 50, 100, 500, 1000]
    results = []

    for scale in scales:
        res = benchmark_graph_scale(num_nodes=scale, repetitions=15)
        results.append(res)
        print(f"Nodes: {res['num_nodes']:4d} | "
              f"Build Med: {res['construct_median_ms']:7.3f}ms (p95: {res['construct_p95_ms']:7.3f}ms) | "
              f"Path Med: {res['shortest_path_median_ms']:6.3f}ms (p95: {res['shortest_path_p95_ms']:6.3f}ms) | "
              f"Matrix (10x10) Med: {res['matrix_median_ms']:7.3f}ms (p95: {res['matrix_p95_ms']:7.3f}ms)")

    print("=" * 80)
    print("BENCHMARK SUMMARY COMPLETE")
    print("=" * 80)
    return results

if __name__ == "__main__":
    run_benchmarks()
