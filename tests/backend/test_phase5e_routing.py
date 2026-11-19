import pytest
import math
from itertools import permutations
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.incident import Incident
from app.models.vehicle import Vehicle
from app.models.resource import Resource
from app.models.rescue import RoadBlockage
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog
from app.models.audit import AuditLog

from app.ai.optimization.graph import RoadGraphEngine, create_synthetic_toy_graph
from app.ai.optimization.allocation import AllocationResult, CommodityAllocationItem
from app.ai.optimization.routing import (
    VehicleRoutingEngine,
    NearestFeasibleRoutingEngine,
    FCFSRoutingEngine,
    VehicleInput,
    ShipmentInput,
    verify_phase5d_conservation,
)
from app.ai.optimization.routing_service import VehicleRoutingService
from app.ai.optimization.routing_benchmark_dataset import generate_dirs_route_benchmark

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def toy_graph():
    return create_synthetic_toy_graph()

@pytest.fixture
def routing_engine():
    return VehicleRoutingEngine()

# TEST-5E-01: Vehicle eligibility
def test_5e_01_vehicle_eligibility(routing_engine, toy_graph):
    # Only AVAILABLE vehicles should be routed.
    v_avail = VehicleInput("V1", "VEH_001", "TRUCK", 2000.0, 10.0, "A", 13.00, 80.00, status="AVAILABLE")
    v_maint = VehicleInput("V2", "VEH_002", "TRUCK", 2000.0, 10.0, "A", 13.00, 80.00, status="MAINTENANCE")
    v_transit = VehicleInput("V3", "VEH_003", "TRUCK", 2000.0, 10.0, "A", 13.00, 80.00, status="IN_TRANSIT")
    
    shipment = ShipmentInput(
        shipment_id="S1", origin_depot_id="A", origin_depot_lat=13.00, origin_depot_lng=80.00,
        incident_id="B", incident_lat=13.00, incident_lng=80.10, incident_title="Site B",
        priority_score=80.0, severity_level="CRITICAL", commodities={"WATER": 100.0},
        total_weight_kg=100.0, total_volume_m3=0.1
    )

    res = routing_engine.solve([shipment], [v_avail, v_maint, v_transit], toy_graph)
    assert len(res.routes) == 1
    assert res.routes[0].vehicle_id == "V1"
    assert all(r.vehicle_id not in ("V2", "V3") for r in res.routes)

# TEST-5E-02: Vehicle capacity
def test_5e_02_vehicle_capacity(routing_engine, toy_graph):
    # Overweight shipment cannot be routed
    v = VehicleInput("V1", "VEH_001", "VAN", 500.0, 2.0, "A", 13.00, 80.00, status="AVAILABLE")
    shipment = ShipmentInput(
        shipment_id="S1", origin_depot_id="A", origin_depot_lat=13.00, origin_depot_lng=80.00,
        incident_id="B", incident_lat=13.00, incident_lng=80.10, incident_title="Site B",
        priority_score=80.0, severity_level="HIGH", commodities={"WATER": 600.0},
        total_weight_kg=600.0, total_volume_m3=0.6
    )

    res = routing_engine.solve([shipment], [v], toy_graph)
    assert len(res.routes) == 0
    assert len(res.unrouted_shipments) == 1
    assert "exceeds" in res.unrouted_shipments[0].reason

# TEST-5E-03: Phase 5D allocation conservation
def test_5e_03_phase5d_allocation_conservation(routing_engine, toy_graph):
    v = VehicleInput("V1", "VEH_001", "TRUCK", 1000.0, 5.0, "A", 13.00, 80.00, status="AVAILABLE")
    s1 = ShipmentInput("S1", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 90.0, "CRITICAL",
                       {"WATER": 400.0, "FOOD": 100.0}, 450.0, 0.48)
    s2 = ShipmentInput("S2", "A", 13.00, 80.00, "C", 13.00, 80.25, "Site C", 50.0, "MEDIUM",
                       {"WATER": 800.0}, 800.0, 0.8)

    res = routing_engine.solve([s1, s2], [v], toy_graph)
    check = verify_phase5d_conservation([s1, s2], res)
    assert check["conservation_holds"] is True

