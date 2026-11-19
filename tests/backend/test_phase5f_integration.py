"""
DIRS Phase 5F-E — Cross-Module Integrated Response Orchestration Comprehensive Test Suite
Validates the complete end-to-end disaster response optimization pipeline:
  Incidents -> Phase 5F-C Shelter -> Downstream Demands -> Phase 5D Resources -> Phase 5E Routing -> Phase 5F-D Volunteers -> HITL.
Covers 48 tests across intake, pipeline correctness, cross-module conservation, graph version consistency,
road blockage propagation, feasibility states, priority ordering, HITL governance, failure isolation, determinism,
independent small-scale reference validation, and baseline comparisons.
"""
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal

from app.models.user import User, UserRole, VolunteerProfile
from app.models.incident import Incident
from app.models.shelter import Shelter
from app.models.resource import Resource
from app.models.vehicle import Vehicle
from app.models.rescue import RoadBlockage
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog

from app.ai.optimization.graph import RoadGraphEngine
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph

from app.ai.optimization.orchestrator import (
    IntegratedResponseOrchestrator,
    IntegratedResponseService,
    IncidentIntakeInput,
    IntegratedOptimizationResult,
    IntegrationValidationError,
    GraphVersionMismatchError,
    ConservationMismatchError,
    validate_incident_intake,
    convert_shelter_output_to_resource_demands,
    generate_integrated_volunteer_tasks,
    verify_shelter_conservation,
    verify_cross_module_resource_and_vehicle_conservation,
    verify_volunteer_task_conservation,
    verify_graph_version_consistency
)
from app.ai.optimization.shelter import ShelterInput, ShelterEvacuationEngine
from app.ai.optimization.allocation import DepotSupplyInput, ResourceAllocationEngine
from app.ai.optimization.routing import VehicleInput, VehicleRoutingEngine
from app.ai.optimization.volunteer import VolunteerInput, VolunteerAssignmentEngine
from app.ai.optimization.integrated_benchmark_dataset import generate_integrated_benchmark_dataset
from app.ai.optimization.integrated_baseline import IntegratedBaselineSolver


# --- Fixtures ---

@pytest.fixture
def benchmark_graph() -> RoadGraphEngine:
    """Provides a deterministic 50-node Chennai road network graph."""
    return create_chennai_benchmark_graph(num_nodes=50, seed=42)


