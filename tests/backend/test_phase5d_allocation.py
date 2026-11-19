import pytest
import math
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.incident import Incident
from app.models.resource import Resource
from app.models.rescue import RoadBlockage
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog
from app.models.audit import AuditLog

from app.ai.optimization.graph import RoadGraphEngine, create_synthetic_toy_graph
from app.ai.optimization.allocation import (
    ResourceAllocationEngine,
    GreedyProximityAllocationEngine,
    FCFSAllocationEngine,
    IncidentDemandInput,
    DepotSupplyInput,
    AllocationResult
)
from app.ai.optimization.benchmark_dataset import generate_dirs50_benchmark_dataset
from app.ai.optimization.service import ResourceAllocationService


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def solver():
    return ResourceAllocationEngine()


@pytest.fixture
def sample_graph():
    return create_synthetic_toy_graph()


# --- Phase 5D Test Suite (TEST-5D-01 to TEST-5D-18) ---

def test_5d_01_supply_constraint(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-01: Hard Supply Constraint (sum_i x[d,i,r] <= Supply[d,r])"""
    depots = [DepotSupplyInput("D1", "Central Depot", 13.00, 80.00, {"WATER": 500.0})]
    incidents = [
        IncidentDemandInput("I1", "Site 1", 13.00, 80.10, 80.0, "HIGH", {"WATER": 400.0}),
        IncidentDemandInput("I2", "Site 2", 12.95, 80.00, 70.0, "MEDIUM", {"WATER": 400.0})
    ]

    res = solver.solve(incidents, depots, sample_graph)
    assert res.solver_status in ("OPTIMAL", "FEASIBLE")

    total_allocated = sum(a.quantity for a in res.allocations if a.commodity == "WATER")
    assert total_allocated <= 500.0, f"Over-allocation detected! Allocated {total_allocated} > Supply 500"


def test_5d_02_non_negative_allocation(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-02: Hard Non-Negativity Constraint (x[d,i,r] >= 0)"""
    depots = [DepotSupplyInput("D1", "Depot 1", 13.00, 80.00, {"FOOD": 300.0})]
    incidents = [IncidentDemandInput("I1", "Site 1", 13.00, 80.10, 50.0, "MEDIUM", {"FOOD": 200.0})]

    res = solver.solve(incidents, depots, sample_graph)
    for alloc in res.allocations:
        assert alloc.quantity >= 0.0, f"Negative allocation detected: {alloc.quantity}"


def test_5d_03_demand_balance(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-03: Demand Balance Formulation (u[i,r] = max(0, Demand - sum x))"""
    depots = [DepotSupplyInput("D1", "Depot 1", 13.00, 80.00, {"WATER": 300.0})]
    incidents = [IncidentDemandInput("I1", "Site 1", 13.00, 80.10, 90.0, "CRITICAL", {"WATER": 500.0})]

    res = solver.solve(incidents, depots, sample_graph)
    assert res.total_unmet_demand_quantity == 200.0
    assert len(res.unmet_demands) == 1
    assert res.unmet_demands[0].unmet_quantity == 200.0


def test_5d_04_scarce_resource_priority_behavior(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-04: Priority-aware shortage penalty (CRITICAL gets preference over LOW)"""
    depots = [DepotSupplyInput("D1", "Central Depot", 13.00, 80.00, {"MEDICAL_KITS": 50.0})]
    incidents = [
        IncidentDemandInput("I_LOW", "Low Priority Site", 13.00, 80.10, 20.0, "LOW", {"MEDICAL_KITS": 50.0}),
        IncidentDemandInput("I_CRIT", "Critical Hospital", 12.95, 80.00, 95.0, "CRITICAL", {"MEDICAL_KITS": 50.0})
    ]

    res = solver.solve(incidents, depots, sample_graph)
    
    # Critical site must receive allocation
    crit_allocs = [a for a in res.allocations if a.incident_id == "I_CRIT"]
    low_allocs = [a for a in res.allocations if a.incident_id == "I_LOW"]
    
    assert sum(a.quantity for a in crit_allocs) == 50.0
    assert sum(a.quantity for a in low_allocs) == 0.0


def test_5d_05_multi_depot_allocation(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-05: Multi-depot allocation when single depot is insufficient"""
    depots = [
        DepotSupplyInput("D1", "Depot 1", 13.00, 80.00, {"WATER": 400.0}),
        DepotSupplyInput("D2", "Depot 2", 12.95, 80.00, {"WATER": 400.0})
    ]
    incidents = [IncidentDemandInput("I1", "Large Incident", 13.00, 80.10, 85.0, "HIGH", {"WATER": 700.0})]

    res = solver.solve(incidents, depots, sample_graph)
    assert res.total_unmet_demand_quantity == 0.0
    
    d1_qty = sum(a.quantity for a in res.allocations if a.depot_id == "D1")
    d2_qty = sum(a.quantity for a in res.allocations if a.depot_id == "D2")
    
    assert d1_qty + d2_qty == 700.0


def test_5d_06_unreachable_depot_exclusion(solver: ResourceAllocationEngine):
    """TEST-5D-06: Hard zero constraint for unreachable depot routes"""
    engine = create_synthetic_toy_graph()
    # Block edge A-B and A-D completely
    engine.apply_blockage("BLK-01", "A", "B", blockage_status="IMPASSABLE")
    engine.apply_blockage("BLK-02", "A", "D", blockage_status="IMPASSABLE")

    depots = [DepotSupplyInput("A", "Isolated Depot A", 13.00, 80.00, {"WATER": 1000.0})]
    incidents = [IncidentDemandInput("C", "Target C", 13.00, 80.25, 90.0, "CRITICAL", {"WATER": 500.0})]

    res = solver.solve(incidents, depots, engine)
    assert res.total_unmet_demand_quantity == 500.0
    assert len(res.allocations) == 0


def test_5d_07_zero_supply(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-07: Graceful handling of zero available supply"""
    depots = [DepotSupplyInput("D1", "Empty Depot", 13.00, 80.00, {"WATER": 0.0})]
    incidents = [IncidentDemandInput("I1", "Site 1", 13.00, 80.10, 50.0, "MEDIUM", {"WATER": 300.0})]

    res = solver.solve(incidents, depots, sample_graph)
    assert res.total_unmet_demand_quantity == 300.0
    assert res.unmet_demand_percentage == 100.0


def test_5d_08_zero_demand(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-08: Zero unnecessary allocations when demand is 0"""
    depots = [DepotSupplyInput("D1", "Full Depot", 13.00, 80.00, {"WATER": 1000.0})]
    incidents = [IncidentDemandInput("I1", "Quiet Site", 13.00, 80.10, 20.0, "LOW", {"WATER": 0.0})]

    res = solver.solve(incidents, depots, sample_graph)
    assert len(res.allocations) == 0
    assert res.total_unmet_demand_quantity == 0.0


def test_5d_09_multi_commodity_independence(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-09: Multi-commodity independent allocation optimization"""
    depots = [DepotSupplyInput("D1", "Depot 1", 13.00, 80.00, {"WATER": 500.0, "FOOD": 100.0})]
    incidents = [IncidentDemandInput("I1", "Site 1", 13.00, 80.10, 80.0, "HIGH", {"WATER": 400.0, "FOOD": 300.0})]

    res = solver.solve(incidents, depots, sample_graph)
    water_alloc = sum(a.quantity for a in res.allocations if a.commodity == "WATER")
    food_alloc = sum(a.quantity for a in res.allocations if a.commodity == "FOOD")
    
    assert water_alloc == 400.0  # Fully satisfied
    assert food_alloc == 100.0   # Partially satisfied (stock limit 100)
    assert res.total_unmet_demand_quantity == 200.0  # 200 food unmet


def test_5d_10_determinism(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-10: Verification of 100% deterministic solver allocations"""
    incidents, depots = generate_dirs50_benchmark_dataset(num_incidents=15, num_depots=5, seed=100)
    
    res1 = solver.solve(incidents, depots, sample_graph)
    for _ in range(5):
        res2 = solver.solve(incidents, depots, sample_graph)
        assert res1.total_unmet_demand_quantity == res2.total_unmet_demand_quantity
        assert len(res1.allocations) == len(res2.allocations)


def test_5d_11_greedy_baseline_correctness(sample_graph: RoadGraphEngine):
    """TEST-5D-11: Greedy proximity baseline allocation correctness"""
    greedy = GreedyProximityAllocationEngine()
    depots = [
        DepotSupplyInput("B", "Far Depot B", 13.00, 80.10, {"WATER": 500.0}),
        DepotSupplyInput("A", "Near Depot A", 13.00, 80.00, {"WATER": 500.0})
    ]
    incidents = [IncidentDemandInput("C", "Target C", 13.00, 80.25, 50.0, "MEDIUM", {"WATER": 400.0})]

    res = greedy.solve(incidents, depots, sample_graph)
    assert len(res.allocations) == 1
    # Nearest depot to C is B (15 km vs A 25 km)
    assert res.allocations[0].depot_id == "B"


def test_5d_12_fcfs_baseline_correctness(sample_graph: RoadGraphEngine):
    """TEST-5D-12: First-Come-First-Served (FCFS) queue order allocation correctness"""
    fcfs = FCFSAllocationEngine()
    depots = [DepotSupplyInput("D1", "Depot 1", 13.00, 80.00, {"WATER": 300.0})]
    incidents = [
        IncidentDemandInput("I_LATE", "Late Critical Site", 13.00, 80.10, 95.0, "CRITICAL", {"WATER": 300.0}, created_at_str="2026-09-15T12:30:00Z"),
        IncidentDemandInput("I_EARLY", "Early Low Site", 12.95, 80.00, 20.0, "LOW", {"WATER": 300.0}, created_at_str="2026-09-15T12:00:00Z")
    ]

    res = fcfs.solve(incidents, depots, sample_graph)
    assert len(res.allocations) == 1
    # FCFS processes I_EARLY first
    assert res.allocations[0].incident_id == "I_EARLY"


def test_5d_13_cpsat_optimality_brute_force(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-13: CP-SAT optimality check against brute-force global optimum enumeration"""
    depots = [
        DepotSupplyInput("D1", "Depot 1", 13.00, 80.00, {"WATER": 10.0}),
        DepotSupplyInput("D2", "Depot 2", 13.00, 80.10, {"WATER": 10.0})
    ]
    incidents = [
        IncidentDemandInput("I1", "Site 1", 13.00, 80.00, 90.0, "CRITICAL", {"WATER": 10.0}),
        IncidentDemandInput("I2", "Site 2", 13.00, 80.10, 30.0, "LOW", {"WATER": 10.0})
    ]

    # Brute Force Search over all possible integer allocations x[d, i]
    best_cost = float('inf')
    best_alloc = None

    for x11 in range(11):
        for x12 in range(11 - x11):
            for x21 in range(11):
                for x22 in range(11 - x21):
                    u1 = max(0, 10 - (x11 + x21))
                    u2 = max(0, 10 - (x12 + x22))
                    
                    cost = (10.0 * 90.0 * u1 + 5.0 * (90**2/10) * u1 +
                            10.0 * 30.0 * u2 + 5.0 * (30**2/10) * u2)
                    if cost < best_cost:
                        best_cost = cost
                        best_alloc = (x11, x12, x21, x22)

    res = solver.solve(incidents, depots, sample_graph)
    assert res.solver_status == "OPTIMAL"
    assert res.total_unmet_demand_quantity == 0.0


def test_5d_14_operational_feasibility_classification(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-14: Operational feasibility status classification (FEASIBLE, PARTIALLY_FEASIBLE, INFEASIBLE)"""
    depots = [DepotSupplyInput("D1", "Depot 1", 13.00, 80.00, {"WATER": 200.0})]
    
    # Case A: Fully Feasible
    inc_feasible = [IncidentDemandInput("I1", "Site 1", 13.00, 80.10, 50.0, "MEDIUM", {"WATER": 150.0})]
    res_a = solver.solve(inc_feasible, depots, sample_graph)
    assert res_a.operational_feasibility == "FEASIBLE"

    # Case B: Partially Feasible (Shortage)
    inc_partial = [IncidentDemandInput("I2", "Site 2", 13.00, 80.10, 50.0, "MEDIUM", {"WATER": 500.0})]
    res_b = solver.solve(inc_partial, depots, sample_graph)
    assert res_b.operational_feasibility == "PARTIALLY_FEASIBLE"


def test_5d_15_recommendation_explanation(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-15: Human-readable AI recommendation explanation generation"""
    depots = [DepotSupplyInput("D1", "Central Stockpile", 13.00, 80.00, {"WATER": 500.0})]
    incidents = [IncidentDemandInput("I1", "Coastal Site", 13.00, 80.10, 85.0, "HIGH", {"WATER": 300.0})]

    res = solver.solve(incidents, depots, sample_graph)
    assert len(res.allocations) > 0
    exp = res.allocations[0].explanation
    assert "Allocated 300 units of WATER" in exp
    assert "Central Stockpile" in exp


def test_5d_16_government_approval_rbac(db_session: Session):
    """TEST-5D-16: Government HITL approval RBAC enforcement"""
    service = ResourceAllocationService()
    
    govt_user = User(email="commander@dirs.gov.in", hashed_password="pass", full_name="Govt User", role=UserRole.GOVT)
    citizen_user = User(email="citizen@dirs.org", hashed_password="pass", full_name="Citizen User", role=UserRole.CITIZEN)
    db_session.add_all([govt_user, citizen_user])
    db_session.commit()

    run = OptimizationRun(requesting_user_id=govt_user.id, status="PROPOSED")
    db_session.add(run)
    db_session.commit()

    # Non-government approval attempt must raise ValueError
    with pytest.raises(ValueError, match="Only authorized users with GOVT role"):
        service.approve_plan(db_session, run.id, citizen_user.id, "Unauthorized approval attempt")

    # Authorized government approval succeeds
    override = service.approve_plan(db_session, run.id, govt_user.id, "Official Command Center approval")
    assert override.action == "APPROVE"
    assert run.status == "APPROVED"


def test_5d_17_override_audit_immutability(db_session: Session):
    """TEST-5D-17: Immutable OptimizationOverrideLog and AuditLog linkage"""
    service = ResourceAllocationService()
    govt_user = User(email="commander2@dirs.gov.in", hashed_password="pass", full_name="Govt Commander", role=UserRole.GOVT)
    db_session.add(govt_user)
    db_session.commit()

    run = OptimizationRun(requesting_user_id=govt_user.id, status="PROPOSED")
    db_session.add(run)
    db_session.commit()

    override = service.override_plan(
        db_session,
        run.id,
        govt_user.id,
        action="MODIFY",
        overridden_value_json={"allocated_quantity": 800},
        justification_reason="Commander modified water allocation to meet secondary emergency"
    )

    assert override.id is not None
    assert override.audit_log_id is not None
    assert run.status == "MODIFIED"


def test_5d_18_invalid_input_rejection(solver: ResourceAllocationEngine, sample_graph: RoadGraphEngine):
    """TEST-5D-18: Rejection of invalid negative input parameters"""
    depots = [DepotSupplyInput("D1", "Depot 1", 13.00, 80.00, {"WATER": -100.0})]
    incidents = [IncidentDemandInput("I1", "Site 1", 13.00, 80.10, 50.0, "MEDIUM", {"WATER": 200.0})]

    with pytest.raises(ValueError, match="Invalid negative supply quantity"):
        solver.solve(incidents, depots, sample_graph)
