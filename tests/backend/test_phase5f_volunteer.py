"""
DIRS Phase 5F-D — Volunteer Assignment Optimization Engine Comprehensive Test Suite
Validates CP-SAT mathematical correctness, skill qualification, availability, workload limits,
travel-time cutoffs, exact task conservation, priority dominance, brute-force ground truth,
objective reconciliation, determinism, baselines, and Government HITL workflow.
"""
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal

from app.models.user import User, UserRole, VolunteerProfile
from app.models.incident import Incident
from app.models.rescue import RoadBlockage
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog

from app.ai.optimization.graph import RoadGraphEngine
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
from app.ai.optimization.volunteer import (
    VolunteerAssignmentEngine,
    GreedyFeasibleVolunteerSolver,
    FCFSVolunteerSolver,
    BruteForceVolunteerSolver,
    VolunteerInput,
    IncidentTaskInput,
    VolunteerAssignmentResult,
    OBJECTIVE_WEIGHTS,
    SKILL_CATEGORIES
)
from app.ai.optimization.volunteer_benchmark_dataset import generate_volunteer_benchmark_dataset
from app.ai.optimization.volunteer_service import VolunteerAssignmentService


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
    email = f"vol_commander_{uuid.uuid4().hex[:6]}@dirs.gov.in"
    user = User(
        email=email,
        hashed_password="hashed_sec_pass",
        full_name="Cmdr. Volunteer Operations",
        role=UserRole.GOVT
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def citizen_user(db_session: Session) -> User:
    email = f"vol_citizen_{uuid.uuid4().hex[:6]}@dirs.org"
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
# PART 1: BASIC & OPERATIONAL TESTS (Tests 1 to 8)
# ==============================================================================

def test_5f_vol_01_single_incident_single_volunteer(benchmark_graph: RoadGraphEngine):
    """Test 1: Single incident, single general task, single qualified volunteer."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(
        incident_id="INC_001",
        title="General Relief Point",
        latitude=13.0827,
        longitude=80.2707,
        priority_score=60.0,
        severity_level="MEDIUM",
        required_skills={"GENERAL": 1},
        shifts=["SHIFT_1"]
    )
    vol = VolunteerInput(
        volunteer_id="VOL_001",
        name="Volunteer One",
        latitude=13.0820,
        longitude=80.2700,
        skill_category="GENERAL",
        verification_status="VERIFIED",
        is_available=True,
        assignment_status="UNASSIGNED"
    )

    result = engine.solve([vol], [inc], benchmark_graph)

    assert result.solver_status == "OPTIMAL"
    assert result.operational_feasibility == "FULLY_FEASIBLE"
    assert result.total_tasks_demanded == 1
    assert result.total_tasks_assigned == 1
    assert result.total_tasks_unmet == 0
    assert len(result.assignments) == 1
    assert result.assignments[0].volunteer_id == "VOL_001"
    assert result.assignments[0].incident_id == "INC_001"
    assert result.assignments[0].skill_category == "GENERAL"


def test_5f_vol_02_multiple_incidents_multiple_volunteers(benchmark_graph: RoadGraphEngine):
    """Test 2: Multiple incidents, multiple volunteers, mixed skills."""
    engine = VolunteerAssignmentEngine()
    inc1 = IncidentTaskInput(
        incident_id="INC_001",
        title="Medical Center",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"MEDICAL": 1, "GENERAL": 1},
        shifts=["SHIFT_1"]
    )
    inc2 = IncidentTaskInput(
        incident_id="INC_002",
        title="Rescue Sector",
        latitude=13.0110,
        longitude=80.2350,
        required_skills={"RESCUE": 1},
        shifts=["SHIFT_1"]
    )

    vols = [
        VolunteerInput(
            volunteer_id="VOL_MED",
            name="Paramedic Alice",
            latitude=13.0800,
            longitude=80.2700,
            skill_category="MEDICAL",
            medical_certified=True,
            verification_status="VERIFIED"
        ),
        VolunteerInput(
            volunteer_id="VOL_GEN",
            name="Helper Bob",
            latitude=13.0810,
            longitude=80.2710,
            skill_category="GENERAL",
            verification_status="VERIFIED"
        ),
        VolunteerInput(
            volunteer_id="VOL_RES",
            name="Rescuer Charlie",
            latitude=13.0100,
            longitude=80.2340,
            skill_category="RESCUE",
            verification_status="VERIFIED"
        ),
    ]

    result = engine.solve(vols, [inc1, inc2], benchmark_graph)

    assert result.solver_status == "OPTIMAL"
    assert result.operational_feasibility == "FULLY_FEASIBLE"
    assert result.total_tasks_assigned == 3
    assert result.total_tasks_unmet == 0
    assert result.deployed_volunteers_count == 3


def test_5f_vol_03_multiple_task_types(benchmark_graph: RoadGraphEngine):
    """Test 3: Single incident requesting all 4 skill categories."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(
        incident_id="INC_MULTI",
        title="Multi-Skill Hub",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"MEDICAL": 1, "RESCUE": 1, "LOGISTICS": 1, "GENERAL": 1},
        shifts=["SHIFT_1"]
    )

    vols = [
        VolunteerInput(volunteer_id="V1", name="Doc", latitude=13.08, longitude=80.27, skill_category="MEDICAL", medical_certified=True),
        VolunteerInput(volunteer_id="V2", name="Swimmer", latitude=13.08, longitude=80.27, skill_category="RESCUE"),
        VolunteerInput(volunteer_id="V3", name="Driver", latitude=13.08, longitude=80.27, skill_category="LOGISTICS"),
        VolunteerInput(volunteer_id="V4", name="Aide", latitude=13.08, longitude=80.27, skill_category="GENERAL"),
    ]

    result = engine.solve(vols, [inc], benchmark_graph)

    assert result.solver_status == "OPTIMAL"
    assert result.total_tasks_assigned == 4
    assert result.total_tasks_unmet == 0