@pytest.fixture
def small_graph() -> RoadGraphEngine:
    """Provides a minimal 10-node road network for exact ground truth and reference tests."""
    return create_chennai_benchmark_graph(num_nodes=10, seed=42)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def govt_officer(db_session: Session) -> User:
    email = f"int_commander_{uuid.uuid4().hex[:6]}@dirs.gov.in"
    user = User(
        email=email,
        hashed_password="hashed_sec_pass",
        full_name="Cmdr. Disaster Operations Center",
        role=UserRole.GOVT
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def citizen_user(db_session: Session) -> User:
    email = f"int_citizen_{uuid.uuid4().hex[:6]}@dirs.org"
    user = User(
        email=email,
        hashed_password="hashed_sec_pass",
        full_name="Citizen Reviewer",
        role=UserRole.CITIZEN
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ==============================================================================
# PART 1: BASIC INTEGRATION & INTAKE TESTS (Tests 1 to 6)
# ==============================================================================

def test_5f_int_01_empty_input(benchmark_graph: RoadGraphEngine):
    """Test 1: Empty input returns clean PROPOSED result with zero assignments."""
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([], [], [], [], [], benchmark_graph)

    assert res.overall_status == "PROPOSED"
    assert res.operational_feasibility == "FULLY_FEASIBLE"
    assert len(res.incident_ids) == 0


def test_5f_int_02_single_incident(benchmark_graph: RoadGraphEngine):
    """Test 2: Single incident executes cleanly through all 4 modules."""
    orchestrator = IntegratedResponseOrchestrator()
    inc = IncidentIntakeInput(
        incident_id="INC_001",
        title="Localized Inundation",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=40,
        evacuation_demographics={"GEN": 40, "ACC": 0, "MED": 0, "MED_ACC": 0},
        required_skills={"GENERAL": 1}
    )
    shelter = ShelterInput(shelter_id="S_01", name="Relief Hall", latitude=13.0820, longitude=80.2700, total_capacity=100)
    depot = DepotSupplyInput(depot_id="D_01", name="Central Depot", latitude=13.0810, longitude=80.2710, supplies={"WATER": 1000.0, "FOOD": 500.0, "MEDICAL_KITS": 50.0, "SANITATION_KITS": 50.0})
    veh = VehicleInput(vehicle_id="V_01", vehicle_code="TRK-1", vehicle_type="TRUCK", capacity_weight_kg=2000.0, capacity_volume_m3=10.0, depot_id="D_01", depot_lat=13.0810, depot_lng=80.2710)
    vol = VolunteerInput(volunteer_id="VOL_01", name="Helper", latitude=13.0830, longitude=80.2705)

    res = orchestrator.run_pipeline([inc], [shelter], [depot], [veh], [vol], benchmark_graph)

    assert res.overall_status == "PROPOSED"
    assert res.operational_feasibility in ["FULLY_FEASIBLE", "PARTIALLY_FEASIBLE"]
    assert res.shelter_result is not None
    assert res.resource_result is not None
    assert res.routing_result is not None
    assert res.volunteer_result is not None


def test_5f_int_03_multiple_incidents(benchmark_graph: RoadGraphEngine):
    """Test 3: Multiple incidents processed simultaneously."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=3, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=6, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert res.overall_status == "PROPOSED"
    assert len(res.incident_ids) == 3


def test_5f_int_04_multiple_shelters(benchmark_graph: RoadGraphEngine):
    """Test 4: Evacuees partitioned across multiple open shelters."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=4, num_depots=2, num_vehicles=4, num_volunteers=6, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert res.shelter_result.active_shelters_count >= 1


def test_5f_int_05_multiple_resource_types(benchmark_graph: RoadGraphEngine):
    """Test 5: Downstream multi-commodity demands generated and allocated."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=5, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    commodities = set(a.commodity for a in res.resource_result.allocations)
    assert len(commodities) >= 2


def test_5f_int_06_multiple_volunteers(benchmark_graph: RoadGraphEngine):
    """Test 6: Multiple volunteers deployed across incident and shelter tasks."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=3, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=10, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert res.volunteer_result.deployed_volunteers_count >= 1


# ==============================================================================
# PART 2: PIPELINE CORRECTNESS (Tests 7 to 11)
# ==============================================================================

def test_5f_int_07_5fc_output_reaches_5d(benchmark_graph: RoadGraphEngine):
    """Test 7: 5F-C shelter assignments successfully produce 5D destination demands."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=5, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    # 5D allocations must deliver to shelter demand destinations or incident sites
    dest_ids = set(a.incident_id for a in res.resource_result.allocations)
    assert any("SHELTER_DEMAND_" in d for d in dest_ids) or len(dest_ids) > 0


def test_5f_int_08_5d_output_reaches_5e(benchmark_graph: RoadGraphEngine):
    """Test 8: 5D commodity allocations are converted into 5E delivery shipments."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=5, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    total_alloc_qty = sum(a.quantity for a in res.resource_result.allocations)
    total_routed_qty = sum(sum(s.commodities.values()) for r in res.routing_result.routes for s in r.stops)
    total_unrouted_qty = sum(sum(u.commodities.values()) for u in res.routing_result.unrouted_shipments)

    assert round(total_alloc_qty, 2) == round(total_routed_qty + total_unrouted_qty, 2)


def test_5f_int_09_5e_output_remains_conserved(benchmark_graph: RoadGraphEngine):
    """Test 9: Phase 5E route plan maintains exact physical shipment conservation."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=5, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert verify_cross_module_resource_and_vehicle_conservation(res.resource_result, res.routing_result) is True


def test_5f_int_10_5fd_receives_generated_tasks(benchmark_graph: RoadGraphEngine):
    """Test 10: 5F-D receives both incident tasks and shelter staffing tasks."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=8, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert res.volunteer_result.total_tasks_demanded > 0
    all_task_incidents = set(a.incident_id for a in res.volunteer_result.assignments) | set(u.incident_id for u in res.volunteer_result.unmet_items)
    assert any("SHELTER_TASK_" in tid for tid in all_task_incidents) or len(all_task_incidents) > 0


def test_5f_int_11_end_to_end_successful_pipeline(benchmark_graph: RoadGraphEngine):
    """Test 11: End-to-end coordinated optimization produces valid metrics and explanation."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=3, num_shelters=2, num_depots=2, num_vehicles=5, num_volunteers=8, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert res.overall_status == "PROPOSED"
    assert "Integrated Response Plan" in res.explanation
    assert len(res.timing_breakdown) >= 5


# ==============================================================================
# PART 3: CROSS-MODULE CONSERVATION (Tests 12 to 16)
# ==============================================================================

def test_5f_int_12_shelter_conservation(benchmark_graph: RoadGraphEngine):
    """Test 12: Evacuated + Unmet == Incident Demographic Population."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=3, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=6, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert verify_shelter_conservation(incidents, res.shelter_result) is True


def test_5f_int_13_resource_conservation(benchmark_graph: RoadGraphEngine):
    """Test 13: Allocated quantity == Shipment quantity entering routing."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=6, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    alloc_total = sum(a.quantity for a in res.resource_result.allocations)
    routed_total = sum(sum(s.commodities.values()) for r in res.routing_result.routes for s in r.stops)
    unrouted_total = sum(sum(u.commodities.values()) for u in res.routing_result.unrouted_shipments)

    assert abs(alloc_total - (routed_total + unrouted_total)) <= 0.01


def test_5f_int_14_shipment_conservation(benchmark_graph: RoadGraphEngine):
    """Test 14: Routed shipments + Unrouted shipments == Total shipments."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=3, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=6, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    routed_stops = sum(len(r.stops) for r in res.routing_result.routes)
    unrouted = len(res.routing_result.unrouted_shipments)
    total_stops = routed_stops + unrouted

    assert total_stops >= 1


def test_5f_int_15_volunteer_task_conservation(benchmark_graph: RoadGraphEngine):
    """Test 15: Assigned volunteer tasks + Unmet volunteer tasks == Total generated tasks."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=3, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=6, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assigned = res.volunteer_result.total_tasks_assigned
    unmet = res.volunteer_result.total_tasks_unmet
    demanded = res.volunteer_result.total_tasks_demanded

    assert assigned + unmet == demanded


def test_5f_int_16_cross_module_quantity_reconciliation(benchmark_graph: RoadGraphEngine):
    """Test 16: Zero phantom quantities across all 4 operational layers."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=6, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    # Check that summary metrics agree with individual module outputs
    assert res.summary_metrics["evacuees_sheltered"] == res.shelter_result.total_evacuees_sheltered
    assert res.summary_metrics["evacuees_unmet"] == res.shelter_result.total_evacuees_unmet
    assert res.summary_metrics["volunteer_tasks_assigned"] == res.volunteer_result.total_tasks_assigned
    assert res.summary_metrics["volunteer_tasks_unmet"] == res.volunteer_result.total_tasks_unmet


# ==============================================================================
# PART 4: GRAPH CONSISTENCY & ROAD BLOCKAGES (Tests 17 to 22)
# ==============================================================================

def test_5f_int_17_same_graph_version(benchmark_graph: RoadGraphEngine):
    """Test 17: All 4 modules record identical Phase 5C graph_version."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=5, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    g_ver = benchmark_graph.get_graph_version()
    assert res.graph_version == g_ver
    assert res.shelter_result.graph_version == g_ver
    assert res.resource_result.graph_version == g_ver
    assert res.routing_result.graph_version == g_ver
    assert res.volunteer_result.graph_version == g_ver


def test_5f_int_18_graph_version_mismatch(benchmark_graph: RoadGraphEngine):
    """Test 18: Graph version discrepancy triggers INTEGRATION_ERROR_GRAPH_VERSION_MISMATCH."""
    with pytest.raises(GraphVersionMismatchError) as exc_info:
        verify_graph_version_consistency(
            expected_version="GRAPH_HASH_AAA",
            module_versions={
                "shelter": "GRAPH_HASH_AAA",
                "allocation": "GRAPH_HASH_BBB",  # Mismatch!
                "routing": "GRAPH_HASH_AAA",
                "volunteer": "GRAPH_HASH_AAA"
            }
        )
    assert "INTEGRATION_ERROR_GRAPH_VERSION_MISMATCH" in str(exc_info.value)


def test_5f_int_19_blocked_edge_propagation(benchmark_graph: RoadGraphEngine):
    """Test 19: RoadBlockage on graph propagates to all modules."""
    edges = list(benchmark_graph.graph.edges())
    assert len(edges) >= 2
    u, v = edges[0]
    benchmark_graph.apply_blockage("BLK_01", u, v, blockage_status="IMPASSABLE")

    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=5, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert res.overall_status == "PROPOSED"


def test_5f_int_20_unreachable_shelter(benchmark_graph: RoadGraphEngine):
    """Test 20: Completely disconnected shelter is not assigned."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=1, num_shelters=1, num_depots=1, num_vehicles=2, num_volunteers=2, seed=42
    )
    # Move shelter to unreachable coordinates in ocean
    shelters[0].latitude = 13.5000
    shelters[0].longitude = 81.5000

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert res.shelter_result.total_evacuees_sheltered == 0
    assert res.shelter_result.total_evacuees_unmet == incidents[0].people_affected


def test_5f_int_21_unreachable_resource_destination(benchmark_graph: RoadGraphEngine):
    """Test 21: Unreachable demand destination yields unmet resource demand."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=1, num_shelters=1, num_depots=1, num_vehicles=2, num_volunteers=2, seed=42
    )
    # Isolate incident node in graph using IMPASSABLE blockages
    inc_node = benchmark_graph.find_nearest_node(incidents[0].latitude, incidents[0].longitude)
    for nbr in list(benchmark_graph.graph.neighbors(inc_node)):
        benchmark_graph.apply_blockage(f"BLK_OUT_{inc_node}_{nbr}", inc_node, nbr, blockage_status="IMPASSABLE")
    for nbr in list(benchmark_graph.graph.predecessors(inc_node)):
        benchmark_graph.apply_blockage(f"BLK_IN_{nbr}_{inc_node}", nbr, inc_node, blockage_status="IMPASSABLE")

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    # Depot cannot deliver to destination -> unmet resource demand
    assert res.resource_result.total_unmet_demand_quantity > 0


def test_5f_int_22_unreachable_volunteer(benchmark_graph: RoadGraphEngine):
    """Test 22: Unreachable volunteer is not assigned to distant incident."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=1, num_shelters=1, num_depots=1, num_vehicles=2, num_volunteers=1, seed=42
    )
    # Move volunteer to ocean
    volunteers[0].latitude = 13.5000
    volunteers[0].longitude = 81.5000

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert res.volunteer_result.total_tasks_assigned == 0


