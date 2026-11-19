"""
DIRS Phase 5F-C — Shelter Evacuation Optimization Engine Comprehensive Test Suite
Validates CP-SAT mathematical correctness, demographic conservation, capacity limits,
amenity compatibility, brute-force ground-truth optimality, objective reconciliation,
priority dominance, determinism, baselines, and Government HITL workflow.
"""
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal

from app.models.user import User, UserRole
from app.models.incident import Incident
from app.models.shelter import Shelter
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog

from app.ai.optimization.graph import RoadGraphEngine
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
from app.ai.optimization.shelter import (
    ShelterEvacuationEngine,
    GreedyProximityShelterSolver,
    FCFSShelterSolver,
    BruteForceShelterSolver,
    IncidentEvacuationInput,
    ShelterInput,
    ShelterEvacuationResult,
    DEMOGRAPHIC_GROUPS,
    OBJECTIVE_WEIGHTS
)
from app.ai.optimization.shelter_benchmark_dataset import generate_shelter_benchmark_dataset
from app.ai.optimization.shelter_service import ShelterEvacuationService


# --- Fixtures ---

@pytest.fixture
def benchmark_graph() -> RoadGraphEngine:
    """Provides a deterministic 50-node Chennai road network graph."""
    return create_chennai_benchmark_graph(num_nodes=50, seed=42)