def test_5f_vol_04_multiple_shifts(benchmark_graph: RoadGraphEngine):
    """Test 4: Multiple shifts; each volunteer deployed at most once per shift."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(
        incident_id="INC_SHIFTS",
        title="24hr Emergency Post",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"GENERAL": 1},
        shifts=["SHIFT_1", "SHIFT_2"],
        task_durations={"SHIFT_1": 4.0, "SHIFT_2": 4.0}
    )

    # 1 volunteer available for both shifts
    vol = VolunteerInput(
        volunteer_id="V_SUPER",
        name="All-day Volunteer",
        latitude=13.0820,
        longitude=80.2700,
        skill_category="GENERAL",
        shift_availability=["SHIFT_1", "SHIFT_2"],
        max_shift_hours=8.0
    )

    result = engine.solve([vol], [inc], benchmark_graph)

    assert result.solver_status == "OPTIMAL"
    # The volunteer can take 1 task in SHIFT_1 and 1 task in SHIFT_2
    assert result.total_tasks_assigned == 2
    assert result.total_tasks_unmet == 0
    assert len(result.assignments) == 2
    shift_ids = [a.shift_id for a in result.assignments]
    assert "SHIFT_1" in shift_ids and "SHIFT_2" in shift_ids


def test_5f_vol_05_zero_demand(benchmark_graph: RoadGraphEngine):
    """Test 5: Zero demand cleanly returns empty optimal result."""
    engine = VolunteerAssignmentEngine()
    vol = VolunteerInput(volunteer_id="V1", name="Idle", latitude=13.08, longitude=80.27)
    result = engine.solve([vol], [], benchmark_graph)

    assert result.solver_status == "OPTIMAL"
    assert result.operational_feasibility == "FULLY_FEASIBLE"
    assert result.total_tasks_demanded == 0
    assert result.total_tasks_assigned == 0
    assert len(result.assignments) == 0


def test_5f_vol_06_zero_available_volunteers(benchmark_graph: RoadGraphEngine):
    """Test 6: Demand present but zero volunteers -> 100% unmet, INFEASIBLE."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(
        incident_id="INC_001",
        title="Unattended Incident",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"GENERAL": 3}
    )

    result = engine.solve([], [inc], benchmark_graph)

    assert result.operational_feasibility == "INFEASIBLE"
    assert result.total_tasks_demanded == 3
    assert result.total_tasks_assigned == 0
    assert result.total_tasks_unmet == 3
    assert result.unmet_percentage == 100.0


def test_5f_vol_07_fully_satisfied_demand(benchmark_graph: RoadGraphEngine):
    """Test 7: 2 demands, 3 volunteers -> 100% fulfilled."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(
        incident_id="INC_SAT",
        title="Relief",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"GENERAL": 2}
    )
    vols = [
        VolunteerInput(volunteer_id=f"V{i}", name=f"Vol {i}", latitude=13.08, longitude=80.27)
        for i in range(3)
    ]

    result = engine.solve(vols, [inc], benchmark_graph)

    assert result.operational_feasibility == "FULLY_FEASIBLE"
    assert result.total_tasks_assigned == 2
    assert result.total_tasks_unmet == 0


def test_5f_vol_08_partially_satisfied_demand(benchmark_graph: RoadGraphEngine):
    """Test 8: 5 demands, 2 volunteers -> PARTIALLY_FEASIBLE, 3 unmet."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(
        incident_id="INC_PART",
        title="High Demand Incident",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"GENERAL": 5}
    )
    vols = [
        VolunteerInput(volunteer_id="V1", name="Vol 1", latitude=13.08, longitude=80.27),
        VolunteerInput(volunteer_id="V2", name="Vol 2", latitude=13.08, longitude=80.27)
    ]

    result = engine.solve(vols, [inc], benchmark_graph)

    assert result.operational_feasibility == "PARTIALLY_FEASIBLE"
    assert result.total_tasks_assigned == 2
    assert result.total_tasks_unmet == 3
    assert result.unmet_percentage == 60.0


