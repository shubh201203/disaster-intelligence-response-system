import time
import json
import os
import sys
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.ai.optimization.graph import create_synthetic_toy_graph, RoadGraphEngine
from app.ai.optimization.allocation import (
    ResourceAllocationEngine,
    GreedyProximityAllocationEngine,
    FCFSAllocationEngine
)
from app.ai.optimization.benchmark_dataset import generate_dirs50_benchmark_dataset
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph

def run_phase5d_benchmark():
    print("==================================================")
    print("   DIRS PHASE 5D RESOURCE ALLOCATION BENCHMARK   ")
    print("==================================================")

    # 1. Generate standard DIRS-50 synthetic dataset (50 incidents, 25 depots)
    incidents, depots = generate_dirs50_benchmark_dataset(num_incidents=50, num_depots=25, seed=42)
    graph_engine = create_chennai_benchmark_graph()

    print(f"Dataset Loaded: {len(incidents)} active incidents, {len(depots)} resource depots.")
    print(f"Graph Network Loaded: {graph_engine.graph.number_of_nodes()} nodes, {graph_engine.graph.number_of_edges()} edges.\n")

    # Initialize Solvers
    cpsat_engine = ResourceAllocationEngine()
    greedy_engine = GreedyProximityAllocationEngine()
    fcfs_engine = FCFSAllocationEngine()

    # 2. Benchmark CP-SAT Engine
    print("--- 1. CP-SAT Multi-Commodity Optimization Engine ---")
    t0 = time.perf_counter()
    res_cpsat = cpsat_engine.solve(incidents, depots, graph_engine, solver_time_limit_sec=5.0)
    t1 = time.perf_counter()
    cpsat_wall_ms = round((t1 - t0) * 1000.0, 2)
    print(f"Status: {res_cpsat.solver_status} ({res_cpsat.operational_feasibility})")
    print(f"Runtime: {res_cpsat.solver_runtime_ms:.2f} ms (Wall-clock: {cpsat_wall_ms} ms)")
    print(f"Total Unmet Demand: {res_cpsat.total_unmet_demand_quantity:.1f} ({res_cpsat.unmet_demand_percentage:.2f}%)")
    print(f"Priority-Weighted Unmet: {res_cpsat.priority_weighted_unmet_demand:.1f}")
    print(f"Critical Fulfillment: {res_cpsat.critical_fulfillment_percentage:.2f}%")
    print(f"Mean Travel Time: {res_cpsat.mean_shipment_travel_time_mins:.1f} mins")
    print(f"Resource Utilization: {res_cpsat.resource_utilization_percentage:.2f}%\n")

    # 3. Benchmark Baseline A (Greedy Proximity)
    print("--- 2. Baseline A: Greedy Proximity Allocation ---")
    t0 = time.perf_counter()
    res_greedy = greedy_engine.solve(incidents, depots, graph_engine)
    t1 = time.perf_counter()
    greedy_wall_ms = round((t1 - t0) * 1000.0, 2)
    print(f"Runtime: {res_greedy.solver_runtime_ms:.2f} ms")
    print(f"Total Unmet Demand: {res_greedy.total_unmet_demand_quantity:.1f} ({res_greedy.unmet_demand_percentage:.2f}%)")
    print(f"Priority-Weighted Unmet: {res_greedy.priority_weighted_unmet_demand:.1f}")
    print(f"Critical Fulfillment: {res_greedy.critical_fulfillment_percentage:.2f}%")
    print(f"Mean Travel Time: {res_greedy.mean_shipment_travel_time_mins:.1f} mins\n")

    # 4. Benchmark Baseline B (FCFS Queue)
    print("--- 3. Baseline B: First-Come-First-Served (FCFS) ---")
    t0 = time.perf_counter()
    res_fcfs = fcfs_engine.solve(incidents, depots, graph_engine)
    t1 = time.perf_counter()
    fcfs_wall_ms = round((t1 - t0) * 1000.0, 2)
    print(f"Runtime: {res_fcfs.solver_runtime_ms:.2f} ms")
    print(f"Total Unmet Demand: {res_fcfs.total_unmet_demand_quantity:.1f} ({res_fcfs.unmet_demand_percentage:.2f}%)")
    print(f"Priority-Weighted Unmet: {res_fcfs.priority_weighted_unmet_demand:.1f}")
    print(f"Critical Fulfillment: {res_fcfs.critical_fulfillment_percentage:.2f}%")
    print(f"Mean Travel Time: {res_fcfs.mean_shipment_travel_time_mins:.1f} mins\n")

    # Summary JSON structure
    report = {
        "benchmark_name": "DIRS-50 Multi-Commodity Resource Allocation Benchmark",
        "num_incidents": len(incidents),
        "num_depots": len(depots),
        "results": {
            "CP_SAT": {
                "solver_status": res_cpsat.solver_status,
                "operational_feasibility": res_cpsat.operational_feasibility,
                "runtime_ms": res_cpsat.solver_runtime_ms,
                "unmet_demand_qty": res_cpsat.total_unmet_demand_quantity,
                "unmet_demand_pct": res_cpsat.unmet_demand_percentage,
                "priority_weighted_unmet": res_cpsat.priority_weighted_unmet_demand,
                "critical_fulfillment_pct": res_cpsat.critical_fulfillment_percentage,
                "mean_travel_time_mins": res_cpsat.mean_shipment_travel_time_mins,
                "resource_utilization_pct": res_cpsat.resource_utilization_percentage
            },
            "GREEDY_PROXIMITY": {
                "runtime_ms": res_greedy.solver_runtime_ms,
                "unmet_demand_qty": res_greedy.total_unmet_demand_quantity,
                "unmet_demand_pct": res_greedy.unmet_demand_percentage,
                "priority_weighted_unmet": res_greedy.priority_weighted_unmet_demand,
                "critical_fulfillment_pct": res_greedy.critical_fulfillment_percentage,
                "mean_travel_time_mins": res_greedy.mean_shipment_travel_time_mins
            },
            "FCFS_QUEUE": {
                "runtime_ms": res_fcfs.solver_runtime_ms,
                "unmet_demand_qty": res_fcfs.total_unmet_demand_quantity,
                "unmet_demand_pct": res_fcfs.unmet_demand_percentage,
                "priority_weighted_unmet": res_fcfs.priority_weighted_unmet_demand,
                "critical_fulfillment_pct": res_fcfs.critical_fulfillment_percentage,
                "mean_travel_time_mins": res_fcfs.mean_shipment_travel_time_mins
            }
        }
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/PHASE5D_BENCHMARK_RESULTS.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Benchmark completed. Results written to docs/PHASE5D_BENCHMARK_RESULTS.json.")

if __name__ == "__main__":
    run_phase5d_benchmark()
