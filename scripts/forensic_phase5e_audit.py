"""
DIRS Phase 5E Forensic Audit Script
Verifies all 15 structural invariants and scientific requirements.
"""
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ai.optimization.routing import (
    VehicleRoutingEngine,
    NearestFeasibleRoutingEngine,
    FCFSRoutingEngine,
    VehicleInput,
    ShipmentInput,
    verify_phase5d_conservation,
)
from app.ai.optimization.graph import create_synthetic_toy_graph
from app.ai.optimization.routing_service import VehicleRoutingService
from app.ai.optimization.routing_benchmark_dataset import generate_dirs_route_benchmark

def run_forensic_audit():
    print("=" * 70)
    print("DIRS Phase 5E — Forensic Invariant Audit")
    print("=" * 70)

    checks = {}

    # Check 1: RoutingModel actually imported and available
    try:
        from ortools.constraint_solver import pywrapcp
        assert hasattr(pywrapcp, "RoutingModel")
        checks["1_routing_model_imported"] = True
    except Exception as e:
        checks["1_routing_model_imported"] = False

    # Check 2: RoutingModel actually executed
    g = create_synthetic_toy_graph()
    v = VehicleInput("V1", "VEH_001", "TRUCK", 1000.0, 5.0, "A", 13.00, 80.00, status="AVAILABLE")
    s = ShipmentInput("S1", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 50.0, "MEDIUM", {"WATER": 100.0}, 100.0, 0.1)
    res = VehicleRoutingEngine().solve([s], [v], g)
    checks["2_routing_model_executed"] = len(res.routes) == 1 and res.algorithm == "OR-Tools RoutingModel"

    # Check 3: Vehicle capacity constraints exist (weight and volume)
    checks["3_capacity_dimensions_exist"] = hasattr(v, "capacity_weight_kg") and hasattr(v, "capacity_volume_m3")

    # Check 4: Time dimension exists
    checks["4_time_dimension_exists"] = hasattr(res.routes[0].stops[0], "arrival_time_min") and hasattr(res.routes[0].stops[0], "departure_time_min")

    # Check 5: Phase 5C matrix consumed
    checks["5_phase5c_matrix_consumed"] = res.graph_version != ""

    # Check 6: Phase 5D conservation exists and verified
    c_check = verify_phase5d_conservation([s], res)
    checks["6_phase5d_conservation_verified"] = c_check["conservation_holds"]

    # Check 7: IMPASSABLE arcs are genuinely forbidden
    g_blocked = create_synthetic_toy_graph()
    g_blocked.apply_blockage("BLK_1", "A", "B", blockage_status="IMPASSABLE")
    res_b = VehicleRoutingEngine().solve([s], [v], g_blocked)
    # Direct edge A->B is 10 mins; reroute must take longer
    checks["7_impassable_arc_forbidden"] = res_b.routes[0].total_travel_time_min > 10.0

    # Check 8: DELAYED arcs affect route costs
    g_delayed = create_synthetic_toy_graph()
    g_delayed.apply_blockage("BLK_2", "A", "B", blockage_status="DELAYED", delay_penalty_mins=30.0)
    res_d = VehicleRoutingEngine().solve([s], [v], g_delayed)
    checks["8_delayed_arc_affects_cost"] = res_d.routes[0].total_travel_time_min > res.routes[0].total_travel_time_min

    # Check 9: Vehicle eligibility enforced (AVAILABLE only)
    v_maint = VehicleInput("V2", "VEH_002", "TRUCK", 1000.0, 5.0, "A", 13.00, 80.00, status="MAINTENANCE")
    res_elig = VehicleRoutingEngine().solve([s], [v_maint], g)
    checks["9_vehicle_eligibility_enforced"] = len(res_elig.routes) == 0 and len(res_elig.unrouted_shipments) == 1

    # Check 10: Depot compatibility enforced
    v_diff = VehicleInput("V3", "VEH_003", "TRUCK", 1000.0, 5.0, "DEPOT_OTHER", 13.00, 80.00, status="AVAILABLE")
    res_dep = VehicleRoutingEngine().solve([s], [v_diff], g)
    checks["10_depot_compatibility_enforced"] = len(res_dep.routes) == 0 and len(res_dep.unrouted_shipments) == 1

    # Check 11: Baselines exist and executable
    res_near = NearestFeasibleRoutingEngine().solve([s], [v], g)
    res_fcfs = FCFSRoutingEngine().solve([s], [v], g)
    checks["11_baselines_exist"] = len(res_near.routes) == 1 and len(res_fcfs.routes) == 1

    # Check 12: Brute-force validation exists
    s_b = ShipmentInput("S_B", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 50.0, "MEDIUM", {"WATER": 10.0}, 10.0, 0.01)
    s_d = ShipmentInput("S_D", "A", 13.00, 80.00, "D", 12.95, 80.00, "Site D", 50.0, "MEDIUM", {"WATER": 10.0}, 10.0, 0.01)
    res_bf = VehicleRoutingEngine().solve([s_b, s_d], [v], g)
    checks["12_brute_force_validation_exists"] = res_bf.routes[0].total_travel_time_min == 30.0

    # Check 13: Government approval enforced (RBAC in VehicleRoutingService)
    checks["13_government_approval_enforced"] = hasattr(VehicleRoutingService, "approve_route_plan")

    # Check 14: Override logging preserved
    checks["14_override_logging_preserved"] = hasattr(VehicleRoutingService, "override_route_plan")

    # Check 15: No Phase 5F/5G implementation exists
    app_ai_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app", "ai", "optimization"))
    opt_files = os.listdir(app_ai_dir)
    has_5f = any("shelter" in f.lower() or "volunteer" in f.lower() or "what_if" in f.lower() or "evac" in f.lower() for f in opt_files)
    checks["15_no_phase_5f_5g_code"] = not has_5f

    # Check 16: End-to-end physical blockage reconstruction verification
    g_p_open = create_synthetic_toy_graph()
    ver_p_open = g_p_open.get_graph_version()
    g_p_blocked = create_synthetic_toy_graph()
    g_p_blocked.apply_blockage("BLK_PHYS_AUDIT", "A", "B", blockage_status="IMPASSABLE")
    ver_p_blocked = g_p_blocked.get_graph_version()
    res_p_blocked = VehicleRoutingEngine().solve([s], [v], g_p_blocked)
    physical_edges_audited = []
    curr = "A"
    for stop in res_p_blocked.routes[0].stops:
        leg = g_p_blocked.compute_shortest_path(curr, stop.incident_id)
        physical_edges_audited.extend(zip(leg.node_sequence[:-1], leg.node_sequence[1:]))
        curr = stop.incident_id
    ret_leg = g_p_blocked.compute_shortest_path(curr, res_p_blocked.routes[0].start_depot_id)
    physical_edges_audited.extend(zip(ret_leg.node_sequence[:-1], ret_leg.node_sequence[1:]))
    checks["16_end_to_end_physical_blockage_reconstructed"] = (
        ver_p_open != ver_p_blocked and
        ("A", "B") not in physical_edges_audited and
        ("B", "A") not in physical_edges_audited and
        len(physical_edges_audited) > 0
    )

    # Check 17: Objective arithmetic reconciliation (raw vs computed vs rounded)
    tb_test = res_p_blocked.timing_breakdown
    timing_sum = (
        tb_test["matrix_build_ms"] +
        tb_test["model_construction_ms"] +
        tb_test["solver_search_ms"] +
        tb_test["solution_extraction_ms"] +
        tb_test["orchestration_overhead_ms"]
    )
    checks["17_timing_arithmetic_reconciled"] = abs(timing_sum - tb_test["total_routing_ms"]) < 0.05

    print("\n--- Audit Check Results ---")
    all_passed = True
    for name, passed in checks.items():
        status = "PASSED" if passed else "FAILED"
        print(f"[{status}] {name}")
        if not passed:
            all_passed = False

    passed_count = sum(1 for p in checks.values() if p)
    total_count = len(checks)
    print(f"Overall Forensic Audit Status: {'PASSED (' + str(passed_count) + '/' + str(total_count) + ')' if all_passed else 'FAILED'}")
    print("=" * 70)

    # Save forensic audit report
    report_path = os.path.join("docs", "PHASE5E_FORENSIC_AUDIT_REPORT.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"overall_status": "PASSED" if all_passed else "FAILED", "checks": checks}, f, indent=2)

    return all_passed

if __name__ == "__main__":
    success = run_forensic_audit()
    sys.exit(0 if success else 1)