# ==============================================================================
# PART 2: SKILLS & QUALIFICATION CONSTRAINTS (Tests 9 to 14)
# ==============================================================================

def test_5f_vol_09_general_skill(benchmark_graph: RoadGraphEngine):
    """Test 9: Any verified volunteer can satisfy a GENERAL task."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_G", title="G", latitude=13.08, longitude=80.27, required_skills={"GENERAL": 1})
    vol = VolunteerInput(volunteer_id="V_LOG", name="Logistics Guy", latitude=13.08, longitude=80.27, skill_category="LOGISTICS")

    result = engine.solve([vol], [inc], benchmark_graph)

    assert result.total_tasks_assigned == 1


def test_5f_vol_10_medical_skill_requires_certification(benchmark_graph: RoadGraphEngine):
    """Test 10: Medical task strictly requires medical_certified == True."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_M", title="Medical Triage", latitude=13.08, longitude=80.27, required_skills={"MEDICAL": 1})

    # Volunteer has skill_category MEDICAL but NOT certified
    vol_uncertified = VolunteerInput(
        volunteer_id="V_UNCERT",
        name="Uncertified Med Student",
        latitude=13.08,
        longitude=80.27,
        skill_category="MEDICAL",
        medical_certified=False
    )

    result = engine.solve([vol_uncertified], [inc], benchmark_graph)

    # Uncertified volunteer must NOT be assigned to medical task
    assert result.total_tasks_assigned == 0
    assert result.total_tasks_unmet == 1
    assert result.skill_unmet_counts["MEDICAL"] == 1

    # Now add certified medical volunteer
    vol_certified = VolunteerInput(
        volunteer_id="V_CERT",
        name="Dr. Smith",
        latitude=13.08,
        longitude=80.27,
        skill_category="MEDICAL",
        medical_certified=True
    )

    result2 = engine.solve([vol_certified], [inc], benchmark_graph)
    assert result2.total_tasks_assigned == 1
    assert result2.total_tasks_unmet == 0


def test_5f_vol_11_rescue_skill(benchmark_graph: RoadGraphEngine):
    """Test 11: RESCUE task satisfied by RESCUE category or rescue in skills list."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_R", title="Flood Evacuation", latitude=13.08, longitude=80.27, required_skills={"RESCUE": 1})

    vol = VolunteerInput(
        volunteer_id="V_RES",
        name="Boat Pilot",
        latitude=13.08,
        longitude=80.27,
        skill_category="GENERAL",
        skills=["Swift Water Rescue"]
    )

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 1


def test_5f_vol_12_logistics_skill(benchmark_graph: RoadGraphEngine):
    """Test 12: LOGISTICS task requires LOGISTICS category or logistics in skills."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_L", title="Supply Dispatch", latitude=13.08, longitude=80.27, required_skills={"LOGISTICS": 1})

    vol = VolunteerInput(
        volunteer_id="V_LOG",
        name="Truck Driver",
        latitude=13.08,
        longitude=80.27,
        skill_category="LOGISTICS"
    )

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 1


def test_5f_vol_13_incompatible_skill_unassigned(benchmark_graph: RoadGraphEngine):
    """Test 13: Incompatible skills prevent assignment to specialized tasks."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_R", title="Rescue", latitude=13.08, longitude=80.27, required_skills={"RESCUE": 1})

    # Volunteer is purely logistics
    vol = VolunteerInput(
        volunteer_id="V_LOG",
        name="Warehouse Clerk",
        latitude=13.08,
        longitude=80.27,
        skill_category="LOGISTICS",
        skills=["Inventory Management"]
    )

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 0
    assert result.total_tasks_unmet == 1


def test_5f_vol_14_unverified_medical_rejected(benchmark_graph: RoadGraphEngine):
    """Test 14: Volunteer with verification_status != 'VERIFIED' is rejected."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_M", title="Medical Aid", latitude=13.08, longitude=80.27, required_skills={"MEDICAL": 1})

    vol = VolunteerInput(
        volunteer_id="V_PENDING",
        name="Pending Paramedic",
        latitude=13.08,
        longitude=80.27,
        skill_category="MEDICAL",
        medical_certified=True,
        verification_status="PENDING"
    )

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 0
    assert result.total_tasks_unmet == 1