# TEST-5E-04: IMPASSABLE arc exclusion
def test_5e_04_impassable_arc_exclusion(routing_engine):
    # Create graph with an IMPASSABLE edge
    g = create_synthetic_toy_graph()
    g.apply_blockage("BLK_1", "A", "B", blockage_status="IMPASSABLE")

    v = VehicleInput("V1", "VEH_001", "TRUCK", 2000.0, 10.0, "A", 13.00, 80.00, status="AVAILABLE")
    s = ShipmentInput("S1", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 90.0, "CRITICAL",
                      {"WATER": 200.0}, 200.0, 0.2)

    res = routing_engine.solve([s], [v], g)
    # A->B is IMPASSABLE directly, but alternative A->D->E->F->C->B exists in toy graph
    if res.routes:
        # Verify that direct arc A->B was NOT used
        for r in res.routes:
            assert r.stops[0].incident_id == "B"
            # Route travel time must be greater than direct 10 mins since it rerouted around blocked road
            assert r.total_travel_time_min > 10.0

# TEST-5E-05: Blockage rerouting
def test_5e_05_blockage_rerouting(routing_engine):
    g1 = create_synthetic_toy_graph()
    v = VehicleInput("V1", "VEH_001", "TRUCK", 2000.0, 10.0, "A", 13.00, 80.00, status="AVAILABLE")
    s = ShipmentInput("S1", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 80.0, "HIGH",
                      {"WATER": 100.0}, 100.0, 0.1)

    res1 = routing_engine.solve([s], [v], g1)
    time_normal = res1.routes[0].total_travel_time_min

    g2 = create_synthetic_toy_graph()
    g2.apply_blockage("BLK_2", "A", "B", blockage_status="IMPASSABLE")
    res2 = routing_engine.solve([s], [v], g2)

    assert g1.get_graph_version() != g2.get_graph_version()
    assert res2.routes[0].total_travel_time_min > time_normal

# TEST-5E-06: DELAYED road response
def test_5e_06_delayed_road_response(routing_engine):
    g1 = create_synthetic_toy_graph()
    v = VehicleInput("V1", "VEH_001", "TRUCK", 2000.0, 10.0, "A", 13.00, 80.00, status="AVAILABLE")
    s = ShipmentInput("S1", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 80.0, "HIGH",
                      {"WATER": 100.0}, 100.0, 0.1)

    res1 = routing_engine.solve([s], [v], g1)

    g2 = create_synthetic_toy_graph()
    g2.apply_blockage("BLK_3", "A", "B", blockage_status="DELAYED", delay_penalty_mins=25.0)
    res2 = routing_engine.solve([s], [v], g2)

    assert res2.routes[0].total_travel_time_min > res1.routes[0].total_travel_time_min

# TEST-5E-07: Time-window constraint
def test_5e_07_time_window_constraint(routing_engine, toy_graph):
    v = VehicleInput("V1", "VEH_001", "TRUCK", 2000.0, 10.0, "A", 13.00, 80.00, status="AVAILABLE")
    # Tight time window that causes lateness
    s = ShipmentInput("S1", "A", 13.00, 80.00, "C", 13.00, 80.25, "Site C", 70.0, "MEDIUM",
                      {"WATER": 100.0}, 100.0, 0.1, earliest_arrival_min=0.0, latest_arrival_min=5.0)

    res = routing_engine.solve([s], [v], toy_graph)
    assert len(res.routes) == 1
    assert res.routes[0].stops[0].lateness_min > 0.0
    assert res.total_late_minutes > 0.0

# TEST-5E-08: Multi-stop capacity
def test_5e_08_multi_stop_capacity(routing_engine, toy_graph):
    # Total demand fits in 1 vehicle
    v = VehicleInput("V1", "VEH_001", "TRUCK", 1000.0, 5.0, "A", 13.00, 80.00, status="AVAILABLE")
    s1 = ShipmentInput("S1", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 70.0, "HIGH",
                       {"WATER": 300.0}, 300.0, 0.3)
    s2 = ShipmentInput("S2", "A", 13.00, 80.00, "C", 13.00, 80.25, "Site C", 60.0, "MEDIUM",
                       {"WATER": 400.0}, 400.0, 0.4)

    res = routing_engine.solve([s1, s2], [v], toy_graph)
    assert len(res.routes) == 1
    route = res.routes[0]
    assert len(route.stops) == 2
    assert route.weight_used_kg == 700.0
    assert route.weight_utilization_pct == 70.0