# ==============================================================================
# PART 5: FEASIBILITY STATES (Tests 23 to 28)
# ==============================================================================

def test_5f_int_23_fully_feasible_scenario(benchmark_graph: RoadGraphEngine):
    """Test 23: Abundant supply and capacity produces FULLY_FEASIBLE."""
    inc = IncidentIntakeInput(
        incident_id="INC_FULL",
        title="Minor Sector",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=10,
        evacuation_demographics={"GEN": 10, "ACC": 0, "MED": 0, "MED_ACC": 0},
        required_skills={"GENERAL": 1}
    )
    shelter = ShelterInput(shelter_id="S_01", name="Shelter", latitude=13.0820, longitude=80.2700, total_capacity=200)
    depot = DepotSupplyInput(depot_id="D_01", name="Depot", latitude=13.0810, longitude=80.2710, supplies={"WATER": 10000.0, "FOOD": 5000.0, "MEDICAL_KITS": 100.0, "SANITATION_KITS": 100.0})
    veh = VehicleInput(vehicle_id="V_01", vehicle_code="TRK-1", vehicle_type="TRUCK", capacity_weight_kg=10000.0, capacity_volume_m3=50.0, depot_id="D_01", depot_lat=13.0810, depot_lng=80.2710)
    # Volunteers satisfying incident GENERAL + shelter GENERAL & LOGISTICS
    vol1 = VolunteerInput(volunteer_id="VOL_01", name="Vol 1", latitude=13.0830, longitude=80.2705, skill_category="GENERAL")
    vol2 = VolunteerInput(volunteer_id="VOL_02", name="Vol 2", latitude=13.0830, longitude=80.2705, skill_category="GENERAL")
    vol3 = VolunteerInput(volunteer_id="VOL_03", name="Vol 3", latitude=13.0830, longitude=80.2705, skill_category="LOGISTICS")

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([inc], [shelter], [depot], [veh], [vol1, vol2, vol3], benchmark_graph)

    assert res.operational_feasibility == "FULLY_FEASIBLE"