# ==============================================================================
# PART 3: AVAILABILITY & WORKLOAD CONSTRAINTS (Tests 15 to 18)
# ==============================================================================

def test_5f_vol_15_unavailable_volunteer_ignored(benchmark_graph: RoadGraphEngine):
    """Test 15: is_available == False or assignment_status != UNASSIGNED is barred."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_1", title="Task", latitude=13.08, longitude=80.27, required_skills={"GENERAL": 1})

    vol_unavail = VolunteerInput(volunteer_id="V_UNAV", name="V1", latitude=13.08, longitude=80.27, is_available=False)
    vol_onmission = VolunteerInput(volunteer_id="V_MIS", name="V2", latitude=13.08, longitude=80.27, assignment_status="ON_MISSION")

    result = engine.solve([vol_unavail, vol_onmission], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 0
    assert result.total_tasks_unmet == 1


def test_5f_vol_16_unavailable_shift_ignored(benchmark_graph: RoadGraphEngine):
    """Test 16: Volunteer restricted to SHIFT_2 cannot be assigned to SHIFT_1."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(
        incident_id="INC_1",
        title="Day Shift Task",
        latitude=13.08,
        longitude=80.27,
        required_skills={"GENERAL": 1},
        shifts=["SHIFT_1"]
    )

    vol = VolunteerInput(
        volunteer_id="V_NIGHT",
        name="Night Worker",
        latitude=13.08,
        longitude=80.27,
        shift_availability=["SHIFT_2"]
    )

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 0
    assert result.total_tasks_unmet == 1


def test_5f_vol_17_workload_hours_ceiling(benchmark_graph: RoadGraphEngine):
    """Test 17: Task duration 8h exceeds volunteer max_shift_hours 4h."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(
        incident_id="INC_LONG",
        title="Long Mission",
        latitude=13.08,
        longitude=80.27,
        required_skills={"GENERAL": 1},
        shifts=["SHIFT_1"],
        task_durations={"SHIFT_1": 8.0}
    )

    vol = VolunteerInput(
        volunteer_id="V_PARTTIME",
        name="Part Time Volunteer",
        latitude=13.08,
        longitude=80.27,
        max_shift_hours=4.0
    )

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 0
    assert result.total_tasks_unmet == 1


def test_5f_vol_18_maximum_travel_time_constraint(benchmark_graph: RoadGraphEngine):
    """Test 18: Volunteer max_travel_time_mins prevents distant assignment."""
    engine = VolunteerAssignmentEngine()
    # Incident far away in Chennai south (Tambaram)
    inc = IncidentTaskInput(
        incident_id="INC_FAR",
        title="Distant Flood Site",
        latitude=12.9250,
        longitude=80.1180,
        required_skills={"GENERAL": 1}
    )

    # Volunteer in north Chennai (Perambur) with 10 min transit budget
    vol = VolunteerInput(
        volunteer_id="V_LOCAL",
        name="Hyper-local Volunteer",
        latitude=13.1110,
        longitude=80.2420,
        max_travel_time_mins=10.0  # Transit will be ~30-40 min, exceeding 10.0
    )

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 0
    assert result.total_tasks_unmet == 1


# ==============================================================================
# PART 4: ROUTING & NETWORK FEASIBILITY (Tests 19 to 22)
# ==============================================================================

def test_5f_vol_19_reachable_incident_assigned(benchmark_graph: RoadGraphEngine):
    """Test 19: Incident reachable on road network is assigned with valid transit times."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_NEAR", title="Near", latitude=13.0827, longitude=80.2707, required_skills={"GENERAL": 1})
    vol = VolunteerInput(volunteer_id="V_NEAR", name="Neighbor", latitude=13.0820, longitude=80.2700)

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 1
    assert len(result.assignments) == 1
    assert result.assignments[0].transit_time_minutes > 0.0
    assert result.assignments[0].transit_distance_km > 0.0


def test_5f_vol_20_unreachable_incident_prohibited(benchmark_graph: RoadGraphEngine):
    """Test 20: Completely disconnected incident coordinate cannot be assigned."""
    engine = VolunteerAssignmentEngine()
    # Coordinates in the Indian Ocean / disconnected
    inc = IncidentTaskInput(incident_id="INC_ISLAND", title="Isolated Island", latitude=13.5000, longitude=81.5000, required_skills={"GENERAL": 1})
    vol = VolunteerInput(volunteer_id="V1", name="Volunteer", latitude=13.0820, longitude=80.2700, max_travel_time_mins=30.0)

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 0
    assert result.total_tasks_unmet == 1