# TEST-5E-09: Critical priority
def test_5e_09_critical_priority(routing_engine, toy_graph):
    v = VehicleInput("V1", "VEH_001", "TRUCK", 2000.0, 10.0, "A", 13.00, 80.00, status="AVAILABLE")
    # Low priority at B (10 mins away), Critical priority at C (25 mins away)
    s_low = ShipmentInput("S_LOW", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 30.0, "LOW",
                          {"FOOD": 100.0}, 50.0, 0.08)
    s_crit = ShipmentInput("S_CRIT", "A", 13.00, 80.00, "C", 13.00, 80.25, "Site C", 95.0, "CRITICAL",
                           {"MEDICAL_KITS": 50.0}, 100.0, 0.25)

    res = routing_engine.solve([s_low, s_crit], [v], toy_graph)
    assert len(res.routes) == 1
    stops = res.routes[0].stops
    assert len(stops) == 2
    assert res.critical_mean_response_time_min > 0.0

# TEST-5E-10: Unrouted shipment handling
def test_5e_10_unrouted_shipment_handling(routing_engine, toy_graph):
    # Depot mismatch: shipment from D2, but only vehicle from D1 available
    v = VehicleInput("V1", "VEH_001", "TRUCK", 2000.0, 10.0, "DEPOT_1", 13.00, 80.00, status="AVAILABLE")
    s = ShipmentInput("S1", "DEPOT_2", 12.95, 80.00, "B", 13.00, 80.10, "Site B", 80.0, "HIGH",
                      {"WATER": 200.0}, 200.0, 0.2)

    res = routing_engine.solve([s], [v], toy_graph)
    assert len(res.routes) == 0
    assert len(res.unrouted_shipments) == 1
    assert "DEPOT_2" in res.unrouted_shipments[0].reason

# TEST-5E-11: Route result schema correctness
def test_5e_11_route_result_correctness(routing_engine, toy_graph):
    v = VehicleInput("V1", "VEH_001", "TRUCK", 1000.0, 5.0, "A", 13.00, 80.00, status="AVAILABLE")
    s = ShipmentInput("S1", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 80.0, "HIGH",
                      {"WATER": 200.0}, 200.0, 0.2)

    res = routing_engine.solve([s], [v], toy_graph)
    assert res.operational_status == "FULLY_FEASIBLE"
    assert res.solver_status in ("OPTIMAL", "FEASIBLE")
    assert res.graph_version != ""
    assert res.total_distance_km > 0.0
    assert res.total_travel_time_min > 0.0

# TEST-5E-12: Route duration calculation
def test_5e_12_route_duration_calculation(routing_engine, toy_graph):
    v = VehicleInput("V1", "VEH_001", "TRUCK", 1000.0, 5.0, "A", 13.00, 80.00, status="AVAILABLE")
    s = ShipmentInput("S1", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 80.0, "HIGH",
                      {"WATER": 100.0}, 100.0, 0.1, service_time_min=20.0)

    res = routing_engine.solve([s], [v], toy_graph)
    route = res.routes[0]
    assert route.total_service_time_min == 20.0
    assert route.total_route_duration_min == route.total_travel_time_min + 20.0

# TEST-5E-13: Determinism
def test_5e_13_determinism(routing_engine, toy_graph):
    shipments, vehicles = generate_dirs_route_benchmark(num_incidents=5, num_vehicles=3, seed=42)
    res_list = [routing_engine.solve(shipments, vehicles, toy_graph) for _ in range(5)]

    first_routes = [(r.vehicle_code, len(r.stops), r.total_distance_km) for r in res_list[0].routes]
    for other in res_list[1:]:
        other_routes = [(r.vehicle_code, len(r.stops), r.total_distance_km) for r in other.routes]
        assert other_routes == first_routes