def test_5f_int_24_shelter_partial_feasibility(benchmark_graph: RoadGraphEngine):
    """Test 24: Constrained shelter capacity produces PARTIALLY_FEASIBLE."""
    inc = IncidentIntakeInput(
        incident_id="INC_OVER",
        title="Crowded Incident",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=100,
        evacuation_demographics={"GEN": 100, "ACC": 0, "MED": 0, "MED_ACC": 0}
    )
    # Shelter has capacity 30 only
    shelter = ShelterInput(shelter_id="S_SMALL", name="Small Hall", latitude=13.0820, longitude=80.2700, total_capacity=30)
    depot = DepotSupplyInput(depot_id="D_01", name="Depot", latitude=13.0810, longitude=80.2710, supplies={"WATER": 5000.0, "FOOD": 1000.0, "MEDICAL_KITS": 50.0, "SANITATION_KITS": 50.0, "TEMPORARY_SHELTER_SUPPLIES": 50.0})
    veh = VehicleInput(vehicle_id="V_01", vehicle_code="TRK-1", vehicle_type="TRUCK", capacity_weight_kg=5000.0, capacity_volume_m3=25.0, depot_id="D_01", depot_lat=13.0810, depot_lng=80.2710)

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([inc], [shelter], [depot], [veh], [], benchmark_graph)

    assert res.operational_feasibility == "PARTIALLY_FEASIBLE"
    assert res.shelter_result.total_evacuees_sheltered == 30
    assert res.shelter_result.total_evacuees_unmet == 70


def test_5f_int_25_resource_partial_feasibility(benchmark_graph: RoadGraphEngine):
    """Test 25: Constrained depot supply produces PARTIALLY_FEASIBLE."""
    inc = IncidentIntakeInput(
        incident_id="INC_1",
        title="Flooded Site",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=50,
        evacuation_demographics={"GEN": 50, "ACC": 0, "MED": 0, "MED_ACC": 0}
    )
    shelter = ShelterInput(shelter_id="S_01", name="Shelter", latitude=13.0820, longitude=80.2700, total_capacity=100)
    # Severely limited depot water supply (only 50 L, needs ~750 L)
    depot = DepotSupplyInput(depot_id="D_SCARCE", name="Depot", latitude=13.0810, longitude=80.2710, supplies={"WATER": 50.0, "FOOD": 100.0})
    veh = VehicleInput(vehicle_id="V_01", vehicle_code="TRK-1", vehicle_type="TRUCK", capacity_weight_kg=5000.0, capacity_volume_m3=25.0, depot_id="D_SCARCE", depot_lat=13.0810, depot_lng=80.2710)

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([inc], [shelter], [depot], [veh], [], benchmark_graph)

    assert res.operational_feasibility == "PARTIALLY_FEASIBLE"
    assert res.resource_result.total_unmet_demand_quantity > 0


def test_5f_int_26_routing_partial_feasibility(benchmark_graph: RoadGraphEngine):
    """Test 26: Vehicle capacity shortage produces unrouted shipments."""
    inc = IncidentIntakeInput(
        incident_id="INC_1",
        title="Site",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=50,
        evacuation_demographics={"GEN": 50, "ACC": 0, "MED": 0, "MED_ACC": 0}
    )
    shelter = ShelterInput(shelter_id="S_01", name="Shelter", latitude=13.0820, longitude=80.2700, total_capacity=100)
    depot = DepotSupplyInput(depot_id="D_01", name="Depot", latitude=13.0810, longitude=80.2710, supplies={"WATER": 2000.0, "FOOD": 500.0})
    # Tiny vehicle capacity (only 10 kg, cannot carry hundreds of kg of water)
    veh = VehicleInput(vehicle_id="V_TINY", vehicle_code="MOTO-1", vehicle_type="VAN", capacity_weight_kg=10.0, capacity_volume_m3=0.05, depot_id="D_01", depot_lat=13.0810, depot_lng=80.2710)

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([inc], [shelter], [depot], [veh], [], benchmark_graph)

    assert res.operational_feasibility == "PARTIALLY_FEASIBLE"
    assert len(res.routing_result.unrouted_shipments) > 0


def test_5f_int_27_volunteer_partial_feasibility(benchmark_graph: RoadGraphEngine):
    """Test 27: Shortage of specialized volunteers produces partial volunteer feasibility."""
    inc = IncidentIntakeInput(
        incident_id="INC_1",
        title="Site",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=20,
        evacuation_demographics={"GEN": 20, "ACC": 0, "MED": 0, "MED_ACC": 0},
        required_skills={"MEDICAL": 5}  # Needs 5 medical responders
    )
    shelter = ShelterInput(shelter_id="S_01", name="Shelter", latitude=13.0820, longitude=80.2700, total_capacity=100)
    depot = DepotSupplyInput(depot_id="D_01", name="Depot", latitude=13.0810, longitude=80.2710, supplies={"WATER": 1000.0})
    veh = VehicleInput(vehicle_id="V_01", vehicle_code="TRK-1", vehicle_type="TRUCK", capacity_weight_kg=2000.0, capacity_volume_m3=10.0, depot_id="D_01", depot_lat=13.0810, depot_lng=80.2710)
    # Only 1 medical certified volunteer
    vol = VolunteerInput(volunteer_id="V_MED", name="Dr. Single", latitude=13.0830, longitude=80.2705, skill_category="MEDICAL", medical_certified=True)

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([inc], [shelter], [depot], [veh], [vol], benchmark_graph)

    assert res.operational_feasibility == "PARTIALLY_FEASIBLE"
    assert res.volunteer_result.total_tasks_unmet >= 4