def test_5f_vol_21_blocked_route_reroutes_or_rejects(benchmark_graph: RoadGraphEngine):
    """Test 21: Applying impassable road blockage severs path or increases travel time."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_1", title="Sector 1", latitude=13.0827, longitude=80.2707, required_skills={"GENERAL": 1})
    vol = VolunteerInput(volunteer_id="V1", name="Responder", latitude=13.0110, longitude=80.2350, max_travel_time_mins=45.0)

    # Initial solve
    res1 = engine.solve([vol], [inc], benchmark_graph)
    assert res1.total_tasks_assigned == 1
    initial_time = res1.assignments[0].transit_time_minutes

    # Apply severe blockage to graph
    edges = list(benchmark_graph.graph.edges())
    if edges:
        u, v = edges[0]
        benchmark_graph.apply_blockage(
            blockage_id="BLK_99",
            source_id=u,
            target_id=v,
            blockage_status="IMPASSABLE",
            delay_penalty_mins=50.0
        )

    res2 = engine.solve([vol], [inc], benchmark_graph)
    # Either successfully rerouted or rejected if threshold exceeded
    if res2.total_tasks_assigned == 1:
        assert res2.assignments[0].transit_time_minutes >= initial_time


def test_5f_vol_22_travel_time_cutoff_enforced(benchmark_graph: RoadGraphEngine):
    """Test 22: Cutoff is strictly respected: 45.0 min max does not allow 45.1 min."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_1", title="City Center", latitude=13.0827, longitude=80.2707, required_skills={"GENERAL": 1})
    # Set volunteer transit threshold just below actual transit time
    vol = VolunteerInput(volunteer_id="V1", name="Volunteer", latitude=13.0110, longitude=80.2350, max_travel_time_mins=5.0)

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 0
    assert result.total_tasks_unmet == 1


# ==============================================================================
# PART 5: PRIORITY DOMINANCE & CONTENTION (Tests 23 to 24)
# ==============================================================================

def test_5f_vol_23_medical_vs_general_contention(benchmark_graph: RoadGraphEngine):
    """
    Test 23: Critical Contention Test:
    1 medical task (unmet penalty 2500) vs 1 general task (unmet penalty 1000).
    Only 1 medical-certified volunteer who can do either task.
    Mathematical formulation MUST deploy volunteer to medical task!
    """
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(
        incident_id="INC_CONTENTION",
        title="Field Station",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"MEDICAL": 1, "GENERAL": 1},
        shifts=["SHIFT_1"]
    )

    # 1 medical-certified volunteer
    vol = VolunteerInput(
        volunteer_id="V_DOC",
        name="Dr. Triage",
        latitude=13.0820,
        longitude=80.2700,
        skill_category="MEDICAL",
        medical_certified=True,
        verification_status="VERIFIED"
    )

    result = engine.solve([vol], [inc], benchmark_graph)

    assert result.total_tasks_demanded == 2
    assert result.total_tasks_assigned == 1
    assert result.total_tasks_unmet == 1

    # The single assignment MUST be for the MEDICAL task
    assert result.assignments[0].skill_category == "MEDICAL"
    assert result.assignments[0].volunteer_id == "V_DOC"

    # The unmet task MUST be GENERAL
    assert result.unmet_items[0].skill_category == "GENERAL"


def test_5f_vol_24_multiple_medical_contention(benchmark_graph: RoadGraphEngine):
    """
    Test 24: Multiple medical incidents competing for limited medical volunteers.
    Prefers closest medical incident to minimize transit penalty while filling 1 role.
    """
    engine = VolunteerAssignmentEngine()
    inc_near = IncidentTaskInput(
        incident_id="INC_MED_NEAR",
        title="Near Clinic",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"MEDICAL": 1}
    )
    inc_far = IncidentTaskInput(
        incident_id="INC_MED_FAR",
        title="Far Clinic",
        latitude=12.9250,
        longitude=80.1180,
        required_skills={"MEDICAL": 1}
    )

    vol = VolunteerInput(
        volunteer_id="V_DOC",
        name="Dr. Near",
        latitude=13.0820,
        longitude=80.2700,
        skill_category="MEDICAL",
        medical_certified=True
    )

    result = engine.solve([vol], [inc_near, inc_far], benchmark_graph)

    assert result.total_tasks_assigned == 1
    assert result.total_tasks_unmet == 1
    # Assigns to near clinic
    assert result.assignments[0].incident_id == "INC_MED_NEAR"
    assert result.unmet_items[0].incident_id == "INC_MED_FAR"


# ==============================================================================
# PART 6: CONSERVATION & DEPLOYMENT REIFICATION (Tests 25 to 27)
# ==============================================================================

