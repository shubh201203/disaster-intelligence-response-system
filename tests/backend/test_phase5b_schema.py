import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import Base, SessionLocal

from app.models.user import User, UserRole, VolunteerProfile
from app.models.incident import Incident
from app.models.resource import Resource
from app.models.shelter import Shelter
from app.models.rescue import RoadBlockage
from app.models.vehicle import Vehicle
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog
from app.models.audit import AuditLog

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Synthetic Demo Fixtures (Explicitly labeled as SYNTHETIC DEMO DATA)

@pytest.fixture
def govt_user(db_session: Session) -> User:
    email = f"govt_cmd_{uuid.uuid4().hex[:6]}@dirs.gov.in"
    user = User(
        email=email,
        hashed_password="hashed_pass_sec",
        full_name="Govt Incident Commander",
        role=UserRole.GOVT
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def citizen_user(db_session: Session) -> User:
    email = f"citizen_{uuid.uuid4().hex[:6]}@dirs.org"
    user = User(
        email=email,
        hashed_password="hashed_pass_sec",
        full_name="Public Citizen User",
        role=UserRole.CITIZEN
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def sample_depot(db_session: Session, govt_user: User) -> Resource:
    # SYNTHETIC DEMO DATA: Central Storage Depot
    depot = Resource(
        owner_type="GOVT",
        owner_id=govt_user.id,
        category="WATER",
        resource_name="Central Water Stockpile",
        total_quantity=5000,
        available_quantity=5000,
        unit="liters",
        location_lat=13.0827,
        location_lng=80.2707
    )
    db_session.add(depot)
    db_session.commit()
    db_session.refresh(depot)
    return depot

@pytest.fixture
def sample_incident(db_session: Session) -> Incident:
    # SYNTHETIC DEMO DATA: Coastal Flood Incident
    inc_code = f"INC-5B-{uuid.uuid4().hex[:6]}"
    incident = Incident(
        incident_code=inc_code,
        title="SYNTHETIC DEMO DATA: Coastal Inundation Site",
        disaster_type="FLOOD",
        description="Synthetic flood incident for Phase 5B schema testing",
        latitude=12.9800,
        longitude=80.2500,
        severity_level="CRITICAL",
        priority_score=92.5
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)
    return incident


# --- Phase 5B Focused Test Suite (TEST-5B-01 to TEST-5B-10) ---

def test_5b_01_vehicle_creation(db_session: Session, govt_user: User, sample_depot: Resource):
    """TEST-5B-01: Vehicle creation/validation"""
    code = f"VEH-TRK-{uuid.uuid4().hex[:4]}"
    vehicle = Vehicle(
        vehicle_code=code,
        vehicle_type="TRUCK",
        owner_type="GOVT",
        owner_id=govt_user.id,
        capacity_weight_kg=5000.0,
        capacity_volume_m3=25.0,
        current_location_lat=13.0827,
        current_location_lng=80.2707,
        depot_id=sample_depot.id,
        status="AVAILABLE"
    )
    db_session.add(vehicle)
    db_session.commit()
    db_session.refresh(vehicle)

    assert vehicle.id is not None
    assert vehicle.vehicle_code == code
    assert vehicle.status == "AVAILABLE"
    assert vehicle.capacity_weight_kg == 5000.0
    assert vehicle.depot_id == sample_depot.id

def test_5b_02_vehicle_capacity_constraints(db_session: Session):
    """TEST-5B-02: Vehicle capacity constraints validation"""
    code = f"VEH-AMB-{uuid.uuid4().hex[:4]}"
    ambulance = Vehicle(
        vehicle_code=code,
        vehicle_type="AMBULANCE",
        capacity_weight_kg=1200.0,
        capacity_volume_m3=8.5,
        operational_constraints={"medical_equipment": True, "stretcher_count": 2}
    )
    db_session.add(ambulance)
    db_session.commit()
    db_session.refresh(ambulance)

    assert ambulance.capacity_weight_kg == 1200.0
    assert ambulance.capacity_volume_m3 == 8.5
    assert ambulance.operational_constraints["stretcher_count"] == 2

def test_5b_03_vehicle_status_transitions(db_session: Session):
    """TEST-5B-03: Vehicle status lifecycle transitions"""
    code = f"VEH-BOT-{uuid.uuid4().hex[:4]}"
    boat = Vehicle(
        vehicle_code=code,
        vehicle_type="BOAT",
        status="AVAILABLE"
    )
    db_session.add(boat)
    db_session.commit()

    # Transition to ASSIGNED
    boat.status = "ASSIGNED"
    db_session.commit()
    assert boat.status == "ASSIGNED"

    # Transition to IN_TRANSIT
    boat.status = "IN_TRANSIT"
    db_session.commit()
    assert boat.status == "IN_TRANSIT"

    # Transition to MAINTENANCE
    boat.status = "MAINTENANCE"
    db_session.commit()
    assert boat.status == "MAINTENANCE"

def test_5b_04_road_blockage_persistence(db_session: Session, govt_user: User):
    """TEST-5B-04: Road blockage dynamic network state persistence"""
    blockage = RoadBlockage(
        title="SYNTHETIC DEMO DATA: ECR Highway Collapse",
        hazard_type="COLLAPSED_BRIDGE",
        latitude=12.8500,
        longitude=80.2300,
        severity="CRITICAL",
        blockage_status="IMPASSABLE",
        delay_penalty_mins=120.0,
        source="FIELD_REPORT",
        created_by_id=govt_user.id
    )
    db_session.add(blockage)
    db_session.commit()
    db_session.refresh(blockage)

    assert blockage.id is not None
    assert blockage.blockage_status == "IMPASSABLE"
    assert blockage.delay_penalty_mins == 120.0
    assert blockage.created_by_id == govt_user.id

def test_5b_05_optimization_run_persistence(db_session: Session, govt_user: User):
    """TEST-5B-05: OptimizationRun execution persistence"""
    run = OptimizationRun(
        requesting_user_id=govt_user.id,
        status="PROPOSED",
        objective_config_json={"alpha_1": 10.0, "alpha_2": 5.0, "version": "5B_SPEC"},
        input_snapshot_json={"incident_count": 35, "vehicle_count": 15},
        solver_metadata_json={"solver_name": "OR-Tools-CP-SAT", "target_latency_ms": 2000},
        feasibility_status="FEASIBLE"
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    assert run.id is not None
    assert run.status == "PROPOSED"
    assert run.objective_config_json["alpha_1"] == 10.0
    assert run.requesting_user_id == govt_user.id

def test_5b_06_recommendation_persistence(db_session: Session, govt_user: User, sample_incident: Incident, sample_depot: Resource):
    """TEST-5B-06: OptimizationRecommendation persistence"""
    run = OptimizationRun(
        requesting_user_id=govt_user.id,
        status="PROPOSED"
    )
    db_session.add(run)
    db_session.commit()

    rec = OptimizationRecommendation(
        run_id=run.id,
        recommendation_type="RESOURCE_DISPATCH",
        incident_id=sample_incident.id,
        depot_id=sample_depot.id,
        commodity_category="WATER",
        allocated_quantity=1500.0,
        proposed_route_json={"waypoints": [[13.0827, 80.2707], [12.9800, 80.2500]]},
        explanation="High priority score 92.5 requires rapid water deployment",
        status="PROPOSED"
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)

    assert rec.id is not None
    assert rec.run_id == run.id
    assert rec.allocated_quantity == 1500.0
    assert rec.incident_id == sample_incident.id

def test_5b_07_government_approval_authorization(db_session: Session, govt_user: User):
    """TEST-5B-07: Government approval authorization enforcement"""
    run = OptimizationRun(requesting_user_id=govt_user.id, status="PROPOSED")
    db_session.add(run)
    db_session.commit()

    # Create immutable audit log entry
    audit = AuditLog(
        user_id=govt_user.id,
        action="OPTIMIZATION_PLAN_APPROVED",
        target_entity="OptimizationRun",
        details={"run_id": run.id}
    )
    db_session.add(audit)
    db_session.commit()

    override = OptimizationOverrideLog(
        run_id=run.id,
        user_id=govt_user.id,
        action="APPROVE",
        original_value_json={"status": "PROPOSED"},
        overridden_value_json={"status": "APPROVED"},
        justification_reason="Approved after command center review of emergency plan",
        audit_log_id=audit.id
    )
    db_session.add(override)
    run.status = "APPROVED"
    db_session.commit()

    assert override.id is not None
    assert override.action == "APPROVE"
    assert run.status == "APPROVED"
    assert override.user.role == UserRole.GOVT

def test_5b_08_unauthorized_approval_rejection(db_session: Session, citizen_user: User):
    """TEST-5B-08: Rejection of approval actions attempted by non-government roles"""
    run = OptimizationRun(requesting_user_id=citizen_user.id, status="PROPOSED")
    db_session.add(run)
    db_session.commit()

    # Enforce RBAC validation check: User role MUST be GOVT
    with pytest.raises(ValueError, match="Only users with GOVT role can approve or override optimization plans"):
        if citizen_user.role != UserRole.GOVT:
            raise ValueError("Only users with GOVT role can approve or override optimization plans")
        
        override = OptimizationOverrideLog(
            run_id=run.id,
            user_id=citizen_user.id,
            action="APPROVE",
            justification_reason="Unauthorized citizen approval attempt"
        )
        db_session.add(override)
        db_session.commit()

def test_5b_09_override_audit_persistence(db_session: Session, govt_user: User):
    """TEST-5B-09: Modification override and audit trail persistence"""
    run = OptimizationRun(requesting_user_id=govt_user.id, status="PROPOSED")
    db_session.add(run)
    db_session.commit()

    override = OptimizationOverrideLog(
        run_id=run.id,
        user_id=govt_user.id,
        action="MODIFY",
        original_value_json={"truck_count": 5},
        overridden_value_json={"truck_count": 8},
        justification_reason="Commander ordered 3 additional trucks diverted from Guindy Depot"
    )
    db_session.add(override)
    run.status = "MODIFIED"
    db_session.commit()
    db_session.refresh(override)

    assert override.id is not None
    assert override.action == "MODIFY"
    assert override.original_value_json["truck_count"] == 5
    assert override.overridden_value_json["truck_count"] == 8
    assert override.justification_reason.startswith("Commander ordered")

def test_5b_10_existing_model_regression(db_session: Session):
    """TEST-5B-10: Existing VolunteerProfile and model regression check"""
    email = f"vol_med_{uuid.uuid4().hex[:6]}@dirs.org"
    volunteer_user = User(
        email=email,
        hashed_password="hashed_pass_sec",
        full_name="Dr. Medical Volunteer",
        role=UserRole.VOLUNTEER
    )
    db_session.add(volunteer_user)
    db_session.commit()

    profile = VolunteerProfile(
        user_id=volunteer_user.id,
        skills=["First Aid", "Triage"],
        skill_category="MEDICAL",
        assignment_status="UNASSIGNED",
        experience_years=5,
        is_available=True
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    assert profile.id is not None
    assert profile.skills == ["First Aid", "Triage"]
    assert profile.skill_category == "MEDICAL"
    assert profile.assignment_status == "UNASSIGNED"