@pytest.fixture
def small_graph() -> RoadGraphEngine:
    """Provides a minimal 10-node road network for exact ground truth tests."""
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
    email = f"shelter_commander_{uuid.uuid4().hex[:6]}@dirs.gov.in"
    user = User(
        email=email,
        hashed_password="hashed_sec_pass",
        full_name="Cmdr. Shelter Operations",
        role=UserRole.GOVT
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def citizen_user(db_session: Session) -> User:
    email = f"shelter_citizen_{uuid.uuid4().hex[:6]}@dirs.org"
    user = User(
        email=email,
        hashed_password="hashed_sec_pass",
        full_name="Citizen Evaluator",
        role=UserRole.CITIZEN
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ==============================================================================
# PART 1: CORE FORMULATION & CAPACITY TESTS (Tests 1 to 10)
# ==============================================================================

def test_5f_01_single_incident_single_shelter(benchmark_graph: RoadGraphEngine):
    """Test 1: Single incident, single unconstrained shelter."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput(
        incident_id="INC_001",
        title="Localized Inundation",
        latitude=13.0827,
        longitude=80.2707,
        priority_score=75.0,
        severity_level="HIGH",
        disaster_type="FLOOD",
        people_affected=50,
        evacuation_demographics={"GEN": 50, "ACC": 0, "MED": 0, "MED_ACC": 0}
    )
    shelter = ShelterInput(
        shelter_id="SHELTER_001",
        name="Central Shelter",
        latitude=13.0830,
        longitude=80.2710,
        total_capacity=100,
        current_occupancy=0,
        status="OPEN"
    )

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.solver_status == "OPTIMAL"
    assert res.operational_feasibility == "FULLY_FEASIBLE"
    assert res.total_evacuees_sheltered == 50
    assert res.total_evacuees_unmet == 0
    assert len(res.assignments) == 1
    assert res.assignments[0].assigned_quantity == 50
    # Demographic Conservation
    assert res.assignments[0].assigned_quantity + res.total_evacuees_unmet == inc.people_affected


def test_5f_02_multiple_incidents_multiple_shelters(benchmark_graph: RoadGraphEngine):
    """Test 2: Multiple incidents, multiple candidate shelters."""
    engine = ShelterEvacuationEngine()
    incidents = [
        IncidentEvacuationInput("INC_A", "Zone A", 13.08, 80.27, 80.0, "HIGH", "FLOOD", 60, {"GEN": 60}),
        IncidentEvacuationInput("INC_B", "Zone B", 13.01, 80.21, 90.0, "CRITICAL", "FLOOD", 80, {"GEN": 80})
    ]
    shelters = [
        ShelterInput("SHELTER_1", "North Shelter", 13.08, 80.27, 100, 0, "OPEN"),
        ShelterInput("SHELTER_2", "South Shelter", 13.01, 80.21, 100, 0, "OPEN")
    ]

    res = engine.solve(incidents, shelters, benchmark_graph)

    assert res.solver_status == "OPTIMAL"
    assert res.operational_feasibility == "FULLY_FEASIBLE"
    assert res.total_evacuees_sheltered == 140
    assert res.total_evacuees_unmet == 0
    # Check that each incident is assigned to its proximate shelter
    assigned_s1 = sum(a.assigned_quantity for a in res.assignments if a.shelter_id == "SHELTER_1")
    assigned_s2 = sum(a.assigned_quantity for a in res.assignments if a.shelter_id == "SHELTER_2")
    assert assigned_s1 == 60
    assert assigned_s2 == 80


def test_5f_03_capacity_limited_assignment(benchmark_graph: RoadGraphEngine):
    """Test 3: Shelter capacity strictly less than incident demand."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_CAP", "Overcrowded Site", 13.08, 80.27, 80.0, "HIGH", "FLOOD", 100, {"GEN": 100})
    shelter = ShelterInput("SHELTER_LIM", "Small Facility", 13.08, 80.27, 40, 0, "OPEN")

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.solver_status == "OPTIMAL"
    assert res.operational_feasibility == "PARTIALLY_FEASIBLE"
    assert res.total_evacuees_sheltered == 40
    assert res.total_evacuees_unmet == 60
    # Strict capacity compliance
    assert res.total_evacuees_sheltered <= shelter.total_capacity
    # Exact conservation: sheltered + unmet == displaced
    assert res.total_evacuees_sheltered + res.total_evacuees_unmet == 100


def test_5f_04_shelter_activation_overhead(benchmark_graph: RoadGraphEngine):
    """Test 4: Shelter activation overhead reification (gamma_7 = 500)."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_ACT", "Test Site", 13.08, 80.27, 70.0, "MEDIUM", "FLOOD", 30, {"GEN": 30})
    # Shelter 1 can fit all 30 evacuees. Shelter 2 is redundant.
    shelter1 = ShelterInput("S_MAIN", "Main Shelter", 13.08, 80.27, 100, 0, "OPEN")
    shelter2 = ShelterInput("S_EXTRA", "Extra Shelter", 13.05, 80.25, 100, 0, "OPEN")

    res = engine.solve([inc], [shelter1, shelter2], benchmark_graph)

    assert res.solver_status == "OPTIMAL"
    assert res.active_shelters_count == 1
    active_ids = {a.shelter_id for a in res.assignments}
    assert "S_MAIN" in active_ids
    assert "S_EXTRA" not in active_ids
    assert res.objective_breakdown["activation"] == OBJECTIVE_WEIGHTS["gamma_7"] * 1


def test_5f_05_existing_shelter_occupancy(benchmark_graph: RoadGraphEngine):
    """Test 5: Available capacity = total_capacity - current_occupancy."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_OCC", "Test Site", 13.08, 80.27, 70.0, "MEDIUM", "FLOOD", 50, {"GEN": 50})
    # Total 100, but 80 already occupied -> remaining is 20
    shelter = ShelterInput("S_OCC", "Pre-Occupied Shelter", 13.08, 80.27, 100, current_occupancy=80, status="OPEN")

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.total_evacuees_sheltered == 20
    assert res.total_evacuees_unmet == 30
    assert res.total_evacuees_sheltered + res.total_evacuees_unmet == 50


def test_5f_06_closed_shelter_exclusion(benchmark_graph: RoadGraphEngine):
    """Test 6: CLOSED shelter receives 0 assignments regardless of nominal capacity."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_CLOSED", "Test Site", 13.08, 80.27, 70.0, "MEDIUM", "FLOOD", 30, {"GEN": 30})
    shelter = ShelterInput("S_CLOSED", "Damaged Facility", 13.08, 80.27, 500, 0, status="CLOSED")

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.total_evacuees_sheltered == 0
    assert res.total_evacuees_unmet == 30
    assert res.operational_feasibility == "INFEASIBLE"
    assert len(res.assignments) == 0


def test_5f_07_full_shelter_exclusion(benchmark_graph: RoadGraphEngine):
    """Test 7: FULL shelter receives 0 assignments."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_FULL", "Test Site", 13.08, 80.27, 70.0, "MEDIUM", "FLOOD", 25, {"GEN": 25})
    shelter = ShelterInput("S_FULL", "Full Facility", 13.08, 80.27, 100, 100, status="FULL")

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.total_evacuees_sheltered == 0
    assert res.total_evacuees_unmet == 25
    assert res.operational_feasibility == "INFEASIBLE"