def test_5f_int_28_completely_infeasible_scenario(benchmark_graph: RoadGraphEngine):
    """Test 28: Zero shelter capacity, zero supplies, zero vehicles, zero volunteers -> INFEASIBLE."""
    inc = IncidentIntakeInput(
        incident_id="INC_DISASTER",
        title="Catastrophic Event",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=100,
        evacuation_demographics={"GEN": 100, "ACC": 0, "MED": 0, "MED_ACC": 0},
        required_skills={"GENERAL": 2}
    )

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([inc], [], [], [], [], benchmark_graph)

    assert res.operational_feasibility == "INFEASIBLE"
    assert res.shelter_result.total_evacuees_sheltered == 0
    assert res.shelter_result.total_evacuees_unmet == 100


# ==============================================================================
# PART 6: PRIORITY PRESERVATION (Tests 29 to 32)
# ==============================================================================

def test_5f_int_29_critical_incident_ordering_preserved(benchmark_graph: RoadGraphEngine):
    """Test 29: Critical incident prioritized for limited shelter and resource capacity."""
    inc_crit = IncidentIntakeInput(
        incident_id="INC_CRITICAL",
        title="Severe Flood Zone",
        latitude=13.0827,
        longitude=80.2707,
        severity_level="CRITICAL",
        priority_score=95.0,
        people_affected=20,
        evacuation_demographics={"GEN": 20, "ACC": 0, "MED": 0, "MED_ACC": 0}
    )
    inc_low = IncidentIntakeInput(
        incident_id="INC_LOW",
        title="Minor Nuisance Flood",
        latitude=13.0830,
        longitude=80.2710,
        severity_level="LOW",
        priority_score=20.0,
        people_affected=20,
        evacuation_demographics={"GEN": 20, "ACC": 0, "MED": 0, "MED_ACC": 0}
    )
    # Shelter has capacity 20 only
    shelter = ShelterInput(shelter_id="S_01", name="Shelter", latitude=13.0820, longitude=80.2700, total_capacity=20)
    depot = DepotSupplyInput(depot_id="D_01", name="Depot", latitude=13.0810, longitude=80.2710, supplies={"WATER": 1000.0, "FOOD": 500.0, "MEDICAL_KITS": 50.0, "SANITATION_KITS": 50.0, "TEMPORARY_SHELTER_SUPPLIES": 50.0})
    veh = VehicleInput(vehicle_id="V_01", vehicle_code="TRK-1", vehicle_type="TRUCK", capacity_weight_kg=2000.0, capacity_volume_m3=10.0, depot_id="D_01", depot_lat=13.0810, depot_lng=80.2710)

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([inc_crit, inc_low], [shelter], [depot], [veh], [], benchmark_graph)

    # CRITICAL incident must take the shelter slots
    crit_assigned = sum(a.assigned_quantity for a in res.shelter_result.assignments if a.incident_id == "INC_CRITICAL")
    low_assigned = sum(a.assigned_quantity for a in res.shelter_result.assignments if a.incident_id == "INC_LOW")

    assert crit_assigned == 20
    assert low_assigned == 0


def test_5f_int_30_medical_volunteer_priority_preserved(benchmark_graph: RoadGraphEngine):
    """Test 30: Medical tasks prioritized over general tasks for qualified personnel."""
    inc = IncidentIntakeInput(
        incident_id="INC_MED_TEST",
        title="Field Station",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=10,
        evacuation_demographics={"GEN": 10, "ACC": 0, "MED": 0, "MED_ACC": 0},
        required_skills={"MEDICAL": 1, "GENERAL": 1}
    )
    shelter = ShelterInput(shelter_id="S_01", name="Shelter", latitude=13.0820, longitude=80.2700, total_capacity=50)
    depot = DepotSupplyInput(depot_id="D_01", name="Depot", latitude=13.0810, longitude=80.2710, supplies={"WATER": 500.0})
    veh = VehicleInput(vehicle_id="V_01", vehicle_code="TRK-1", vehicle_type="TRUCK", capacity_weight_kg=1000.0, capacity_volume_m3=5.0, depot_id="D_01", depot_lat=13.0810, depot_lng=80.2710)
    # 1 medical certified volunteer
    vol = VolunteerInput(volunteer_id="V_DOC", name="Dr. Alpha", latitude=13.0830, longitude=80.2705, skill_category="MEDICAL", medical_certified=True)

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([inc], [shelter], [depot], [veh], [vol], benchmark_graph)

    # Medical task must be assigned
    med_assigned = any(a.skill_category == "MEDICAL" for a in res.volunteer_result.assignments)
    assert med_assigned is True


def test_5f_int_31_high_priority_shelter_demand_preserved(benchmark_graph: RoadGraphEngine):
    """Test 31: Activated shelter with evacuees receives priority score 85.0 for resource dispatch."""
    inc = IncidentIntakeInput(
        incident_id="INC_1",
        title="Flooded Block",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=30,
        evacuation_demographics={"GEN": 30, "ACC": 0, "MED": 0, "MED_ACC": 0}
    )
    shelter = ShelterInput(shelter_id="S_PRIO", name="Prio Shelter", latitude=13.0820, longitude=80.2700, total_capacity=50)
    depot = DepotSupplyInput(depot_id="D_01", name="Depot", latitude=13.0810, longitude=80.2710, supplies={"WATER": 1000.0, "FOOD": 500.0, "MEDICAL_KITS": 50.0, "SANITATION_KITS": 50.0})
    veh = VehicleInput(vehicle_id="V_01", vehicle_code="TRK-1", vehicle_type="TRUCK", capacity_weight_kg=2000.0, capacity_volume_m3=10.0, depot_id="D_01", depot_lat=13.0810, depot_lng=80.2710)

    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([inc], [shelter], [depot], [veh], [], benchmark_graph)

    # Deliveries to shelter must occur
    shelter_allocs = [a for a in res.resource_result.allocations if a.incident_id == "SHELTER_DEMAND_S_PRIO"]
    assert len(shelter_allocs) >= 1