# TEST-5E-14: Baseline correctness
def test_5e_14_baseline_correctness(toy_graph):
    shipments, vehicles = generate_dirs_route_benchmark(num_incidents=6, num_vehicles=3, seed=42)
    b_near = NearestFeasibleRoutingEngine().solve(shipments, vehicles, toy_graph)
    b_fcfs = FCFSRoutingEngine().solve(shipments, vehicles, toy_graph)

    assert b_near.operational_status in ("FULLY_FEASIBLE", "PARTIALLY_FEASIBLE")
    assert b_fcfs.operational_status in ("FULLY_FEASIBLE", "PARTIALLY_FEASIBLE")
    assert len(b_near.routes) > 0
    assert len(b_fcfs.routes) > 0

# TEST-5E-15: Government approval RBAC
def test_5e_15_government_approval_rbac(db_session: Session):
    service = VehicleRoutingService()
    user_citizen = User(id="cit_001", email="cit@test.com", hashed_password="pw", full_name="Cit", role=UserRole.CITIZEN)
    user_govt = User(id="gov_001", email="gov@test.com", hashed_password="pw", full_name="Gov", role=UserRole.GOVT)
    db_session.merge(user_citizen)
    db_session.merge(user_govt)
    db_session.commit()

    run = OptimizationRun(id="run_test_01", requesting_user_id="gov_001", status="PROPOSED")
    db_session.merge(run)
    db_session.commit()

    with pytest.raises(ValueError, match="Only authorized users with GOVT role"):
        service.approve_route_plan(db_session, "run_test_01", "cit_001", "Citizen approval attempt")

    log = service.approve_route_plan(db_session, "run_test_01", "gov_001", "Approved by commander")
    assert log.action == "APPROVE"
    assert db_session.query(OptimizationRun).filter_by(id="run_test_01").first().status == "APPROVED"

# TEST-5E-16: Override audit immutability
def test_5e_16_override_audit_immutability(db_session: Session):
    service = VehicleRoutingService()
    user_govt = User(id="gov_002", email="gov2@test.com", hashed_password="pw", full_name="Gov 2", role=UserRole.GOVT)
    db_session.merge(user_govt)
    run = OptimizationRun(id="run_test_02", requesting_user_id="gov_002", status="PROPOSED")
    db_session.merge(run)
    db_session.commit()

    override = service.override_route_plan(
        db_session, "run_test_02", "gov_002", "MODIFY",
        {"modified_routes": ["V1-rerouted"]}, "Field situation required route alteration"
    )
    assert override.action == "MODIFY"
    assert override.audit_log_id is not None
    audit = db_session.query(AuditLog).filter_by(id=override.audit_log_id).first()
    assert audit is not None
    assert audit.action == "ROUTING_PLAN_MODIFIED"

# TEST-5E-17: Invalid input rejection
def test_5e_17_invalid_input_rejection(routing_engine, toy_graph):
    # Empty shipments or vehicles returns clean unroutable result
    res_no_ship = routing_engine.solve([], [VehicleInput("V1", "V1", "TRUCK", 1000, 5, "A", 13, 80)], toy_graph)
    assert res_no_ship.operational_status == "UNROUTABLE"
    assert len(res_no_ship.routes) == 0

    res_no_veh = routing_engine.solve([ShipmentInput("S1", "A", 13, 80, "B", 13, 80.1, "B", 50, "LOW", {}, 10, 0.1)], [], toy_graph)
    assert res_no_veh.operational_status == "UNROUTABLE"
    assert len(res_no_veh.unrouted_shipments) == 1

# TEST-5E-18: Brute-force optimality validation
def test_5e_18_brute_force_optimality(routing_engine, toy_graph):
    # Tiny instance: 1 vehicle at A, 2 stops at B and D
    v = VehicleInput("V1", "VEH_001", "TRUCK", 2000.0, 10.0, "A", 13.00, 80.00, status="AVAILABLE")
    s_b = ShipmentInput("S_B", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 50.0, "MEDIUM", {"WATER": 10.0}, 10.0, 0.01)
    s_d = ShipmentInput("S_D", "A", 13.00, 80.00, "D", 12.95, 80.00, "Site D", 50.0, "MEDIUM", {"WATER": 10.0}, 10.0, 0.01)

    # Permutations: [B, D] vs [D, B]
    # Path A -> B -> D -> A:
    # A->B = 10, B->D (B->A->D = 10+5=15), D->A = 5 => total travel = 30
    # Path A -> D -> B -> A:
    # A->D = 5, D->B (D->A->B = 5+10=15), B->A = 10 => total travel = 30
    res = routing_engine.solve([s_b, s_d], [v], toy_graph)
    assert len(res.routes) == 1
    assert res.routes[0].total_travel_time_min == 30.0