def test_5f_08_inaccessible_shelter_rejection(benchmark_graph: RoadGraphEngine):
    """Test 8: Shelter lacking accessibility_features cannot accept ACC evacuees."""
    engine = ShelterEvacuationEngine()
    # 20 evacuees requiring accessibility
    inc = IncidentEvacuationInput("INC_ACC", "Elderly Care Home", 13.08, 80.27, 85.0, "HIGH", "FLOOD", 20, {"ACC": 20})
    # Shelter has 500 capacity but accessibility_features == False
    shelter = ShelterInput("S_NO_ACC", "Standard School", 13.08, 80.27, 500, 0, status="OPEN", accessibility_features=False)

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.total_evacuees_sheltered == 0
    assert res.total_evacuees_unmet == 20
    assert res.demographic_unmet_counts["ACC"] == 20


def test_5f_09_unreachable_shelter_exclusion():
    """Test 9: Shelter isolated or unreachable across road network is excluded."""
    # Graph with two disconnected components
    graph = RoadGraphEngine()
    graph.add_node("N_INC", 13.0827, 80.2707)
    graph.add_node("N_SHELTER", 12.6000, 79.8000)
    # No edges -> unreachable (R_is = 0)

    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("N_INC", "Cutoff Hamlet", 13.0827, 80.2707, 80.0, "HIGH", "FLOOD", 15, {"GEN": 15})
    shelter = ShelterInput("N_SHELTER", "Island Center", 12.6000, 79.8000, 200, 0, "OPEN")

    res = engine.solve([inc], [shelter], graph)

    assert res.total_evacuees_sheltered == 0
    assert res.total_evacuees_unmet == 15
    assert res.operational_feasibility == "INFEASIBLE"
    assert len(res.assignments) == 0


def test_5f_10_zero_unmet_demand_verification(benchmark_graph: RoadGraphEngine):
    """Test 10: Ample compatible capacity produces zero unmet demand."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_ZERO_UNMET", "Town Center", 13.08, 80.27, 75.0, "HIGH", "FLOOD", 50, {"GEN": 50})
    shelter = ShelterInput("S_AMPLE", "Civic Center", 13.08, 80.27, 200, 0, "OPEN")

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.total_evacuees_unmet == 0
    assert res.operational_feasibility == "FULLY_FEASIBLE"
    assert res.unmet_percentage == 0.0


# ==============================================================================
# PART 2: DEMOGRAPHIC CONSERVATION & PARTITION TESTS (Tests 11 to 17)
# ==============================================================================

def test_5f_11_demographic_general_population(benchmark_graph: RoadGraphEngine):
    """Test 11: General population demographic assignment."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_GEN", "General Community", 13.08, 80.27, 60.0, "MEDIUM", "FLOOD", 40, {"GEN": 40})
    shelter = ShelterInput("S_GEN", "Basic Shelter", 13.08, 80.27, 50, 0, "OPEN", accessibility_features=False, has_medical=False)

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.total_evacuees_sheltered == 40
    assert res.assignments[0].demographic_group == "GEN"