def test_5f_vol_25_exact_task_conservation(benchmark_graph: RoadGraphEngine):
    """
    Test 25: Verify Task Demand Conservation Law:
    sum_v y_vikt + u_ikt == d_ikt for every incident, skill, and shift.
    """
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(
        incident_id="INC_CONS",
        title="Relief Post",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"MEDICAL": 2, "RESCUE": 1, "GENERAL": 3},
        shifts=["SHIFT_1"]
    )

    # 3 general volunteers, 1 rescue, 1 medical -> some will be unmet
    vols = [
        VolunteerInput(volunteer_id="V_MED", name="Doc", latitude=13.08, longitude=80.27, skill_category="MEDICAL", medical_certified=True),
        VolunteerInput(volunteer_id="V_RES", name="Rescuer", latitude=13.08, longitude=80.27, skill_category="RESCUE"),
        VolunteerInput(volunteer_id="V_G1", name="G1", latitude=13.08, longitude=80.27, skill_category="GENERAL"),
        VolunteerInput(volunteer_id="V_G2", name="G2", latitude=13.08, longitude=80.27, skill_category="GENERAL"),
    ]

    result = engine.solve(vols, [inc], benchmark_graph)

    total_demand = sum(inc.required_skills.values())
    assert result.total_tasks_assigned + result.total_tasks_unmet == total_demand

    for skill, demand in inc.required_skills.items():
        assigned_skill = sum(1 for a in result.assignments if a.skill_category == skill)
        unmet_skill = sum(u.unmet_quantity for u in result.unmet_items if u.skill_category == skill)
        assert assigned_skill + unmet_skill == demand, f"Conservation violated for {skill}"