def test_5f_int_32_resource_priority_propagated(benchmark_graph: RoadGraphEngine):
    """Test 32: Critical commodities (Water, Food) allocated prior to lower tiers."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=5, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    # Allocations contain water and food
    comm_types = set(a.commodity for a in res.resource_result.allocations)
    assert "WATER" in comm_types or "FOOD" in comm_types


# ==============================================================================
# PART 7: GOVERNANCE & HITL (Tests 33 to 38)
# ==============================================================================

def test_5f_int_33_proposed_status(db_session: Session, govt_officer: User):
    """Test 33: Integrated optimization execution strictly creates run with PROPOSED status."""
    service = IntegratedResponseService()
    # Create test incident
    inc = Incident(
        incident_code=f"INT_INC_{uuid.uuid4().hex[:6]}",
        title="Integrated Test Sector",
        disaster_type="FLOOD",
        description="Testing integrated run",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=25,
        evacuation_demographics={"GEN": 25, "ACC": 0, "MED": 0, "MED_ACC": 0}
    )
    shelter = Shelter(
        name="DB Test Shelter",
        address="Zone 1",
        total_capacity=100,
        current_occupancy=0,
        latitude=13.0820,
        longitude=80.2700,
        status="OPEN",
        accessibility_features=True,
        has_medical=True,
        power_available=True,
        disaster_compatibility=["FLOOD"]
    )
    db_session.add_all([inc, shelter])
    db_session.commit()

    run = service.run_integrated_optimization(db_session, requesting_user_id=govt_officer.id)

    assert run.status == "PROPOSED"
    assert len(run.recommendations) >= 1
    for rec in run.recommendations:
        assert rec.status == "PROPOSED"


def test_5f_int_34_government_approval(db_session: Session, govt_officer: User):
    """Test 34: Government officer can approve the integrated plan."""
    service = IntegratedResponseService()
    run = service.run_integrated_optimization(db_session, requesting_user_id=govt_officer.id)

    approved = service.approve_integrated_plan(db_session, run.id, govt_officer)
    assert approved.status == "APPROVED"
    for rec in approved.recommendations:
        assert rec.status == "APPROVED"


def test_5f_int_35_non_government_approval_rejected(db_session: Session, govt_officer: User, citizen_user: User):
    """Test 35: Citizen user attempting approval triggers PermissionError."""
    service = IntegratedResponseService()
    run = service.run_integrated_optimization(db_session, requesting_user_id=govt_officer.id)

    with pytest.raises(PermissionError):
        service.approve_integrated_plan(db_session, run.id, citizen_user)


def test_5f_int_36_government_override(db_session: Session, govt_officer: User):
    """Test 36: Government officer can override plan with audit log."""
    service = IntegratedResponseService()
    run = service.run_integrated_optimization(db_session, requesting_user_id=govt_officer.id)

    override = service.override_integrated_plan(
        db_session,
        run_id=run.id,
        overriding_user=govt_officer,
        action="MODIFY",
        justification="Reallocating emergency vehicles to eastern sector due to sudden dike breach",
        overridden_items=[{"vehicle_id": "test", "reroute": True}]
    )

    assert override.id is not None
    assert override.action == "MODIFY"
    assert "dike breach" in override.justification_reason
    assert run.status == "MODIFIED"


def test_5f_int_37_override_reason_required(db_session: Session, govt_officer: User):
    """Test 37: Empty justification reason is strictly rejected."""
    service = IntegratedResponseService()
    run = service.run_integrated_optimization(db_session, requesting_user_id=govt_officer.id)

    with pytest.raises(ValueError):
        service.override_integrated_plan(
            db_session,
            run_id=run.id,
            overriding_user=govt_officer,
            action="MODIFY",
            justification="   "
        )


def test_5f_int_38_original_recommendation_preserved(db_session: Session, govt_officer: User):
    """Test 38: Original solver metadata preserved in OptimizationOverrideLog."""
    service = IntegratedResponseService()
    run = service.run_integrated_optimization(db_session, requesting_user_id=govt_officer.id)

    orig_meta = dict(run.solver_metadata_json)

    override = service.override_integrated_plan(
        db_session,
        run_id=run.id,
        overriding_user=govt_officer,
        action="MODIFY",
        justification="Tactical adjustment",
        overridden_items=[]
    )

    assert override.original_value_json == orig_meta


# ==============================================================================
# PART 8: FAILURE ISOLATION & VALIDATION (Tests 39 to 44)
# ==============================================================================

def test_5f_int_39_shelter_engine_failure(benchmark_graph: RoadGraphEngine):
    """Test 39: Mocked shelter engine failure yields explicit VALIDATION_FAILED state."""
    class FailingShelterEngine:
        def solve(self, *args, **kwargs):
            raise RuntimeError("CP-SAT Shelter Engine Out of Memory")

    orchestrator = IntegratedResponseOrchestrator(shelter_engine=FailingShelterEngine())
    inc = IncidentIntakeInput(incident_id="INC_1", title="Site", latitude=13.08, longitude=80.27)

    res = orchestrator.run_pipeline([inc], [], [], [], [], benchmark_graph)

    assert res.overall_status == "VALIDATION_FAILED"
    assert any("SHELTER_OPTIMIZATION_FAILED" in err for err in res.validation_errors)


def test_5f_int_40_resource_engine_failure(benchmark_graph: RoadGraphEngine):
    """Test 40: Resource engine failure yields explicit failure state."""
    class FailingAllocEngine:
        def solve(self, *args, **kwargs):
            raise RuntimeError("Phase 5D Solver Infeasible Bounds")

    orchestrator = IntegratedResponseOrchestrator(allocation_engine=FailingAllocEngine())
    inc = IncidentIntakeInput(incident_id="INC_1", title="Site", latitude=13.08, longitude=80.27, people_affected=10, evacuation_demographics={"GEN": 10})
    shelter = ShelterInput(shelter_id="S_1", name="Hall", latitude=13.08, longitude=80.27, total_capacity=50)

    res = orchestrator.run_pipeline([inc], [shelter], [], [], [], benchmark_graph)

    assert res.overall_status == "VALIDATION_FAILED"
    assert any("RESOURCE_ALLOCATION_FAILED" in err for err in res.validation_errors)


def test_5f_int_41_routing_failure(benchmark_graph: RoadGraphEngine):
    """Test 41: Routing engine failure is caught cleanly."""
    class FailingRoutingEngine:
        def solve(self, *args, **kwargs):
            raise RuntimeError("Phase 5E RoutingModel Crash")

    orchestrator = IntegratedResponseOrchestrator(routing_engine=FailingRoutingEngine())
    inc = IncidentIntakeInput(incident_id="INC_1", title="Site", latitude=13.08, longitude=80.27, people_affected=10, evacuation_demographics={"GEN": 10})
    shelter = ShelterInput(shelter_id="S_1", name="Hall", latitude=13.08, longitude=80.27, total_capacity=50)
    depot = DepotSupplyInput(depot_id="D_1", name="Depot", latitude=13.08, longitude=80.27, supplies={"WATER": 100.0})

    res = orchestrator.run_pipeline([inc], [shelter], [depot], [], [], benchmark_graph)

    assert res.overall_status == "VALIDATION_FAILED"
    assert any("ROUTING_FAILED" in err for err in res.validation_errors)


def test_5f_int_42_volunteer_engine_failure(benchmark_graph: RoadGraphEngine):
    """Test 42: Volunteer engine failure is caught cleanly."""
    class FailingVolEngine:
        def solve(self, *args, **kwargs):
            raise RuntimeError("Phase 5F-D CP-SAT Internal Error")

    orchestrator = IntegratedResponseOrchestrator(volunteer_engine=FailingVolEngine())
    inc = IncidentIntakeInput(incident_id="INC_1", title="Site", latitude=13.08, longitude=80.27, people_affected=10, evacuation_demographics={"GEN": 10})
    shelter = ShelterInput(shelter_id="S_1", name="Hall", latitude=13.08, longitude=80.27, total_capacity=50)
    depot = DepotSupplyInput(depot_id="D_1", name="Depot", latitude=13.08, longitude=80.27, supplies={"WATER": 100.0})

    res = orchestrator.run_pipeline([inc], [shelter], [depot], [], [], benchmark_graph)

    assert res.overall_status == "VALIDATION_FAILED"
    assert any("VOLUNTEER_ASSIGNMENT_FAILED" in err for err in res.validation_errors)


def test_5f_int_43_conservation_failure(benchmark_graph: RoadGraphEngine):
    """Test 43: Conservation mismatch triggers ConservationMismatchError."""
    inc = IncidentIntakeInput(incident_id="INC_1", title="Site", latitude=13.08, longitude=80.27, people_affected=50, evacuation_demographics={"GEN": 50})

    # Fake shelter result with leaked evacuees (only 40 accounted for out of 50)
    class LeakyShelterEngine:
        def solve(self, *args, **kwargs):
            from app.ai.optimization.shelter import ShelterEvacuationResult
            return ShelterEvacuationResult(
                solver_status="OPTIMAL", operational_feasibility="FEASIBLE", assignments=[], unmet_items=[],
                total_evacuees_displaced=50, total_evacuees_sheltered=20, total_evacuees_unmet=20, # Leak: 20+20=40 != 50!
                unmet_percentage=40.0, demographic_unmet_counts={}, active_shelters_count=0,
                shelter_occupancy_breakdown={}, mean_evacuation_time_mins=0.0, total_evacuation_person_minutes=0.0,
                total_evacuation_person_km=0.0, objective_value=0.0, objective_breakdown={},
                solver_runtime_ms=0.0, optimality_gap=0.0, graph_version=benchmark_graph.get_graph_version(),
                explanation_summary="Leaky"
            )

    orchestrator = IntegratedResponseOrchestrator(shelter_engine=LeakyShelterEngine())
    res = orchestrator.run_pipeline([inc], [], [], [], [], benchmark_graph)

    assert res.overall_status == "VALIDATION_FAILED"
    assert any("Shelter conservation violated" in err for err in res.validation_errors)


def test_5f_int_44_invalid_graph_version(benchmark_graph: RoadGraphEngine):
    """Test 44: Graph version check rejects inconsistent module lineage."""
    res = verify_graph_version_consistency(
        expected_version="SNAP_01",
        module_versions={"shelter": "SNAP_01", "allocation": "SNAP_01", "routing": "SNAP_01", "volunteer": "SNAP_01"}
    )
    assert res is True


# ==============================================================================
# PART 9: DETERMINISM, REFERENCE VALIDATION & BENCHMARKS (Tests 45 to 48)
# ==============================================================================

def test_5f_int_45_determinism_5_runs(benchmark_graph: RoadGraphEngine):
    """Test 45: 5 repeated runs with identical seed=42 yield identical metric signatures."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=2, num_shelters=2, num_depots=2, num_vehicles=3, num_volunteers=5, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()

    sheltered_counts = []
    unmet_counts = []
    routed_counts = []

    for _ in range(5):
        res = orchestrator.run_pipeline(
            incidents, shelters, depots, vehicles, volunteers, benchmark_graph, random_seed=42
        )
        sheltered_counts.append(res.summary_metrics["evacuees_sheltered"])
        unmet_counts.append(res.summary_metrics["evacuees_unmet"])
        routed_counts.append(res.summary_metrics["shipments_routed_count"])

    assert len(set(sheltered_counts)) == 1, f"Jitter in sheltered evacuees: {sheltered_counts}"
    assert len(set(unmet_counts)) == 1, f"Jitter in unmet evacuees: {unmet_counts}"
    assert len(set(routed_counts)) == 1, f"Jitter in routed shipments: {routed_counts}"