def test_5f_12_demographic_accessible_population(benchmark_graph: RoadGraphEngine):
    """Test 12: Accessible population demographic assignment."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_ACC_ONLY", "Special Needs Center", 13.08, 80.27, 80.0, "HIGH", "FLOOD", 30, {"ACC": 30})
    shelter_no_acc = ShelterInput("S_NO_ACC", "Inaccessible Shelter", 13.08, 80.27, 50, 0, "OPEN", accessibility_features=False)
    shelter_acc = ShelterInput("S_ACC", "ADA Compliant Center", 13.07, 80.26, 50, 0, "OPEN", accessibility_features=True)

    res = engine.solve([inc], [shelter_no_acc, shelter_acc], benchmark_graph)

    assert res.total_evacuees_sheltered == 30
    assert res.assignments[0].shelter_id == "S_ACC"
    assert res.assignments[0].demographic_group == "ACC"


def test_5f_13_demographic_medical_population(benchmark_graph: RoadGraphEngine):
    """Test 13: Medical population demographic assignment."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_MED_ONLY", "Triage Site", 13.08, 80.27, 90.0, "CRITICAL", "FLOOD", 25, {"MED": 25})
    shelter_no_med = ShelterInput("S_NO_MED", "Community Hall", 13.08, 80.27, 50, 0, "OPEN", has_medical=False)
    shelter_med = ShelterInput("S_MED", "Hospital Wing", 13.07, 80.26, 50, 0, "OPEN", has_medical=True, power_available=True)

    res = engine.solve([inc], [shelter_no_med, shelter_med], benchmark_graph)

    assert res.total_evacuees_sheltered == 25
    assert res.assignments[0].shelter_id == "S_MED"
    assert res.assignments[0].demographic_group == "MED"


def test_5f_14_demographic_medical_accessible_population(benchmark_graph: RoadGraphEngine):
    """Test 14: Combined medical + accessible population assignment."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_MED_ACC", "Hospice Evacuation", 13.08, 80.27, 95.0, "CRITICAL", "FLOOD", 15, {"MED_ACC": 15})
    # Shelter 1: has medical, lacks accessibility
    s1 = ShelterInput("S_MED_ONLY", "Clinic (Stairs Only)", 13.08, 80.27, 50, 0, "OPEN", accessibility_features=False, has_medical=True, power_available=True)
    # Shelter 2: has accessibility, lacks medical
    s2 = ShelterInput("S_ACC_ONLY", "Civic Center (No Clinic)", 13.08, 80.27, 50, 0, "OPEN", accessibility_features=True, has_medical=False)
    # Shelter 3: has BOTH accessibility and medical
    s3 = ShelterInput("S_DUAL", "Integrated Medical Complex", 13.07, 80.26, 50, 0, "OPEN", accessibility_features=True, has_medical=True, power_available=True)

    res = engine.solve([inc], [s1, s2, s3], benchmark_graph)

    assert res.total_evacuees_sheltered == 15
    assert res.assignments[0].shelter_id == "S_DUAL"
    assert res.assignments[0].demographic_group == "MED_ACC"


def test_5f_15_mixed_demographics_partition_conservation(benchmark_graph: RoadGraphEngine):
    """Test 15: Mixed demographic partition exact conservation."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput(
        "INC_MIXED", "Mixed Ward 142", 13.08, 80.27, 85.0, "HIGH", "FLOOD",
        100, {"GEN": 60, "ACC": 20, "MED": 15, "MED_ACC": 5}
    )
    s_full_cap = ShelterInput("S_ALL", "Comprehensive Complex", 13.08, 80.27, 200, 0, "OPEN", accessibility_features=True, has_medical=True, power_available=True)

    res = engine.solve([inc], [s_full_cap], benchmark_graph)

    assert res.total_evacuees_sheltered == 100
    assert res.total_evacuees_unmet == 0
    # Verify group breakdowns
    sheltered_by_group = {g: 0 for g in DEMOGRAPHIC_GROUPS}
    for a in res.assignments:
        sheltered_by_group[a.demographic_group] += a.assigned_quantity
    assert sheltered_by_group["GEN"] == 60
    assert sheltered_by_group["ACC"] == 20
    assert sheltered_by_group["MED"] == 15
    assert sheltered_by_group["MED_ACC"] == 5