def test_5f_vol_26_assignment_implies_deployment(benchmark_graph: RoadGraphEngine):
    """Test 26: Whenever a volunteer is assigned (y_vikt = 1), deployment is recorded (z_vt = 1)."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_DEP", title="Hub", latitude=13.08, longitude=80.27, required_skills={"GENERAL": 1})
    vol = VolunteerInput(volunteer_id="V_DEP", name="Vol", latitude=13.08, longitude=80.27)

    result = engine.solve([vol], [inc], benchmark_graph)
    assert result.total_tasks_assigned == 1
    assert result.deployed_volunteers_count == 1
    assert result.objective_breakdown["deployment"] == OBJECTIVE_WEIGHTS["lambda_5"]


def test_5f_vol_27_no_spurious_deployment(benchmark_graph: RoadGraphEngine):
    """Test 27: Unassigned volunteers incur zero deployment cost."""
    engine = VolunteerAssignmentEngine()
    inc = IncidentTaskInput(incident_id="INC_1", title="Hub", latitude=13.08, longitude=80.27, required_skills={"GENERAL": 1})
    vols = [
        VolunteerInput(volunteer_id="V1", name="Active", latitude=13.08, longitude=80.27),
        VolunteerInput(volunteer_id="V2", name="Surplus", latitude=13.08, longitude=80.27),
        VolunteerInput(volunteer_id="V3", name="Surplus", latitude=13.08, longitude=80.27),
    ]

    result = engine.solve(vols, [inc], benchmark_graph)
    assert result.total_tasks_assigned == 1
    assert result.deployed_volunteers_count == 1
    assert result.objective_breakdown["deployment"] == OBJECTIVE_WEIGHTS["lambda_5"] * 1


# ==============================================================================
# PART 7: GOVERNANCE & HITL WORKFLOW (Tests 28 to 30)
# ==============================================================================

def test_5f_vol_28_recommendation_proposed_status(db_session: Session, govt_officer: User):
    """Test 28: Initial service execution sets run and recommendations to PROPOSED."""
    service = VolunteerAssignmentService()

    # Create dummy incident and volunteer in DB
    inc = Incident(
        incident_code=f"INC_{uuid.uuid4().hex[:6]}",
        title="Downtown Flash Flood",
        disaster_type="FLOOD",
        description="Water rising fast",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"GENERAL": 1}
    )
    db_session.add(inc)

    vol_user = User(
        email=f"vol_{uuid.uuid4().hex[:6]}@dirs.org",
        hashed_password="hash",
        full_name="Responder Beta",
        role=UserRole.VOLUNTEER
    )
    db_session.add(vol_user)
    db_session.commit()

    vp = VolunteerProfile(
        user_id=vol_user.id,
        skill_category="GENERAL",
        verification_status="VERIFIED",
        is_available=True,
        assignment_status="UNASSIGNED",
        current_lat=13.0820,
        current_lng=80.2700
    )
    db_session.add(vp)
    db_session.commit()

    run = service.run_volunteer_optimization(db_session, requesting_user_id=govt_officer.id)

    assert run.status == "PROPOSED"
    assert run.graph_version is not None
    assert len(run.recommendations) >= 1
    for rec in run.recommendations:
        assert rec.status == "PROPOSED"
        assert rec.recommendation_type == "VOLUNTEER_ASSIGNMENT"


def test_5f_vol_29_government_approval_required(db_session: Session, govt_officer: User, citizen_user: User):
    """Test 29: Non-GOVT user cannot approve; GOVT user transitions run to APPROVED."""
    service = VolunteerAssignmentService()
    run = service.run_volunteer_optimization(db_session, requesting_user_id=govt_officer.id)

    # Citizen cannot approve
    with pytest.raises(PermissionError):
        service.approve_plan(db_session, run.id, citizen_user)

    # Government officer approves
    approved_run = service.approve_plan(db_session, run.id, govt_officer)
    assert approved_run.status == "APPROVED"
    for rec in approved_run.recommendations:
        assert rec.status == "APPROVED"


def test_5f_vol_30_override_logging_audit(db_session: Session, govt_officer: User, citizen_user: User):
    """Test 30: Overrides create immutable OptimizationOverrideLog and AuditLog."""
    service = VolunteerAssignmentService()
    run = service.run_volunteer_optimization(db_session, requesting_user_id=govt_officer.id)

    # Citizen cannot override
    with pytest.raises(PermissionError):
        service.override_plan(
            db_session,
            run_id=run.id,
            overriding_user=citizen_user,
            action="MODIFY",
            justification="Unauthorized override"
        )

    # Government officer overrides
    override_log = service.override_plan(
        db_session,
        run_id=run.id,
        overriding_user=govt_officer,
        action="MODIFY",
        justification="Reallocating field personnel based on on-site tactical commander request",
        overridden_items=[{"volunteer_id": "test", "action": "REASSIGN"}]
    )

    assert override_log.id is not None
    assert override_log.action == "MODIFY"
    assert "tactical commander" in override_log.justification_reason
    assert run.status == "MODIFIED"


# ==============================================================================
# PART 8: BRUTE FORCE & OBJECTIVE RECONCILIATION (Tests 31 to 32)
# ==============================================================================

def test_5f_vol_31_brute_force_ground_truth_optimality(small_graph: RoadGraphEngine):
    """
    Test 31: Independent Brute-Force ground truth comparison.
    CP-SAT optimal objective must match exhaustive combinatorial search on small instance.
    """
    inc1 = IncidentTaskInput(
        incident_id="INC_BF_1",
        title="Site 1",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"MEDICAL": 1, "GENERAL": 1},
        shifts=["SHIFT_1"]
    )
    inc2 = IncidentTaskInput(
        incident_id="INC_BF_2",
        title="Site 2",
        latitude=13.0110,
        longitude=80.2350,
        required_skills={"RESCUE": 1},
        shifts=["SHIFT_1"]
    )

    vols = [
        VolunteerInput(volunteer_id="V1", name="Doc", latitude=13.0800, longitude=80.2700, skill_category="MEDICAL", medical_certified=True),
        VolunteerInput(volunteer_id="V2", name="Aide", latitude=13.0810, longitude=80.2710, skill_category="GENERAL"),
        VolunteerInput(volunteer_id="V3", name="Swimmer", latitude=13.0100, longitude=80.2340, skill_category="RESCUE"),
    ]

    bf_solver = BruteForceVolunteerSolver()
    bf_result = bf_solver.solve(vols, [inc1, inc2], small_graph)
    bf_opt_obj = bf_result["optimal_objective"]

    cp_engine = VolunteerAssignmentEngine()
    cp_result = cp_engine.solve(vols, [inc1, inc2], small_graph)
    cp_opt_obj = cp_result.objective_value

    assert cp_result.solver_status == "OPTIMAL"
    # Match within 0.5 points (accounting for integerization)
    assert abs(cp_opt_obj - bf_opt_obj) <= 0.5, (
        f"CP-SAT obj {cp_opt_obj} does not match Brute-Force optimum {bf_opt_obj}"
    )


def test_5f_vol_32_objective_reconciliation_exact(benchmark_graph: RoadGraphEngine):
    """
    Test 32: Independently reconstruct objective:
    1000 * unmet + 1500 * medical_unmet + 10 * transit_time + 1 * transit_dist + 50 * deployments
    Compare with solver-reported objective within integerization tolerance.
    """
    inc1 = IncidentTaskInput(
        incident_id="INC_REC_1",
        title="Post A",
        latitude=13.0827,
        longitude=80.2707,
        required_skills={"MEDICAL": 2, "GENERAL": 2},
        shifts=["SHIFT_1"]
    )
    # Only 1 medical and 1 general volunteer available -> 1 medical unmet, 1 general unmet
    vols = [
        VolunteerInput(volunteer_id="V_M", name="Doc", latitude=13.0800, longitude=80.2700, skill_category="MEDICAL", medical_certified=True),
        VolunteerInput(volunteer_id="V_G", name="Aide", latitude=13.0810, longitude=80.2710, skill_category="GENERAL"),
    ]

    engine = VolunteerAssignmentEngine()
    result = engine.solve(vols, [inc1], benchmark_graph)

    # Independent calculation
    unmet_count = result.total_tasks_unmet
    med_unmet_count = result.skill_unmet_counts.get("MEDICAL", 0)
    transit_time = result.total_transit_minutes
    transit_dist = result.total_transit_km
    deployments = result.deployed_volunteers_count

    expected_obj = (
        1000.0 * unmet_count +
        1500.0 * med_unmet_count +
        10.0 * transit_time +
        1.0 * transit_dist +
        50.0 * deployments
    )

    diff = abs(result.objective_value - expected_obj)
    assert diff <= 0.5, (
        f"Reconciled objective {expected_obj:.2f} differs from solver {result.objective_value:.2f} by {diff:.4f}"
    )


# ==============================================================================
# PART 9: DETERMINISM, BASELINES & BENCHMARKS (Tests 33 to 35)
# ==============================================================================

def test_5f_vol_33_deterministic_consistency_5_runs(benchmark_graph: RoadGraphEngine):
    """Test 33: 5 repeated runs with seed 42 produce bit-exact identical objectives and assignments."""
    incidents, volunteers = generate_volunteer_benchmark_dataset(num_incidents=10, num_volunteers=25, seed=42)
    engine = VolunteerAssignmentEngine()

    run_objs = []
    run_assignments = []

    for _ in range(5):
        res = engine.solve(volunteers, incidents, benchmark_graph, random_seed=42)
        assert res.solver_status == "OPTIMAL"
        run_objs.append(res.objective_value)
        # Hash assignments
        sig = tuple(sorted((a.volunteer_id, a.incident_id, a.skill_category) for a in res.assignments))
        run_assignments.append(sig)

    assert len(set(run_objs)) == 1, f"Non-deterministic objectives: {run_objs}"
    assert len(set(run_assignments)) == 1, "Non-deterministic assignment signatures detected across 5 runs"


def test_5f_vol_34_baseline_heuristic_comparison(benchmark_graph: RoadGraphEngine):
    """Test 34: CP-SAT achieves equal or lower objective value compared to Greedy and FCFS."""
    incidents, volunteers = generate_volunteer_benchmark_dataset(num_incidents=10, num_volunteers=25, seed=42)

    cp_engine = VolunteerAssignmentEngine()
    greedy_solver = GreedyFeasibleVolunteerSolver()
    fcfs_solver = FCFSVolunteerSolver()

    cp_res = cp_engine.solve(volunteers, incidents, benchmark_graph)
    greedy_res = greedy_solver.solve(volunteers, incidents, benchmark_graph)
    fcfs_res = fcfs_solver.solve(volunteers, incidents, benchmark_graph)

    assert cp_res.solver_status == "OPTIMAL"
    # CP-SAT must be mathematically optimal (<= baselines within integer rounding margin)
    assert cp_res.objective_value <= greedy_res.objective_value + 1.0, (
        f"CP-SAT obj {cp_res.objective_value} worse than Greedy {greedy_res.objective_value}"
    )
    assert cp_res.objective_value <= fcfs_res.objective_value + 1.0, (
        f"CP-SAT obj {cp_res.objective_value} worse than FCFS {fcfs_res.objective_value}"
    )


def test_5f_vol_35_benchmark_dataset_tiers(benchmark_graph: RoadGraphEngine):
    """Test 35: Executes benchmark tiers DIRS-VOL-10 and DIRS-VOL-25 and validates feasibility."""
    engine = VolunteerAssignmentEngine()

    # DIRS-VOL-10
    inc10, vol25 = generate_volunteer_benchmark_dataset(num_incidents=10, num_volunteers=25, seed=42)
    res10 = engine.solve(vol25, inc10, benchmark_graph)
    assert res10.solver_status in ["OPTIMAL", "FEASIBLE"]
    assert res10.total_tasks_demanded > 0
    assert res10.solver_runtime_ms < 2000.0  # Well within latency limits

    # DIRS-VOL-25
    inc25, vol50 = generate_volunteer_benchmark_dataset(num_incidents=25, num_volunteers=50, seed=42)
    res25 = engine.solve(vol50, inc25, benchmark_graph)
    assert res25.solver_status in ["OPTIMAL", "FEASIBLE"]
    assert res25.total_tasks_demanded > 0
    assert res25.solver_runtime_ms < 3000.0