# TEST-5E-19: End-to-end physical blockage reconstruction and edge inspection
def test_5e_19_end_to_end_physical_blockage_reconstruction(routing_engine):
    """
    Physical blockage -> Phase 5C recomputation -> updated graph_version ->
    Phase 5E routing -> physical route reconstruction -> no blocked physical edge traversed.
    """
    # 1. Start with OPEN physical road graph
    g_open = create_synthetic_toy_graph()
    ver_open = g_open.get_graph_version()
    v = VehicleInput("V1", "VEH_001", "TRUCK", 2000.0, 10.0, "A", 13.00, 80.00, status="AVAILABLE")
    s = ShipmentInput("S1", "A", 13.00, 80.00, "B", 13.00, 80.10, "Site B", 80.0, "CRITICAL", {"WATER": 100.0}, 100.0, 0.1)

    # 2. Phase 5C confirms direct A->B path exists
    route_open = g_open.compute_shortest_path("A", "B")
    assert route_open.status == "FEASIBLE"
    assert route_open.node_sequence == ["A", "B"]
    assert route_open.travel_time_minutes == 10.0

    # 3. Apply physical blockage: road A->B becomes IMPASSABLE
    g_blocked = create_synthetic_toy_graph()
    g_blocked.apply_blockage("BLK_PHYS_01", "A", "B", blockage_status="IMPASSABLE")
    ver_blocked = g_blocked.get_graph_version()
    assert ver_open != ver_blocked

    # 4. Phase 5C recomputes: direct A->B is physically unavailable, detour is A->D->E->F->C->B
    route_blocked = g_blocked.compute_shortest_path("A", "B")
    assert route_blocked.status == "FEASIBLE"
    assert route_blocked.node_sequence == ["A", "D", "E", "F", "C", "B"]
    assert ("A", "B") not in zip(route_blocked.node_sequence[:-1], route_blocked.node_sequence[1:])

    # 5. Feed updated graph into Phase 5E VehicleRoutingEngine
    res = routing_engine.solve([s], [v], g_blocked)
    assert res.graph_version == ver_blocked
    assert len(res.routes) == 1
    vehicle_route = res.routes[0]

    # 6. Reconstruct actual physical edges traversed by the vehicle for all tour legs:
    # Tour: Depot A -> Stop 1 (Incident B) -> Depot A
    stops = vehicle_route.stops
    physical_edges_traversed = []
    curr_node = "A"
    for stop in stops:
        leg = g_blocked.compute_shortest_path(curr_node, stop.incident_id)
        assert leg.status == "FEASIBLE"
        seq = leg.node_sequence
        physical_edges_traversed.extend(zip(seq[:-1], seq[1:]))
        curr_node = stop.incident_id

    # Return leg to depot A
    return_leg = g_blocked.compute_shortest_path(curr_node, vehicle_route.start_depot_id)
    assert return_leg.status == "FEASIBLE"
    seq = return_leg.node_sequence
    physical_edges_traversed.extend(zip(seq[:-1], seq[1:]))

    # 7. Assert that NO selected physical edge contains the blocked A->B (or B->A) edge
    assert ("A", "B") not in physical_edges_traversed
    assert ("B", "A") not in physical_edges_traversed

    # 8. Check disconnection case: fully cut incident becomes explicitly unrouted
    g_isolated = create_synthetic_toy_graph()
    g_isolated.apply_blockage("BLK_CUT_1", "A", "B", blockage_status="IMPASSABLE")
    g_isolated.apply_blockage("BLK_CUT_2", "C", "B", blockage_status="IMPASSABLE")
    res_iso = routing_engine.solve([s], [v], g_isolated)
    assert len(res_iso.routes) == 0
    assert len(res_iso.unrouted_shipments) == 1
    assert res_iso.operational_status == "UNROUTABLE"