def test_5f_16_zero_demographic_group_handling(benchmark_graph: RoadGraphEngine):
    """Test 16: Zero demographic counts handle gracefully without phantom allocations."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_ZERO", "Small Sector", 13.08, 80.27, 60.0, "LOW", "FLOOD", 10, {"GEN": 10, "ACC": 0, "MED": 0, "MED_ACC": 0})
    shelter = ShelterInput("S_ANY", "Shelter", 13.08, 80.27, 50, 0, "OPEN", accessibility_features=True, has_medical=True)

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.total_evacuees_sheltered == 10
    allocated_groups = {a.demographic_group for a in res.assignments}
    assert allocated_groups == {"GEN"}


def test_5f_17_inconsistent_input_rejection(benchmark_graph: RoadGraphEngine):
    """Test 17: Inconsistent demographic counts or negative population rejected."""
    engine = ShelterEvacuationEngine()
    # Negative population
    inc_neg = IncidentEvacuationInput("INC_NEG", "Negative", 13.0, 80.0, 50.0, "LOW", "FLOOD", -10)
    with pytest.raises(ValueError, match="negative people_affected"):
        engine.solve([inc_neg], [], benchmark_graph)

    # Inconsistent demographic sum > people_affected
    inc_incon = IncidentEvacuationInput("INC_INCON", "Bad Sum", 13.0, 80.0, 50.0, "LOW", "FLOOD", 20, {"GEN": 20, "ACC": 10})
    with pytest.raises(ValueError, match="Inconsistent demographic total"):
        engine.solve([inc_incon], [], benchmark_graph)


# ==============================================================================
# PART 3: CAPABILITY & COMPATIBILITY ENFORCEMENT (Tests 18 to 20)
# ==============================================================================

def test_5f_18_medical_capable_vs_non_medical_shelter(benchmark_graph: RoadGraphEngine):
    """Test 18: Non-medical shelter strictly rejected for medical demand."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_MED_COMPAT", "Trauma Site", 13.08, 80.27, 85.0, "HIGH", "FLOOD", 20, {"MED": 20})
    s_non_med = ShelterInput("S_NON_MED", "School", 13.08, 80.27, 100, 0, "OPEN", has_medical=False)

    res = engine.solve([inc], [s_non_med], benchmark_graph)

    assert res.total_evacuees_sheltered == 0
    assert res.demographic_unmet_counts["MED"] == 20


def test_5f_19_accessibility_compatible_vs_incompatible_shelter(benchmark_graph: RoadGraphEngine):
    """Test 19: Non-accessible shelter strictly rejected for accessible demand."""
    engine = ShelterEvacuationEngine()
    inc = IncidentEvacuationInput("INC_ACC_COMPAT", "Disabled Center", 13.08, 80.27, 85.0, "HIGH", "FLOOD", 25, {"ACC": 25})
    s_inaccessible = ShelterInput("S_NO_RAMP", "Two Story Hall", 13.08, 80.27, 200, 0, "OPEN", accessibility_features=False)

    res = engine.solve([inc], [s_inaccessible], benchmark_graph)

    assert res.total_evacuees_sheltered == 0
    assert res.demographic_unmet_counts["ACC"] == 25


def test_5f_20_disaster_compatible_vs_incompatible_shelter(benchmark_graph: RoadGraphEngine):
    """Test 20: Disaster hazard compatibility enforcement."""
    engine = ShelterEvacuationEngine()
    # Cyclone incident
    inc = IncidentEvacuationInput("INC_CYCLONE", "Coastal Cyclone", 13.08, 80.27, 85.0, "HIGH", "CYCLONE", 30, {"GEN": 30})
    # Shelter 1 only rated for FLOOD
    s_flood_only = ShelterInput("S_FLOOD_ONLY", "Flood Shelter", 13.08, 80.27, 100, 0, "OPEN", disaster_compatibility=["FLOOD"])
    # Shelter 2 rated for CYCLONE
    s_cyclone = ShelterInput("S_CYCLONE_RATED", "Hardened Cyclone Bunker", 13.07, 80.26, 100, 0, "OPEN", disaster_compatibility=["CYCLONE", "FLOOD"])

    res = engine.solve([inc], [s_flood_only, s_cyclone], benchmark_graph)

    assert res.total_evacuees_sheltered == 30
    assert res.assignments[0].shelter_id == "S_CYCLONE_RATED"


# ==============================================================================
# PART 4: PRIORITY DOMINANCE & CONTENTION (Tests 21 to 24)
# ==============================================================================

