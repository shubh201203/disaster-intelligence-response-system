import time
import json
import os
import sys
import hashlib
import math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.ai.optimization.graph import create_synthetic_toy_graph, RoadGraphEngine
from app.ai.optimization.allocation import (
    ResourceAllocationEngine,
    GreedyProximityAllocationEngine,
    FCFSAllocationEngine,
    IncidentDemandInput,
    DepotSupplyInput,
    _resolve_network_matrices
)
from app.ai.optimization.benchmark_dataset import generate_dirs50_benchmark_dataset
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph

def run_reconciliation():
    print("==================================================================")
    print("   DIRS PHASE 5D FINAL RECONCILIATION & CROSS-VALIDATION SUITE   ")
    print("==================================================================")

    graph_engine = create_chennai_benchmark_graph()
    cpsat_engine = ResourceAllocationEngine()
    greedy_engine = GreedyProximityAllocationEngine()
    fcfs_engine = FCFSAllocationEngine()

    # ------------------------------------------------------------------
    # 1. DIRS-50 STANDARD PERFORMANCE BENCHMARK (10 REPEATED RUNS)
    # ------------------------------------------------------------------
    print("\n--- 1. DIRS-50 STANDARD PERFORMANCE BENCHMARK (10 REPETITIONS) ---")
    incidents, depots = generate_dirs50_benchmark_dataset(num_incidents=50, num_depots=25, seed=42)

    runtimes_total = []
    runtimes_matrix = []
    runtimes_model = []
    runtimes_search = []
    runtimes_extract = []

    for idx in range(10):
        res = cpsat_engine.solve(incidents, depots, graph_engine, solver_time_limit_sec=1.5)
        tb = res.timing_breakdown

        runtimes_matrix.append(tb.get("matrix_retrieval_ms", 0.0))
        runtimes_model.append(tb.get("model_construction_ms", 0.0))
        runtimes_search.append(tb.get("cpsat_solve_ms", 0.0))
        runtimes_extract.append(tb.get("solution_extraction_ms", 0.0))
        runtimes_total.append(tb.get("total_execution_ms", 0.0))

    dirs50_stats = {
        "benchmark_name": "DIRS-50 STANDARD PERFORMANCE BENCHMARK",
        "dataset_seed": 42,
        "num_incidents": 50,
        "num_depots": 25,
        "num_repetitions": 10,
        "matrix_ms_median": round(float(np.median(runtimes_matrix)), 2),
        "model_ms_median": round(float(np.median(runtimes_model)), 2),
        "search_ms_median": round(float(np.median(runtimes_search)), 2),
        "extract_ms_median": round(float(np.median(runtimes_extract)), 2),
        "total_ms_min": round(float(np.min(runtimes_total)), 2),
        "total_ms_median": round(float(np.median(runtimes_total)), 2),
        "total_ms_p95": round(float(np.percentile(runtimes_total, 95)), 2),
        "total_ms_max": round(float(np.max(runtimes_total)), 2),
        "latency_definition": "TOTAL OPTIMIZATION LATENCY = Matrix Retrieval + Model Construction + CP-SAT Search + Solution Extraction + Explanation Generation"
    }

    print(f"Matrix Retrieval (Median):    {dirs50_stats['matrix_ms_median']} ms")
    print(f"Model Construction (Median):  {dirs50_stats['model_ms_median']} ms")
    print(f"CP-SAT Search (Median):        {dirs50_stats['search_ms_median']} ms")
    print(f"Solution Extraction (Median):  {dirs50_stats['extract_ms_median']} ms")
    print(f"Total Latency (Min):           {dirs50_stats['total_ms_min']} ms")
    print(f"Total Latency (Median):        {dirs50_stats['total_ms_median']} ms")
    print(f"Total Latency (p95):           {dirs50_stats['total_ms_p95']} ms")
    print(f"Total Latency (Max):           {dirs50_stats['total_ms_max']} ms")

    target_median_met = dirs50_stats['total_ms_median'] <= 2000.0
    target_p95_met = dirs50_stats['total_ms_p95'] <= 2000.0

    print(f"Phase 5A Target Median (<= 2000 ms): {'MET' if target_median_met else 'NOT MET'}")
    print(f"Phase 5A Target p95    (<= 2000 ms): {'MET' if target_p95_met else 'NOT MET'}")

    # ------------------------------------------------------------------
    # 2. INDEPENDENT OBJECTIVE CROSS-VALIDATION
    # ------------------------------------------------------------------
    print("\n--- 2. OBJECTIVE CROSS-VALIDATION & RECONCILIATION ---")
    
    # Solve standard DIRS-50 once for exact cross-validation
    sol_dirs50 = cpsat_engine.solve(incidents, depots, graph_engine, solver_time_limit_sec=1.5)
    
    # Generate deterministic hash of allocations
    alloc_repr = json.dumps([
        {"d": a.depot_id, "i": a.incident_id, "r": a.commodity, "q": a.quantity}
        for a in sorted(sol_dirs50.allocations, key=lambda x: (x.depot_id, x.incident_id, x.commodity))
    ], sort_keys=True)
    alloc_hash = hashlib.sha256(alloc_repr.encode('utf-8')).hexdigest()[:16]

    # Recompute objective directly from production formula using exact CP-SAT integer ceiling coefficient scaling
    recomputed_z_unmet = 0.0
    recomputed_z_penalty = 0.0

    for u in sol_dirs50.unmet_demands:
        inc = next(i for i in incidents if i.incident_id == u.incident_id)
        p_score = inc.priority_score
        p_weight = max(1.0, p_score)
        sev_boost = 3.0 if inc.severity_level == "CRITICAL" else (2.0 if inc.severity_level == "HIGH" else 1.0)

        # Term 1: math.ceil(alpha_1 * p_weight * sev_boost * SCALE) / SCALE * u_qty
        w_unmet_coeff = math.ceil(10.0 * p_weight * sev_boost * 1000) / 1000.0
        recomputed_z_unmet += w_unmet_coeff * u.unmet_quantity
        
        # Term 2: math.ceil(alpha_2 * (p_score^2 / 10) * sev_boost * SCALE) / SCALE * u_qty
        w_penalty_coeff = math.ceil(5.0 * (p_score ** 2 / 10.0) * sev_boost * 1000) / 1000.0
        recomputed_z_penalty += w_penalty_coeff * u.unmet_quantity

    recomputed_z_time = 0.0
    recomputed_z_dist = 0.0
    active_pairs = set((a.depot_id, a.incident_id) for a in sol_dirs50.allocations)
    
    reachability_mask, travel_times, distances = _resolve_network_matrices(graph_engine, depots, incidents)

    for dep_id, inc_id in active_pairs:
        t_mins = travel_times[(dep_id, inc_id)]
        d_km = distances[(dep_id, inc_id)]
        w_time_coeff = math.ceil(1.0 * t_mins * 1000) / 1000.0
        w_dist_coeff = math.ceil(0.2 * d_km * 1000) / 1000.0
        recomputed_z_time += w_time_coeff
        recomputed_z_dist += w_dist_coeff

    independently_recomputed_obj = recomputed_z_unmet + recomputed_z_penalty + recomputed_z_time + recomputed_z_dist
    solver_reported_obj = sol_dirs50.objective_value
    diff_obj = abs(independently_recomputed_obj - solver_reported_obj)

    print(f"CP-SAT Allocation Hash:                  {alloc_hash}")
    print(f"CP-SAT Solver Objective:                 {solver_reported_obj:.4f}")
    print(f"Independently Recomputed Objective:      {independently_recomputed_obj:.4f}")
    print(f"  - Recomputed Unmet Term:               {recomputed_z_unmet:.4f}")
    print(f"  - Recomputed Penalty Term:             {recomputed_z_penalty:.4f}")
    print(f"  - Recomputed Time Term:                {recomputed_z_time:.4f}")
    print(f"  - Recomputed Dist Term:                {recomputed_z_dist:.4f}")
    print(f"Difference:                             {diff_obj:.4f}")
    print(f"Objective Reconciled (Diff < 0.01):      {diff_obj < 0.01}")

    # ------------------------------------------------------------------
    # 3. SCENARIO-5D-B SEVERE-SCARCITY RECONCILIATION
    # ------------------------------------------------------------------
    print("\n--- 3. SCENARIO-5D-B SEVERE-SCARCITY FUNCTIONAL BENCHMARK (10 REPETITIONS) ---")
    inc_b, dep_b = generate_dirs50_benchmark_dataset(num_incidents=20, num_depots=10, seed=42, supply_multiplier=0.2)

    scen_b_runtimes = []
    for idx in range(10):
        res_b = cpsat_engine.solve(inc_b, dep_b, graph_engine, solver_time_limit_sec=1.5)
        scen_b_runtimes.append(res_b.solver_runtime_ms)

    # Recompute SCENARIO-5D-B objective independently
    sol_b = cpsat_engine.solve(inc_b, dep_b, graph_engine, solver_time_limit_sec=1.5)
    
    z_b_unmet = 0.0
    z_b_penalty = 0.0
    for u in sol_b.unmet_demands:
        inc = next(i for i in inc_b if i.incident_id == u.incident_id)
        p_score = inc.priority_score
        p_weight = max(1.0, p_score)
        sev_boost = 3.0 if inc.severity_level == "CRITICAL" else (2.0 if inc.severity_level == "HIGH" else 1.0)
        w_unmet_coeff = math.ceil(10.0 * p_weight * sev_boost * 1000) / 1000.0
        w_penalty_coeff = math.ceil(5.0 * (p_score ** 2 / 10.0) * sev_boost * 1000) / 1000.0
        z_b_unmet += w_unmet_coeff * u.unmet_quantity
        z_b_penalty += w_penalty_coeff * u.unmet_quantity

    z_b_time = 0.0
    z_b_dist = 0.0
    active_b_pairs = set((a.depot_id, a.incident_id) for a in sol_b.allocations)
    for dep_id, inc_id in active_b_pairs:
        alloc_item = next(a for a in sol_b.allocations if a.depot_id == dep_id and a.incident_id == inc_id)
        w_time_coeff = math.ceil(1.0 * alloc_item.travel_time_minutes * 1000) / 1000.0
        w_dist_coeff = math.ceil(0.2 * alloc_item.distance_km * 1000) / 1000.0
        z_b_time += w_time_coeff
        z_b_dist += w_dist_coeff

    recomputed_b_obj = z_b_unmet + z_b_penalty + z_b_time + z_b_dist
    solver_b_obj = sol_b.objective_value
    diff_b = abs(recomputed_b_obj - solver_b_obj)

    scen_b_stats = {
        "benchmark_name": "SCENARIO-5D-B SEVERE-SCARCITY FUNCTIONAL BENCHMARK",
        "dataset_seed": 42,
        "num_incidents": 20,
        "num_depots": 10,
        "supply_multiplier": 0.2,
        "runtime_ms_median": round(float(np.median(scen_b_runtimes)), 2),
        "runtime_ms_p95": round(float(np.percentile(scen_b_runtimes, 95)), 2),
        "solver_objective": round(solver_b_obj, 2),
        "independently_recomputed_objective": round(recomputed_b_obj, 2),
        "objective_difference": round(diff_b, 4),
        "reconciled": diff_b < 1.0
    }

    print(f"SCENARIO-5D-B Median Runtime:             {scen_b_stats['runtime_ms_median']} ms")
    print(f"SCENARIO-5D-B CP-SAT Solver Objective:     {solver_b_obj:.2f}")
    print(f"SCENARIO-5D-B Recomputed Objective:        {recomputed_b_obj:.2f}")
    print(f"SCENARIO-5D-B Reconciled (Diff < 1.0):     {diff_b < 1.0}")

    # Build Cross-Validation JSON Package
    cross_val_package = {
        "dirs50_standard_benchmark": dirs50_stats,
        "dirs50_cross_validation": {
            "dataset_id": "DIRS-50 Standard (50 incidents, 25 depots)",
            "dataset_seed": 42,
            "graph_version": graph_engine.get_graph_version(),
            "solver_version": "Google OR-Tools CP-SAT 9.15.6755",
            "solver_configuration": {
                "num_search_workers": 1,
                "random_seed": 42,
                "max_time_in_seconds": 1.5
            },
            "objective_weights": {
                "alpha_1_unmet": 10.0,
                "alpha_2_penalty": 5.0,
                "alpha_3_time": 1.0,
                "alpha_4_distance": 0.2
            },
            "demand_total": sum(sum(i.demands.values()) for i in incidents),
            "supply_total": sum(sum(d.supplies.values()) for d in depots),
            "allocation_hash": alloc_hash,
            "solver_reported_objective": round(solver_reported_obj, 4),
            "independently_recomputed_objective": round(independently_recomputed_obj, 4),
            "difference": round(diff_obj, 4),
            "objective_reconciled": diff_obj < 1.0
        },
        "scenario_5d_b_severe_scarcity_benchmark": scen_b_stats
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/PHASE5D_CROSS_VALIDATION.json", "w") as f:
        json.dump(cross_val_package, f, indent=2)

    print("\nReconciliation & cross-validation complete. Written to docs/PHASE5D_CROSS_VALIDATION.json.")

if __name__ == "__main__":
    run_reconciliation()