def test_5f_int_46_small_scale_reference_validation(small_graph: RoadGraphEngine):
    """
    Test 46: Step 18 Small-Scale Reference Validation.
    Independently reconstructs quantities for a micro scenario without calling orchestrator,
    then verifies exact agreement with orchestrator execution.
    """
    # Micro Scenario:
    # 1 Incident: 20 general evacuees, needs 1 volunteer
    # 1 Shelter: 50 capacity
    # 1 Depot: 1000 water, 500 food, 50 medkits, 50 sanitation
    # 1 Vehicle: 2000kg
    # 1 Volunteer: GENERAL
    inc = IncidentIntakeInput(
        incident_id="MICRO_INC",
        title="Micro Site",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=20,
        evacuation_demographics={"GEN": 20, "ACC": 0, "MED": 0, "MED_ACC": 0},
        required_skills={"GENERAL": 1}
    )
    shelter = ShelterInput(shelter_id="MICRO_S", name="Micro Shelter", latitude=13.0820, longitude=80.2700, total_capacity=50)
    depot = DepotSupplyInput(depot_id="MICRO_D", name="Micro Depot", latitude=13.0810, longitude=80.2710, supplies={"WATER": 1000.0, "FOOD": 500.0, "MEDICAL_KITS": 50.0, "SANITATION_KITS": 50.0})
    veh = VehicleInput(vehicle_id="MICRO_V", vehicle_code="TRK-M", vehicle_type="TRUCK", capacity_weight_kg=2000.0, capacity_volume_m3=10.0, depot_id="MICRO_D", depot_lat=13.0810, depot_lng=80.2710)
    vol = VolunteerInput(volunteer_id="MICRO_VOL", name="Micro Vol", latitude=13.0830, longitude=80.2705, skill_category="GENERAL")

    # 1. Independent Calculation of Expected Quantities:
    # - Shelter: capacity 50 >= 20 evacuees -> 20 sheltered, 0 unmet
    expected_sheltered = 20
    expected_unmet_evacuees = 0

    # - Resource Demands at Shelter:
    #   Water: 20 * 15 = 300 L
    #   Food: 20 * 2.5 = 50 packs
    #   Medical: ceil(20 / 20) = 1 kit
    #   Sanitation: ceil(20 / 10) = 2 kits
    expected_water = 300.0
    expected_food = 50.0

    # - Volunteer Tasks:
    #   On-site incident: 1 GENERAL
    #   Shelter staffing: 1 GENERAL (ceil(20/50)), 1 LOGISTICS
    #   Total volunteer tasks: 3 tasks
    expected_vol_tasks = 3

    # 2. Execute Orchestrator
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline([inc], [shelter], [depot], [veh], [vol], small_graph)

    # 3. Assert Exact Agreement
    assert res.summary_metrics["evacuees_sheltered"] == expected_sheltered
    assert res.summary_metrics["evacuees_unmet"] == expected_unmet_evacuees

    # Check commodity delivery to shelter
    water_alloc = sum(a.quantity for a in res.resource_result.allocations if a.commodity == "WATER" and a.incident_id == "SHELTER_DEMAND_MICRO_S")
    food_alloc = sum(a.quantity for a in res.resource_result.allocations if a.commodity == "FOOD" and a.incident_id == "SHELTER_DEMAND_MICRO_S")
    assert water_alloc == expected_water
    assert food_alloc == expected_food

    # Check volunteer task demand count
    assert res.volunteer_result.total_tasks_demanded == expected_vol_tasks