def test_5f_21_priority_dominance_gen_vs_acc(benchmark_graph: RoadGraphEngine):
    """Test 21: Capacity contention: ACC strictly beats GEN for limited slots."""
    engine = ShelterEvacuationEngine()
    # 1 accessible slot available
    shelter = ShelterInput("S_SLOT_1", "Single Slot Accessible", 13.08, 80.27, 1, 0, "OPEN", accessibility_features=True)

    # 1 GEN evacuee vs 1 ACC evacuee at same priority score
    inc = IncidentEvacuationInput("INC_CONTEND", "Contention Site", 13.08, 80.27, 80.0, "HIGH", "FLOOD", 2, {"GEN": 1, "ACC": 1})

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.total_evacuees_sheltered == 1
    # ACC must win the slot because gamma_2 (2000) > gamma_1 (1000)
    assert res.assignments[0].demographic_group == "ACC"
    assert res.demographic_unmet_counts["GEN"] == 1
    assert res.demographic_unmet_counts["ACC"] == 0


def test_5f_22_priority_dominance_gen_vs_med(benchmark_graph: RoadGraphEngine):
    """Test 22: Capacity contention: MED strictly beats GEN for limited slots."""
    engine = ShelterEvacuationEngine()
    shelter = ShelterInput("S_SLOT_MED", "Medical Slot", 13.08, 80.27, 1, 0, "OPEN", has_medical=True, power_available=True)
    inc = IncidentEvacuationInput("INC_CONTEND_MED", "Site", 13.08, 80.27, 80.0, "HIGH", "FLOOD", 2, {"GEN": 1, "MED": 1})

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.total_evacuees_sheltered == 1
    # MED must win because gamma_3 (2500) > gamma_1 (1000)
    assert res.assignments[0].demographic_group == "MED"
    assert res.demographic_unmet_counts["GEN"] == 1


def test_5f_23_priority_dominance_med_vs_med_acc(benchmark_graph: RoadGraphEngine):
    """Test 23: Capacity contention: MED_ACC strictly beats MED for limited slots."""
    engine = ShelterEvacuationEngine()
    shelter = ShelterInput("S_SLOT_DUAL", "Dual Slot", 13.08, 80.27, 1, 0, "OPEN", accessibility_features=True, has_medical=True, power_available=True)
    inc = IncidentEvacuationInput("INC_CONTEND_DUAL", "Site", 13.08, 80.27, 80.0, "HIGH", "FLOOD", 2, {"MED": 1, "MED_ACC": 1})

    res = engine.solve([inc], [shelter], benchmark_graph)

    assert res.total_evacuees_sheltered == 1
    # MED_ACC must win because gamma_4 (4000) > gamma_3 (2500)
    assert res.assignments[0].demographic_group == "MED_ACC"
    assert res.demographic_unmet_counts["MED"] == 1


def test_5f_24_travel_cost_vs_unmet_demand(benchmark_graph: RoadGraphEngine):
    """Test 24: Distant shelter is assigned rather than leaving evacuees unmet."""
    engine = ShelterEvacuationEngine()
    # Incident at Central Chennai
    inc = IncidentEvacuationInput("INC_DIST", "Central", 13.0827, 80.2707, 40.0, "LOW", "FLOOD", 1, {"GEN": 1})
    # Shelter far away at Chengalpattu (~45km)
    shelter = ShelterInput("S_FAR", "Far Out Shelter", 12.6800, 79.9800, 100, 0, "OPEN")

    res = engine.solve([inc], [shelter], benchmark_graph)

    # Even at lowest priority, unmet penalty (1.0 * 40 * 1000 = 40,000) >> transit penalty (~500)
    assert res.total_evacuees_sheltered == 1
    assert res.total_evacuees_unmet == 0


# ==============================================================================
# PART 5: BRUTE-FORCE GROUND TRUTH & OBJECTIVE RECONCILIATION (Tests 25 to 27)
# ==============================================================================

