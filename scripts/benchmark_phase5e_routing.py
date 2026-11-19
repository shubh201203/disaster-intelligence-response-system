"""
DIRS Phase 5E — Vehicle Routing Benchmark & Scalability Profiling Script
Benchmark: DIRS-ROUTE-25 (25 incidents, 10 vehicles) & Scale Variants (5, 10, 25, 50, 100)
Classification: SYNTHETIC CALIBRATED ROUTING BENCHMARK
"""
import time
import statistics
import json
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
from app.ai.optimization.routing import VehicleRoutingEngine, NearestFeasibleRoutingEngine, FCFSRoutingEngine, verify_phase5d_conservation
from app.ai.optimization.routing_benchmark_dataset import generate_dirs_route_benchmark

def run_scalability_benchmark():
    print("=" * 70)
    print("DIRS Phase 5E — Vehicle Routing Scalability & Performance Benchmark")
    print("=" * 70)

    scales = [
        (5, 3, 2),
        (10, 5, 3),
        (25, 10, 4),
        (50, 20, 5),
        (100, 30, 8),
    ]

    results = {}
    engine = VehicleRoutingEngine()

    for n_inc, n_veh, n_dep in scales:
        print(f"\n--- Benchmarking Scale: {n_inc} Incidents, {n_veh} Vehicles, {n_dep} Depots ---")
        graph = create_chennai_benchmark_graph(num_nodes=max(50, n_inc + n_dep))
        shipments, vehicles = generate_dirs_route_benchmark(num_incidents=n_inc, num_vehicles=n_veh, num_depots=n_dep, seed=42)

        latencies = []
        timing_records = []
        n_repeats = 5 if n_inc <= 50 else 3

        for rep in range(n_repeats):
            t0 = time.perf_counter()
            res = engine.solve(shipments, vehicles, graph, solver_time_limit_sec=10.0)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            timing_records.append(res.timing_breakdown)

        med_lat = statistics.median(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        p95_lat = sorted(latencies)[int(0.95 * len(latencies))]

        # Select the median run's timing record so component breakdown sums exactly to total_routing_ms
        sorted_records = sorted(zip(latencies, timing_records), key=lambda x: x[0])
        med_record = sorted_records[len(sorted_records) // 2][1]

        results[f"DIRS-ROUTE-{n_inc}"] = {
            "num_incidents": n_inc,
            "num_vehicles": n_veh,
            "num_depots": n_dep,
            "repeats": n_repeats,
            "latency_min_ms": round(min_lat, 2),
            "latency_median_ms": round(med_lat, 2),
            "latency_p95_ms": round(p95_lat, 2),
            "latency_max_ms": round(max_lat, 2),
            "timing_breakdown_median_run_ms": med_record,
            "component_sum_ms": round(
                med_record["matrix_build_ms"] +
                med_record["model_construction_ms"] +
                med_record["solver_search_ms"] +
                med_record["solution_extraction_ms"] +
                med_record["orchestration_overhead_ms"],
                2
            ),
            "routes_generated": len(res.routes),
            "unrouted_count": res.unrouted_shipment_count,
            "unrouted_pct": round(res.unrouted_shipment_pct, 2),
            "sla_compliance_pct": round(res.sla_compliance_pct, 2),
            "solver_status": res.solver_status,
            "operational_status": res.operational_status,
        }

        print(f"Latency: Min={min_lat:.2f}ms | Median={med_lat:.2f}ms | p95={p95_lat:.2f}ms | Max={max_lat:.2f}ms")
        print(f"Timing Breakdown: {med_record}")
        print(f"Status: Solver={res.solver_status} | Operational={res.operational_status} | Routes={len(res.routes)} | Unrouted={res.unrouted_shipment_count}")

    # Baseline comparison on DIRS-ROUTE-25
    print("\n--- Running Fair Baseline Comparison on DIRS-ROUTE-25 ---")
    graph_25 = create_chennai_benchmark_graph(num_nodes=50)
    s25, v25 = generate_dirs_route_benchmark(num_incidents=25, num_vehicles=10, num_depots=4, seed=42)

    t0 = time.perf_counter()
    res_ortools = engine.solve(s25, v25, graph_25, solver_time_limit_sec=10.0)
    t_ortools = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    res_nearest = NearestFeasibleRoutingEngine().solve(s25, v25, graph_25)
    t_nearest = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    res_fcfs = FCFSRoutingEngine().solve(s25, v25, graph_25)
    t_fcfs = (time.perf_counter() - t0) * 1000.0

    def compile_baseline_entry(res, t_ms, name):
        tot_late_raw = sum(s.lateness_min for r in res.routes for s in r.stops)
        tot_time_raw = sum(r.total_travel_time_min for r in res.routes)
        tot_dist_raw = sum(r.total_distance_km for r in res.routes)
        used_veh = len(res.routes)
        indep_obj = 1000.0 * tot_late_raw + 10.0 * tot_time_raw + 1.0 * tot_dist_raw + 100.0 * used_veh
        rounded_display_obj = 1000.0 * round(tot_late_raw, 2) + 10.0 * round(tot_time_raw, 2) + 1.0 * round(tot_dist_raw, 2) + 100.0 * used_veh

        return {
            "unrouted_pct": round(res.unrouted_shipment_pct, 2),
            "sla_compliance_pct": round(res.sla_compliance_pct, 2),
            "mean_response_time_min": round(res.mean_response_time_min, 2),
            "critical_mean_response_time_min": round(res.critical_mean_response_time_min, 2),
            "total_travel_time_min": round(res.total_travel_time_min, 2),
            "total_distance_km": round(res.total_distance_km, 2),
            "vehicle_utilization_pct": round(res.vehicle_utilization_pct, 2),
            "mean_weight_utilization_pct": round(res.mean_weight_utilization_pct, 2),
            "mean_volume_utilization_pct": round(res.mean_volume_utilization_pct, 2),
            "total_late_minutes": round(res.total_late_minutes, 2),
            "raw_objective_value": round(res.objective_value, 4),
            "independent_recomputed_objective": round(indep_obj, 4),
            "rounded_metrics_objective": round(rounded_display_obj, 2),
            "rounding_discrepancy": round(rounded_display_obj - res.objective_value, 4),
            "runtime_ms": round(t_ms, 2),
        }

    baseline_comp = {
        "OR-Tools RoutingModel": compile_baseline_entry(res_ortools, t_ortools, "OR-Tools"),
        "Baseline A (Nearest-Feasible)": compile_baseline_entry(res_nearest, t_nearest, "Nearest-Feasible"),
        "Baseline B (FCFS)": compile_baseline_entry(res_fcfs, t_fcfs, "FCFS"),
    }

    output_data = {
        "scalability": results,
        "baseline_comparison_dirs_route_25": baseline_comp,
    }

    out_path = os.path.join("docs", "PHASE5E_BENCHMARK_RESULTS.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nSaved benchmark output to {out_path}")

if __name__ == "__main__":
    run_scalability_benchmark()
