import time
import json
import os
import sys
import numpy as np
from typing import Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.ai.optimization.graph import create_synthetic_toy_graph, RoadGraphEngine, haversine_distance
from app.ai.optimization.allocation import (
    ResourceAllocationEngine,
    GreedyProximityAllocationEngine,
    FCFSAllocationEngine,
    IncidentDemandInput,
    DepotSupplyInput
)
from app.ai.optimization.benchmark_dataset import generate_dirs50_benchmark_dataset
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph

def run_forensic_suite():
    print("==================================================================")
    print("  DIRS PHASE 5D FORENSIC AUDIT & PERFORMANCE PROFILING SUITE     ")
    print("==================================================================")

    graph_engine = create_chennai_benchmark_graph()
    cpsat_engine = ResourceAllocationEngine()
    greedy_engine = GreedyProximityAllocationEngine()
    fcfs_engine = FCFSAllocationEngine()

    # ------------------------------------------------------------------
    # 1. TIMING BREAKDOWN & REPEATED RUN PROFILING (DIRS-50 Benchmark)
    # ------------------------------------------------------------------
    print("\n--- 1. SECTION 1: DETAILED TIMING BREAKDOWN (10 REPEATED RUNS) ---")
    
    runs_data = []
    num_repeats = 10
    
    for run_idx in range(num_repeats):
        t_ds_start = time.perf_counter()
        incidents, depots = generate_dirs50_benchmark_dataset(num_incidents=50, num_depots=25, seed=42)
        t_ds_end = time.perf_counter()
        t_dataset_ms = (t_ds_end - t_ds_start) * 1000.0

        res = cpsat_engine.solve(incidents, depots, graph_engine, solver_time_limit_sec=1.5)
        tb = res.timing_breakdown

        run_record = {
            "dataset_gen_ms": round(t_dataset_ms, 3),
            "matrix_retrieval_ms": tb.get("matrix_retrieval_ms", 0.0),
            "model_construction_ms": tb.get("model_construction_ms", 0.0),
            "cpsat_solve_ms": tb.get("cpsat_solve_ms", 0.0),
            "solution_extraction_ms": tb.get("solution_extraction_ms", 0.0),
            "explanation_generation_ms": tb.get("explanation_generation_ms", 0.0),
            "total_execution_ms": tb.get("total_execution_ms", 0.0),
            "total_phase5d_time_ms": round(t_dataset_ms + tb.get("total_execution_ms", 0.0), 3)
        }
        runs_data.append(run_record)

    totals = [r["total_phase5d_time_ms"] for r in runs_data]
    solves = [r["cpsat_solve_ms"] for r in runs_data]
    models = [r["model_construction_ms"] for r in runs_data]
    matrices = [r["matrix_retrieval_ms"] for r in runs_data]

    timing_stats = {
        "dataset_gen_ms_median": round(float(np.median([r["dataset_gen_ms"] for r in runs_data])), 2),
        "matrix_retrieval_ms_median": round(float(np.median(matrices)), 2),
        "model_construction_ms_median": round(float(np.median(models)), 2),
        "cpsat_solve_ms_median": round(float(np.median(solves)), 2),
        "total_execution_ms_median": round(float(np.median(totals)), 2),
        "total_execution_ms_p95": round(float(np.percentile(totals, 95)), 2),
        "total_execution_ms_min": round(float(np.min(totals)), 2),
        "total_execution_ms_max": round(float(np.max(totals)), 2)
    }

    print(f"Dataset Generation (Median): {timing_stats['dataset_gen_ms_median']} ms")
    print(f"Matrix Retrieval (Median): {timing_stats['matrix_retrieval_ms_median']} ms")
    print(f"Model Construction (Median): {timing_stats['model_construction_ms_median']} ms")
    print(f"CP-SAT Search/Presolve (Median): {timing_stats['cpsat_solve_ms_median']} ms")
    print(f"Total DIRS-50 Execution Latency:")
    print(f"  - Median: {timing_stats['total_execution_ms_median']} ms")
    print(f"  - p95:    {timing_stats['total_execution_ms_p95']} ms")
    print(f"  - Min:    {timing_stats['total_execution_ms_min']} ms")
    print(f"  - Max:    {timing_stats['total_execution_ms_max']} ms")

    # Target Assessment
    target_met = timing_stats['total_execution_ms_median'] <= 2000.0
    print(f"\nPhase 5A Target (<= 2000 ms): {'MET' if target_met else 'NOT MET'} ({timing_stats['total_execution_ms_median']} ms)")

    # ------------------------------------------------------------------
    # 2. CONTROLLED SCENARIOS (SCENARIO-5D-A through F)
    # ------------------------------------------------------------------
    print("\n--- 2. SECTION 6: CONTROLLED SYNTHETIC SCENARIOS EVALUATION ---")
    scenarios_results = {}

    # Helper to compute exact metrics for a result
    def compute_full_metrics(res, incidents, depots, graph):
        # Calculate total travel time and distance
        tot_time = sum(a.travel_time_minutes for a in res.allocations)
        tot_dist = sum(a.distance_km for a in res.allocations)
        return {
            "unmet_pct": res.unmet_demand_percentage,
            "priority_weighted_unmet": res.priority_weighted_unmet_demand,
            "critical_fulfillment_pct": res.critical_fulfillment_percentage,
            "mean_travel_time_mins": res.mean_shipment_travel_time_mins,
            "total_travel_time_mins": round(tot_time, 1),
            "total_travel_distance_km": round(tot_dist, 1),
            "resource_utilization_pct": res.resource_utilization_percentage,
            "objective_value": round(res.objective_value, 2),
            "runtime_ms": res.solver_runtime_ms
        }

    # SCENARIO-5D-A: Unconstrained (Supply > Demand)
    inc_a, dep_a = generate_dirs50_benchmark_dataset(num_incidents=20, num_depots=10, seed=42, supply_multiplier=2.0)
    scenarios_results["SCENARIO_5D_A"] = {
        "description": "Supply > Demand (Unconstrained)",
        "CP_SAT": compute_full_metrics(cpsat_engine.solve(inc_a, dep_a, graph_engine), inc_a, dep_a, graph_engine),
        "GREEDY": compute_full_metrics(greedy_engine.solve(inc_a, dep_a, graph_engine), inc_a, dep_a, graph_engine),
        "FCFS": compute_full_metrics(fcfs_engine.solve(inc_a, dep_a, graph_engine), inc_a, dep_a, graph_engine)
    }

    # SCENARIO-5D-B: Severe Scarcity (Supply < Demand)
    inc_b, dep_b = generate_dirs50_benchmark_dataset(num_incidents=20, num_depots=10, seed=42, supply_multiplier=0.2)
    scenarios_results["SCENARIO_5D_B"] = {
        "description": "Supply < Demand (Severe Scarcity)",
        "CP_SAT": compute_full_metrics(cpsat_engine.solve(inc_b, dep_b, graph_engine), inc_b, dep_b, graph_engine),
        "GREEDY": compute_full_metrics(greedy_engine.solve(inc_b, dep_b, graph_engine), inc_b, dep_b, graph_engine),
        "FCFS": compute_full_metrics(fcfs_engine.solve(inc_b, dep_b, graph_engine), inc_b, dep_b, graph_engine)
    }

    # SCENARIO-5D-C: Priority Competition
    dep_c = [DepotSupplyInput("D1", "Central Stockpile", 13.0827, 80.2707, {"MEDICAL_KITS": 50.0})]
    inc_c = [
        IncidentDemandInput("I_CRIT", "Critical Hospital", 13.0067, 80.2020, 95.0, "CRITICAL", {"MEDICAL_KITS": 50.0}),
        IncidentDemandInput("I_LOW", "Minor Clinic", 12.9249, 80.1000, 20.0, "LOW", {"MEDICAL_KITS": 50.0})
    ]
    scenarios_results["SCENARIO_5D_C"] = {
        "description": "Priority Competition (Critical Hospital vs Minor Clinic for 50 Medical Kits)",
        "CP_SAT": compute_full_metrics(cpsat_engine.solve(inc_c, dep_c, graph_engine), inc_c, dep_c, graph_engine),
        "GREEDY": compute_full_metrics(greedy_engine.solve(inc_c, dep_c, graph_engine), inc_c, dep_c, graph_engine),
        "FCFS": compute_full_metrics(fcfs_engine.solve(inc_c, dep_c, graph_engine), inc_c, dep_c, graph_engine)
    }

    # SCENARIO-5D-D: Unreachable Nearest Depot
    toy_blocked = create_synthetic_toy_graph()
    toy_blocked.apply_blockage("BLK_A_B", "A", "B", blockage_status="IMPASSABLE")
    dep_d = [
        DepotSupplyInput("B", "Blocked Depot B (10km)", 13.00, 80.10, {"WATER": 500.0}),
        DepotSupplyInput("D", "Reachable Depot D (13km)", 12.95, 80.00, {"WATER": 500.0})
    ]
    inc_d = [IncidentDemandInput("A", "Target Site A", 13.00, 80.00, 80.0, "HIGH", {"WATER": 300.0})]
    scenarios_results["SCENARIO_5D_D"] = {
        "description": "Unreachable Nearest Depot (D1 Impassable, D2 Reachable)",
        "CP_SAT": compute_full_metrics(cpsat_engine.solve(inc_d, dep_d, toy_blocked), inc_d, dep_d, toy_blocked),
        "GREEDY": compute_full_metrics(greedy_engine.solve(inc_d, dep_d, toy_blocked), inc_d, dep_d, toy_blocked),
        "FCFS": compute_full_metrics(fcfs_engine.solve(inc_d, dep_d, toy_blocked), inc_d, dep_d, toy_blocked)
    }

    # SCENARIO-5D-E: Multi-Depot Supply Competition
    dep_e = [
        DepotSupplyInput("D1", "Depot 1", 13.00, 80.00, {"WATER": 400.0}),
        DepotSupplyInput("D2", "Depot 2", 13.00, 80.10, {"WATER": 400.0}),
        DepotSupplyInput("D3", "Depot 3", 12.95, 80.00, {"WATER": 400.0})
    ]
    inc_e = [IncidentDemandInput("I1", "Massive Flood Site", 13.00, 80.25, 90.0, "CRITICAL", {"WATER": 1000.0})]
    scenarios_results["SCENARIO_5D_E"] = {
        "description": "Multi-Depot Supply Competition (1000 Water needed, depots have 400 each)",
        "CP_SAT": compute_full_metrics(cpsat_engine.solve(inc_e, dep_e, toy_blocked), inc_e, dep_e, toy_blocked),
        "GREEDY": compute_full_metrics(greedy_engine.solve(inc_e, dep_e, toy_blocked), inc_e, dep_e, toy_blocked),
        "FCFS": compute_full_metrics(fcfs_engine.solve(inc_e, dep_e, toy_blocked), inc_e, dep_e, toy_blocked)
    }

    # SCENARIO-5D-F: Commodity-Specific Scarcity
    dep_f = [DepotSupplyInput("D1", "Hub 1", 13.0827, 80.2707, {"WATER": 10000.0, "MEDICAL_KITS": 10.0})]
    inc_f = [IncidentDemandInput("I1", "Disaster Site", 13.0067, 80.2020, 85.0, "HIGH", {"WATER": 1000.0, "MEDICAL_KITS": 200.0})]
    scenarios_results["SCENARIO_5D_F"] = {
        "description": "Commodity-Specific Scarcity (Surplus Water, Deficit Medical Kits)",
        "CP_SAT": compute_full_metrics(cpsat_engine.solve(inc_f, dep_f, graph_engine), inc_f, dep_f, graph_engine),
        "GREEDY": compute_full_metrics(greedy_engine.solve(inc_f, dep_f, graph_engine), inc_f, dep_f, graph_engine),
        "FCFS": compute_full_metrics(fcfs_engine.solve(inc_f, dep_f, graph_engine), inc_f, dep_f, graph_engine)
    }

    # Print Comparison Table for SCENARIO-5D-B
    print("\n--- BASELINE COMPARISON TABLE (SCENARIO-5D-B: Severe Scarcity) ---")
    b_res = scenarios_results["SCENARIO_5D_B"]
    print(f"{'Metric':<30} | {'FCFS':<12} | {'Greedy':<12} | {'CP-SAT':<12}")
    print("-" * 72)
    for m in ["unmet_pct", "priority_weighted_unmet", "critical_fulfillment_pct", "mean_travel_time_mins", "total_travel_time_mins", "total_travel_distance_km", "resource_utilization_pct", "objective_value", "runtime_ms"]:
        v_fcfs = b_res["FCFS"][m]
        v_grd = b_res["GREEDY"][m]
        v_sat = b_res["CP_SAT"][m]
        print(f"{m:<30} | {v_fcfs:<12} | {v_grd:<12} | {v_sat:<12}")

    # ------------------------------------------------------------------
    # 3. OBJECTIVE SCALING FORENSIC ANALYSIS
    # ------------------------------------------------------------------
    print("\n--- 3. SECTION 4: OBJECTIVE SCALING FORENSIC BREAKDOWN ---")
    # Compute raw & weighted contribution for SCENARIO-5D-B under CP-SAT
    inc_b_sol = cpsat_engine.solve(inc_b, dep_b, graph_engine)
    
    # Calculate Z_unmet, Z_penalty, Z_time, Z_distance
    z_unmet_raw = 0.0
    z_penalty_raw = 0.0
    z_time_raw = 0.0
    z_dist_raw = 0.0

    for inc in inc_b:
        p_weight = max(1.0, inc.priority_score)
        sev_boost = 3.0 if inc.severity_level == "CRITICAL" else (2.0 if inc.severity_level == "HIGH" else 1.0)
        
        for u_item in inc_b_sol.unmet_demands:
            if u_item.incident_id == inc.incident_id:
                u_qty = u_item.unmet_quantity
                z_unmet_raw += p_weight * sev_boost * u_qty
                z_penalty_raw += (inc.priority_score**2 / 10.0) * sev_boost * u_qty

    for alloc in inc_b_sol.allocations:
        z_time_raw += alloc.travel_time_minutes
        z_dist_raw += alloc.distance_km

    w_unmet = 10.0 * z_unmet_raw
    w_penalty = 5.0 * z_penalty_raw
    w_time = 1.0 * z_time_raw
    w_dist = 0.2 * z_dist_raw

    tot_obj = w_unmet + w_penalty + w_time + w_dist
    pct_unmet = (w_unmet / tot_obj * 100.0) if tot_obj > 0 else 0
    pct_penalty = (w_penalty / tot_obj * 100.0) if tot_obj > 0 else 0
    pct_time = (w_time / tot_obj * 100.0) if tot_obj > 0 else 0
    pct_dist = (w_dist / tot_obj * 100.0) if tot_obj > 0 else 0

    print(f"Z_unmet (alpha=10.0):   Raw={z_unmet_raw:.1f}, Weighted={w_unmet:.1f} ({pct_unmet:.2f}%)")
    print(f"Z_penalty (alpha=5.0):  Raw={z_penalty_raw:.1f}, Weighted={w_penalty:.1f} ({pct_penalty:.2f}%)")
    print(f"Z_time (alpha=1.0):     Raw={z_time_raw:.1f}, Weighted={w_time:.1f} ({pct_time:.4f}%)")
    print(f"Z_distance (alpha=0.2): Raw={z_dist_raw:.1f}, Weighted={w_dist:.1f} ({pct_dist:.4f}%)")
    print(f"Total Objective Z:      {tot_obj:.1f}")

    # ------------------------------------------------------------------
    # 4. DETERMINISM EMPIRICAL TEST (5 REPEATED RUNS)
    # ------------------------------------------------------------------
    print("\n--- 4. SECTION 12: DETERMINISM EMPIRICAL TEST ---")
    det_results = []
    for d_i in range(5):
        res_d = cpsat_engine.solve(inc_b, dep_b, graph_engine)
        det_results.append((res_d.solver_status, res_d.total_unmet_demand_quantity, len(res_d.allocations), res_d.objective_value))
        print(f"Run {d_i+1}: Status={res_d.solver_status}, Unmet={res_d.total_unmet_demand_quantity}, Allocations={len(res_d.allocations)}, Obj={res_d.objective_value:.2f}")

    all_det_identical = all(r == det_results[0] for r in det_results)
    print(f"Empirically reproducible across 5 repeated runs: {all_det_identical}")

    # Export complete results to JSON
    output_package = {
        "timing_stats": timing_stats,
        "target_met": target_met,
        "scenarios": scenarios_results,
        "objective_scaling": {
            "Z_unmet": {"raw": z_unmet_raw, "weighted": w_unmet, "percentage": pct_unmet},
            "Z_penalty": {"raw": z_penalty_raw, "weighted": w_penalty, "percentage": pct_penalty},
            "Z_time": {"raw": z_time_raw, "weighted": w_time, "percentage": pct_time},
            "Z_distance": {"raw": z_dist_raw, "weighted": w_dist, "percentage": pct_dist},
            "total_objective": tot_obj
        },
        "determinism_verified": all_det_identical
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/PHASE5D_FORENSIC_RESULTS.json", "w") as f:
        json.dump(output_package, f, indent=2)

    print("\nForensic suite complete. Full report written to docs/PHASE5D_FORENSIC_RESULTS.json.")

if __name__ == "__main__":
    run_forensic_suite()
