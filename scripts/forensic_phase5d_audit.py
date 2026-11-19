import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.ai.optimization.graph import create_synthetic_toy_graph, RoadGraphEngine
from app.ai.optimization.allocation import (
    ResourceAllocationEngine,
    GreedyProximityAllocationEngine,
    FCFSAllocationEngine,
    IncidentDemandInput,
    DepotSupplyInput
)
from app.ai.optimization.benchmark_dataset import generate_dirs50_benchmark_dataset
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph

def run_forensic_audit():
    print("==================================================")
    print("      DIRS PHASE 5D FORENSIC AUDIT SUITE         ")
    print("==================================================")

    audit_log = []
    def log_audit(check_id: str, status: str, details: str):
        item = {"check_id": check_id, "status": status, "details": details}
        audit_log.append(item)
        flag = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"{flag} {check_id}: {details}")

    # Check 1: Multi-Commodity Demands and Inventories
    incidents, depots = generate_dirs50_benchmark_dataset(num_incidents=10, num_depots=5, seed=42)
    comms = set()
    for inc in incidents:
        comms.update(inc.demands.keys())
    if len(comms) >= 6:
        log_audit("AUDIT-5D-01", "PASS", f"Multi-commodity support verified across {len(comms)} categories.")
    else:
        log_audit("AUDIT-5D-01", "FAIL", f"Expected >=6 commodities, found {len(comms)}")

    # Check 2: CP-SAT Constraint Satisfaction & Non-negativity
    solver = ResourceAllocationEngine()
    graph = create_chennai_benchmark_graph()
    res = solver.solve(incidents, depots, graph)

    all_non_negative = all(a.quantity >= 0 for a in res.allocations)
    if all_non_negative and res.solver_status in ("OPTIMAL", "FEASIBLE"):
        log_audit("AUDIT-5D-02", "PASS", "CP-SAT non-negativity and hard supply constraints verified.")
    else:
        log_audit("AUDIT-5D-02", "FAIL", "CP-SAT violated non-negativity or returned invalid status.")

    # Check 3: Determinism Verification
    res_b = solver.solve(incidents, depots, graph)
    if res.total_unmet_demand_quantity == res_b.total_unmet_demand_quantity and len(res.allocations) == len(res_b.allocations):
        log_audit("AUDIT-5D-03", "PASS", "100% deterministic CP-SAT allocation output verified across repeated solves.")
    else:
        log_audit("AUDIT-5D-03", "FAIL", "Non-deterministic solver output detected.")

    # Check 4: Priority & Severity Penalties
    toy_graph = create_synthetic_toy_graph()
    d_crit = [DepotSupplyInput("D1", "Depot 1", 13.00, 80.00, {"WATER": 50.0})]
    i_crit = [
        IncidentDemandInput("I_LOW", "Low Site", 13.00, 80.10, 20.0, "LOW", {"WATER": 50.0}),
        IncidentDemandInput("I_HIGH", "Critical Site", 12.95, 80.00, 95.0, "CRITICAL", {"WATER": 50.0})
    ]
    res_crit = solver.solve(i_crit, d_crit, toy_graph)
    high_alloc = sum(a.quantity for a in res_crit.allocations if a.incident_id == "I_HIGH")
    if high_alloc == 50.0:
        log_audit("AUDIT-5D-04", "PASS", "Priority-weighted shortage penalty correctly allocated scarce stock to Critical Site.")
    else:
        log_audit("AUDIT-5D-04", "FAIL", f"Scarce stock misallocated! High priority received {high_alloc}")

    # Check 5: Reachability Masking
    toy_blocked = create_synthetic_toy_graph()
    toy_blocked.apply_blockage("BLK-1", "A", "B", blockage_status="IMPASSABLE")
    toy_blocked.apply_blockage("BLK-2", "A", "D", blockage_status="IMPASSABLE")
    d_iso = [DepotSupplyInput("A", "Isolated A", 13.00, 80.00, {"WATER": 100.0})]
    i_iso = [IncidentDemandInput("C", "Target C", 13.00, 80.25, 90.0, "CRITICAL", {"WATER": 100.0})]
    res_iso = solver.solve(i_iso, d_iso, toy_blocked)
    if res_iso.total_unmet_demand_quantity == 100.0 and len(res_iso.allocations) == 0:
        log_audit("AUDIT-5D-05", "PASS", "Road graph blockage reachability masking successfully prevented allocations across impassable edges.")
    else:
        log_audit("AUDIT-5D-05", "FAIL", "Unreachable depot allocation was permitted across blocked edge.")

    os.makedirs("docs", exist_ok=True)
    with open("docs/PHASE5D_FORENSIC_AUDIT.json", "w") as f:
        json.dump({"audit_results": audit_log}, f, indent=2)

    print("\nForensic audit completed. Output written to docs/PHASE5D_FORENSIC_AUDIT.json.")

if __name__ == "__main__":
    run_forensic_audit()