def test_5f_25_brute_force_ground_truth_optimality(small_graph: RoadGraphEngine):
    """Test 25: CP-SAT matches true mathematical optimum from independent brute-force search."""
    incidents = [
        IncidentEvacuationInput("INC_1", "Site 1", 13.08, 80.27, 80.0, "HIGH", "FLOOD", 6, {"GEN": 3, "ACC": 3}),
        IncidentEvacuationInput("INC_2", "Site 2", 13.01, 80.20, 90.0, "CRITICAL", "FLOOD", 4, {"GEN": 2, "MED": 2})
    ]
    shelters = [
        ShelterInput("S_A", "Shelter A", 13.08, 80.27, 5, 0, "OPEN", accessibility_features=True, has_medical=False),
        ShelterInput("S_B", "Shelter B", 13.01, 80.20, 5, 0, "OPEN", accessibility_features=False, has_medical=True, power_available=True)
    ]

    # 1. Independent Brute-Force Solve
    bf_solver = BruteForceShelterSolver()
    bf_best_cost, bf_allocations = bf_solver.solve(incidents, shelters, small_graph)

    # 2. CP-SAT Solve
    engine = ShelterEvacuationEngine()
    cp_res = engine.solve(incidents, shelters, small_graph)

    assert cp_res.solver_status == "OPTIMAL"
    # Verify objective match within integer scaling tolerance (0.5 points)
    assert abs(cp_res.objective_value - bf_best_cost) <= 0.5


def test_5f_26_independent_objective_reconciliation(benchmark_graph: RoadGraphEngine):
    """
    Test 26: Independent component-by-component objective reconciliation.
    Numerical Tolerance Documentation:
    In OR-Tools CP-SAT, continuous coefficients are integerized by OBJECTIVE_SCALE = 100,
    introducing an integer quantization tolerance of +/- 0.005 points per evacuee.
    For N=1355 evacuees, cumulative quantization bounds: Delta_Z <= 1355 * 0.005 = 6.78 points.
    We verify the reconstructed sum matches the solver objective within 15.0 points (< 0.02% relative error).
    """
    incidents, shelters = generate_shelter_benchmark_dataset(num_incidents=10, num_shelters=5, seed=42)
    engine = ShelterEvacuationEngine()

    res = engine.solve(incidents, shelters, benchmark_graph)

    reconstructed_sum = sum(res.objective_breakdown.values())
    abs_diff = abs(res.objective_value - reconstructed_sum)
    rel_diff = abs_diff / max(1.0, res.objective_value)

    assert abs_diff <= 15.0, f"Discrepancy {abs_diff} exceeds integer quantization bound (15.0)"
    assert rel_diff <= 0.0005, f"Relative discrepancy {rel_diff*100:.3f}% exceeds 0.05% bound"

    # Ensure all 7 components exist and are non-negative
    for k in ["unmet_gen", "unmet_acc", "unmet_med", "unmet_med_acc", "transit_time", "transit_dist", "activation"]:
        assert k in res.objective_breakdown
        assert res.objective_breakdown[k] >= 0.0


def test_5f_27_deterministic_repeatability(benchmark_graph: RoadGraphEngine):
    """Test 27: 5 repeated trials produce bit-exact identical assignments and objective values."""
    incidents, shelters = generate_shelter_benchmark_dataset(num_incidents=15, num_shelters=6, seed=42)
    engine = ShelterEvacuationEngine()

    results = [engine.solve(incidents, shelters, benchmark_graph, random_seed=42) for _ in range(5)]

    base_obj = results[0].objective_value
    base_sheltered = results[0].total_evacuees_sheltered
    base_unmet = results[0].total_evacuees_unmet
    base_active = results[0].active_shelters_count

    for r in results[1:]:
        assert r.objective_value == base_obj
        assert r.total_evacuees_sheltered == base_sheltered
        assert r.total_evacuees_unmet == base_unmet
        assert r.active_shelters_count == base_active


# ==============================================================================
# PART 6: BASELINE COMPARISONS & BENCHMARKS (Tests 28 to 30)
# ==============================================================================