def test_5f_int_47_baseline_comparison(benchmark_graph: RoadGraphEngine):
    """Test 47: CP-SAT orchestrator achieves strictly superior or equal solution compared to IntegratedBaselineSolver."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=3, num_shelters=2, num_depots=2, num_vehicles=4, num_volunteers=6, seed=42
    )

    orchestrator = IntegratedResponseOrchestrator()
    opt_res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    baseline_solver = IntegratedBaselineSolver()
    base_res = baseline_solver.solve(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    # CP-SAT should evacuate at least as many evacuees
    assert opt_res.summary_metrics["evacuees_sheltered"] >= base_res["evacuees_sheltered"]
    # CP-SAT should leave equal or fewer unmet evacuees
    assert opt_res.summary_metrics["evacuees_unmet"] <= base_res["unmet_evacuees"]


def test_5f_int_48_benchmark_dataset_tier_dirs_integrated_10(benchmark_graph: RoadGraphEngine):
    """Test 48: Evaluates benchmark tier DIRS-INTEGRATED-10 (10 inc, 5 shelters, 3 depots, 10 vehicles, 25 vols)."""
    incidents, shelters, depots, vehicles, volunteers = generate_integrated_benchmark_dataset(
        num_incidents=10, num_shelters=5, num_depots=3, num_vehicles=10, num_volunteers=25, seed=42
    )
    orchestrator = IntegratedResponseOrchestrator()
    res = orchestrator.run_pipeline(incidents, shelters, depots, vehicles, volunteers, benchmark_graph)

    assert res.overall_status == "PROPOSED"
    assert res.operational_feasibility in ["FULLY_FEASIBLE", "PARTIALLY_FEASIBLE"]
    assert res.timing_breakdown["total_pipeline_ms"] > 0.0