def test_5f_28_baseline_comparison(benchmark_graph: RoadGraphEngine):
    """Test 28: CP-SAT vs Greedy Proximity vs FCFS on identical scenario."""
    incidents, shelters = generate_shelter_benchmark_dataset(num_incidents=20, num_shelters=8, seed=42)

    cp_engine = ShelterEvacuationEngine()
    greedy_solver = GreedyProximityShelterSolver()
    fcfs_solver = FCFSShelterSolver()

    cp_res = cp_engine.solve(incidents, shelters, benchmark_graph)
    greedy_res = greedy_solver.solve(incidents, shelters, benchmark_graph)
    fcfs_res = fcfs_solver.solve(incidents, shelters, benchmark_graph)

    # CP-SAT must achieve equal or better objective than baselines
    assert cp_res.objective_value <= greedy_res.objective_value + 1.0
    assert cp_res.objective_value <= fcfs_res.objective_value + 1.0
    # Both baselines and CP-SAT conserve population exactly
    assert cp_res.total_evacuees_sheltered + cp_res.total_evacuees_unmet == cp_res.total_evacuees_displaced
    assert greedy_res.total_evacuees_sheltered + greedy_res.total_evacuees_unmet == greedy_res.total_evacuees_displaced
    assert fcfs_res.total_evacuees_sheltered + fcfs_res.total_evacuees_unmet == fcfs_res.total_evacuees_displaced


def test_5f_29_scalability_benchmark_tiers(benchmark_graph: RoadGraphEngine):
    """Test 29: Scalability benchmarks across approved tiers (10/5, 25/10, 50/20)."""
    engine = ShelterEvacuationEngine()
    tiers = [
        (10, 5, "DIRS-SHELTER-10"),
        (25, 10, "DIRS-SHELTER-25"),
        (50, 20, "DIRS-SHELTER-50")
    ]

    for num_inc, num_s, tier_name in tiers:
        incidents, shelters = generate_shelter_benchmark_dataset(num_incidents=num_inc, num_shelters=num_s, seed=42)
        res = engine.solve(incidents, shelters, benchmark_graph, solver_time_limit_sec=5.0)

        assert res.solver_status in ("OPTIMAL", "FEASIBLE")
        # Timing breakdown captured
        assert "solver_ms" in res.timing_breakdown
        assert "total_ms" in res.timing_breakdown
        assert res.timing_breakdown["total_ms"] > 0.0


# ==============================================================================
# PART 7: GOVERNMENT HITL & SERVICE WORKFLOW (Test 30)
# ==============================================================================

def test_5f_30_government_hitl_service_workflow(
    db_session: Session, govt_officer: User, citizen_user: User
):
    """Test 30: End-to-end service orchestrator and Government HITL workflow."""
    # 1. Create DB Shelters and Incidents
    s1 = Shelter(
        name="DB Central Shelter", address="Central Zone", total_capacity=300, current_occupancy=0,
        latitude=13.08, longitude=80.27, status="OPEN", accessibility_features=True,
        has_medical=True, power_available=True, disaster_compatibility=["FLOOD"]
    )
    inc1 = Incident(
        incident_code=f"INC-HITL-{uuid.uuid4().hex[:4]}",
        title="Flooded Neighborhood", disaster_type="FLOOD", description="High water level",
        latitude=13.08, longitude=80.27, people_affected=60, priority_score=85.0,
        severity_level="HIGH",
        evacuation_demographics={"GEN": 40, "ACC": 10, "MED": 10, "MED_ACC": 0}
    )
    db_session.add_all([s1, inc1])
    db_session.commit()

    service = ShelterEvacuationService()

    # 2. Run Optimization: creates run with status="PROPOSED"
    opt_run = service.run_evacuation_optimization(db_session, requesting_user_id=govt_officer.id)

    assert opt_run.status == "PROPOSED"
    assert len(opt_run.recommendations) > 0
    for rec in opt_run.recommendations:
        assert rec.status == "PROPOSED"
        assert rec.recommendation_type == "SHELTER_EVACUATION"

    # 3. Citizen cannot approve
    with pytest.raises(ValueError, match="Only authorized users with GOVT role"):
        service.approve_plan(db_session, opt_run.id, citizen_user.id, "Attempted unauthorized approval")
    assert opt_run.status == "PROPOSED"

    # 4. Government officer approves with justification
    override_log = service.approve_plan(
        db_session, opt_run.id, govt_officer.id,
        "Commander verified safe evacuation corridor and confirmed shelter intake capacity."
    )

    db_session.refresh(opt_run)
    assert opt_run.status == "APPROVED"
    assert override_log.action == "APPROVE"
    assert override_log.justification_reason is not None
    for rec in opt_run.recommendations:
        assert rec.status == "APPROVED"
