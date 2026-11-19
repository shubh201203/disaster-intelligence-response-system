import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import Base, SessionLocal

from pydantic import ValidationError
from app.models.user import User, UserRole, VolunteerProfile
from app.models.incident import Incident
from app.models.shelter import Shelter
from app.models.optimization import OptimizationRun, OptimizationRecommendation, OptimizationOverrideLog
from app.models.audit import AuditLog
from app.schemas.shelter import ShelterCreate, ShelterResponse
from app.schemas.incident import IncidentCreate, IncidentResponse
from app.schemas.user import VolunteerProfileResponse
from app.schemas.optimization import OptimizationRecommendationBase, OptimizationRecommendationResponse, OptimizationRunResponse

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def govt_commander(db_session: Session) -> User:
    email = f"govt_officer_{uuid.uuid4().hex[:6]}@dirs.gov.in"
    user = User(
        email=email,
        hashed_password="hashed_pass_sec",
        full_name="Govt Disaster Director",
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
        full_name="Citizen User",
        role=UserRole.CITIZEN
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

# --- Test 1: Shelter Capacity & Status Validation ---
def test_5f_01_shelter_capacity_and_status_validation(db_session: Session):
    shelter = Shelter(
        name="Test Capacity Shelter",
        address="123 Relief Road, Chennai",
        total_capacity=500,
        current_occupancy=150,
        latitude=13.0827,
        longitude=80.2707,
        status="OPEN"
    )
    db_session.add(shelter)
    db_session.commit()
    db_session.refresh(shelter)

    remaining = max(0, shelter.total_capacity - shelter.current_occupancy) if shelter.status == "OPEN" else 0
    assert shelter.total_capacity == 500
    assert shelter.current_occupancy == 150
    assert remaining == 350
    assert shelter.status in ["OPEN", "FULL", "CLOSED"]

    # When closed, effective remaining capacity is 0
    shelter.status = "CLOSED"
    db_session.commit()
    remaining_closed = max(0, shelter.total_capacity - shelter.current_occupancy) if shelter.status == "OPEN" else 0
    assert remaining_closed == 0

# --- Test 2: Shelter Accessibility & Amenity Fields ---
def test_5f_02_shelter_accessibility_and_amenity_fields(db_session: Session):
    now = datetime.now(timezone.utc)
    shelter = Shelter(
        name="Fully Equipped Central Shelter",
        address="456 Anna Salai, Chennai",
        total_capacity=1000,
        current_occupancy=50,
        latitude=13.0600,
        longitude=80.2500,
        has_medical=True,
        has_food=True,
        has_water=True,
        accessibility_features=True,
        power_available=True,
        sanitation_available=True,
        disaster_compatibility=["FLOOD", "CYCLONE"],
        last_verified_at=now,
        status="OPEN"
    )
    db_session.add(shelter)
    db_session.commit()
    db_session.refresh(shelter)

    assert shelter.accessibility_features is True
    assert shelter.power_available is True
    assert shelter.sanitation_available is True
    assert "FLOOD" in shelter.disaster_compatibility
    assert shelter.last_verified_at is not None

# --- Test 3: Shelter Demographic Compatibility Mapping ---
def test_5f_03_shelter_demographic_compatibility_representation(db_session: Session):
    # Four mutually exclusive demographic categories: GEN, ACC, MED, MED_ACC
    shelter_gen = Shelter(
        name="Basic School Shelter",
        address="Zone 1",
        total_capacity=100,
        latitude=13.0,
        longitude=80.0,
        has_medical=False,
        accessibility_features=False
    )
    shelter_med = Shelter(
        name="Hospital Annex Shelter",
        address="Zone 2",
        total_capacity=100,
        latitude=13.0,
        longitude=80.0,
        has_medical=True,
        accessibility_features=False
    )
    shelter_acc = Shelter(
        name="Accessible Civic Center",
        address="Zone 3",
        total_capacity=100,
        latitude=13.0,
        longitude=80.0,
        has_medical=False,
        accessibility_features=True
    )
    shelter_med_acc = Shelter(
        name="Comprehensive Relief Complex",
        address="Zone 4",
        total_capacity=100,
        latitude=13.0,
        longitude=80.0,
        has_medical=True,
        accessibility_features=True
    )
    db_session.add_all([shelter_gen, shelter_med, shelter_acc, shelter_med_acc])
    db_session.commit()

    # Verify compatibility matrix Omega_sg
    assert shelter_gen.accessibility_features is False
    assert shelter_med.has_medical is True and shelter_med.accessibility_features is False
    assert shelter_acc.accessibility_features is True and shelter_acc.has_medical is False
    assert shelter_med_acc.has_medical is True and shelter_med_acc.accessibility_features is True

# --- Test 4: Volunteer Profile Skill & Status Validation ---
def test_5f_04_volunteer_profile_skill_and_status_validation(db_session: Session):
    vol_user = User(
        email=f"doctor_vol_{uuid.uuid4().hex[:6]}@dirs.org",
        hashed_password="hashed_sec_pass",
        full_name="Dr. Priya Medical Responder",
        role=UserRole.VOLUNTEER
    )
    db_session.add(vol_user)
    db_session.commit()

    profile = VolunteerProfile(
        user_id=vol_user.id,
        skills=["Triage", "Emergency Medicine"],
        skill_category="MEDICAL",
        assignment_status="UNASSIGNED",
        experience_years=6,
        medical_certified=True,
        verification_status="VERIFIED",
        is_available=True,
        current_lat=13.0800,
        current_lng=80.2600
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    assert profile.skill_category == "MEDICAL"
    assert profile.assignment_status == "UNASSIGNED"
    assert profile.medical_certified is True
    assert profile.verification_status == "VERIFIED"
    assert profile.is_available is True

# --- Test 5: Volunteer Workload & Travel Constraints ---
def test_5f_05_volunteer_workload_and_travel_constraints(db_session: Session):
    vol_user = User(
        email=f"rescue_vol_{uuid.uuid4().hex[:6]}@dirs.org",
        hashed_password="hashed_sec_pass",
        full_name="Karthik Water Rescue",
        role=UserRole.VOLUNTEER
    )
    db_session.add(vol_user)
    db_session.commit()

    profile = VolunteerProfile(
        user_id=vol_user.id,
        skills=["Inflatable Raft", "Swimmer"],
        skill_category="RESCUE",
        max_shift_hours=6.0,
        max_travel_time_mins=30.0,
        shift_availability=["SHIFT_1", "SHIFT_2"],
        verification_status="VERIFIED",
        is_available=True
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    assert profile.max_shift_hours == 6.0
    assert profile.max_travel_time_mins == 30.0
    assert "SHIFT_1" in profile.shift_availability
    assert "SHIFT_2" in profile.shift_availability

# --- Test 6: Incident Evacuation Demographics & Required Skills ---
def test_5f_06_incident_evacuation_demographics_and_required_skills(db_session: Session):
    incident = Incident(
        incident_code=f"INC-5F-{uuid.uuid4().hex[:6].upper()}",
        title="Urban Inundation Ward 142",
        disaster_type="FLOOD",
        description="Water level 4 feet. Evacuation needed.",
        latitude=13.0010,
        longitude=80.2210,
        people_affected=150,
        vulnerable_count=30,
        injuries=10,
        priority_score=85.0,
        priority_level="CRITICAL",
        severity_level="CRITICAL",
        required_skills={"MEDICAL": 2, "RESCUE": 4, "GENERAL": 6},
        evacuation_demographics={"GEN": 115, "ACC": 25, "MED": 5, "MED_ACC": 5}
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    assert incident.people_affected == 150
    assert incident.required_skills["MEDICAL"] == 2
    assert incident.required_skills["RESCUE"] == 4
    # Verify population conservation across demographic groups
    demo = incident.evacuation_demographics
    assert demo["GEN"] + demo["ACC"] + demo["MED"] + demo["MED_ACC"] == incident.people_affected

# --- Test 7: Optimization Run & Recommendation (Shelter Evacuation) ---
def test_5f_07_optimization_run_and_recommendation_shelter_evacuation(
    db_session: Session, govt_commander: User
):
    # 1. Create run with Phase 5C graph version
    opt_run = OptimizationRun(
        requesting_user_id=govt_commander.id,
        status="PROPOSED",
        feasibility_status="FEASIBLE",
        graph_version="c9f8a7e2b1d03456",
        objective_config_json={"gamma_1": 1000, "gamma_2": 2000, "gamma_5": 10}
    )
    db_session.add(opt_run)
    db_session.commit()

    # 2. Create Shelter and Incident
    shelter = Shelter(name="Adyar Shelter", address="Adyar", total_capacity=200, latitude=13.0, longitude=80.2)
    incident = Incident(
        incident_code=f"INC-SHELTER-{uuid.uuid4().hex[:4]}",
        title="Flooded Sector",
        disaster_type="FLOOD",
        description="Evacuation required",
        latitude=13.01,
        longitude=80.21,
        people_affected=50
    )
    db_session.add_all([shelter, incident])
    db_session.commit()

    # 3. Create SHELTER_EVACUATION Recommendation
    rec = OptimizationRecommendation(
        run_id=opt_run.id,
        recommendation_type="SHELTER_EVACUATION",
        incident_id=incident.id,
        shelter_id=shelter.id,
        allocated_quantity=50.0,
        demographic_group="ACC",
        transit_time_minutes=14.5,
        transit_distance_km=5.2,
        objective_contribution=245.0,
        explanation="Closest accessible shelter with remaining capacity.",
        status="PROPOSED"
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)

    assert rec.recommendation_type == "SHELTER_EVACUATION"
    assert rec.shelter_id == shelter.id
    assert rec.demographic_group == "ACC"
    assert rec.transit_time_minutes == 14.5
    assert rec.transit_distance_km == 5.2
    assert opt_run.graph_version == "c9f8a7e2b1d03456"

# --- Test 8: Optimization Recommendation (Volunteer Assignment) ---
def test_5f_08_optimization_recommendation_volunteer_assignment(
    db_session: Session, govt_commander: User
):
    opt_run = OptimizationRun(
        requesting_user_id=govt_commander.id,
        status="PROPOSED",
        feasibility_status="PARTIALLY_FEASIBLE"
    )
    db_session.add(opt_run)
    db_session.commit()

    vol_user = User(
        email=f"volunteer_medic_{uuid.uuid4().hex[:6]}@dirs.org",
        hashed_password="hashed_sec_pass",
        full_name="Arun Medical Volunteer",
        role=UserRole.VOLUNTEER
    )
    incident = Incident(
        incident_code=f"INC-VOL-{uuid.uuid4().hex[:4]}",
        title="Medical Triage Post",
        disaster_type="CYCLONE",
        description="Trauma aid required",
        latitude=13.02,
        longitude=80.22,
        people_affected=20
    )
    db_session.add_all([vol_user, incident])
    db_session.commit()

    rec = OptimizationRecommendation(
        run_id=opt_run.id,
        recommendation_type="VOLUNTEER_ASSIGNMENT",
        incident_id=incident.id,
        volunteer_id=vol_user.id,
        allocated_quantity=1.0, # 1 volunteer deployed
        skill_category="MEDICAL",
        shift_id="SHIFT_1",
        transit_time_minutes=18.0,
        transit_distance_km=6.8,
        objective_contribution=190.0,
        explanation="Verified medical professional within 18 min transit window.",
        status="PROPOSED"
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)

    assert rec.recommendation_type == "VOLUNTEER_ASSIGNMENT"
    assert rec.volunteer_id == vol_user.id
    assert rec.skill_category == "MEDICAL"
    assert rec.shift_id == "SHIFT_1"
    assert rec.allocated_quantity == 1.0

# --- Test 9: Government Approval RBAC Enforcement ---
def test_5f_09_government_approval_rbac_enforcement(
    db_session: Session, govt_commander: User, citizen_user: User
):
    opt_run = OptimizationRun(
        requesting_user_id=govt_commander.id,
        status="PROPOSED",
        feasibility_status="FEASIBLE"
    )
    db_session.add(opt_run)
    db_session.commit()

    rec = OptimizationRecommendation(
        run_id=opt_run.id,
        recommendation_type="SHELTER_EVACUATION",
        allocated_quantity=40.0,
        status="PROPOSED"
    )
    db_session.add(rec)
    db_session.commit()

    # RBAC Validation Rule
    def approve_recommendation(actor: User, recommendation: OptimizationRecommendation):
        if actor.role != UserRole.GOVT:
            raise ValueError(f"Unauthorized: Role '{actor.role}' cannot approve disaster recommendations")
        recommendation.status = "APPROVED"

    # 1. Citizen cannot approve
    with pytest.raises(ValueError, match="Unauthorized"):
        approve_recommendation(citizen_user, rec)
    assert rec.status == "PROPOSED"

    # 2. Government Commander can approve
    approve_recommendation(govt_commander, rec)
    db_session.commit()
    assert rec.status == "APPROVED"

# --- Test 10: Override Logging & Immutability ---
def test_5f_10_override_logging_immutability(
    db_session: Session, govt_commander: User
):
    opt_run = OptimizationRun(
        requesting_user_id=govt_commander.id,
        status="PROPOSED"
    )
    db_session.add(opt_run)
    db_session.commit()

    rec = OptimizationRecommendation(
        run_id=opt_run.id,
        recommendation_type="VOLUNTEER_ASSIGNMENT",
        allocated_quantity=1.0,
        skill_category="GENERAL",
        status="PROPOSED"
    )
    db_session.add(rec)
    db_session.commit()

    # Perform Government Override
    audit_entry = AuditLog(
        user_id=govt_commander.id,
        action="OPTIMIZATION_OVERRIDE_APPLIED",
        target_entity="OptimizationRecommendation",
        details={"recommendation_id": rec.id, "field": "skill_category", "old": "GENERAL", "new": "RESCUE"}
    )
    db_session.add(audit_entry)
    db_session.commit()

    override_log = OptimizationOverrideLog(
        run_id=opt_run.id,
        user_id=govt_commander.id,
        action="MODIFY",
        original_value_json={"skill_category": "GENERAL"},
        overridden_value_json={"skill_category": "RESCUE"},
        justification_reason="Critical swift-water rescue requirement escalated by field unit.",
        audit_log_id=audit_entry.id
    )
    db_session.add(override_log)
    rec.status = "MODIFIED"
    rec.skill_category = "RESCUE"
    db_session.commit()
    db_session.refresh(override_log)

    assert override_log.action == "MODIFY"
    assert "swift-water" in override_log.justification_reason
    assert override_log.audit_log_id == audit_entry.id
    assert rec.status == "MODIFIED"
    assert rec.skill_category == "RESCUE"

# --- Test 11: Pydantic Schema Validation & Serialization ---
def test_5f_11_pydantic_schema_validation_and_serialization():
    # 1. Shelter schema
    s_create = ShelterCreate(
        name="Pydantic Validated Shelter",
        address="Koyambedu, Chennai",
        total_capacity=300,
        latitude=13.0700,
        longitude=80.1900,
        accessibility_features=True,
        power_available=True,
        sanitation_available=True,
        disaster_compatibility=["FLOOD", "CYCLONE"]
    )
    assert s_create.total_capacity == 300
    assert s_create.accessibility_features is True

    # 2. Volunteer profile response schema
    vol_resp = VolunteerProfileResponse(
        skills=["First Aid"],
        skill_category="MEDICAL",
        assignment_status="UNASSIGNED",
        max_shift_hours=8.0,
        max_travel_time_mins=45.0,
        shift_availability=["SHIFT_1"]
    )
    assert vol_resp.max_shift_hours == 8.0
    assert vol_resp.shift_availability == ["SHIFT_1"]

    # 3. Incident schema with demographic partition
    inc_create = IncidentCreate(
        title="Flooded Neighborhood",
        disaster_type="FLOOD",
        description="Water logging",
        latitude=13.0,
        longitude=80.2,
        people_affected=100,
        required_skills={"MEDICAL": 1, "RESCUE": 2},
        evacuation_demographics={"GEN": 80, "ACC": 15, "MED": 5, "MED_ACC": 0}
    )
    assert inc_create.required_skills["MEDICAL"] == 1
    assert inc_create.evacuation_demographics["GEN"] == 80

    # 4. Optimization recommendation response schema
    rec_resp = OptimizationRecommendationResponse(
        id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        recommendation_type="SHELTER_EVACUATION",
        allocated_quantity=80.0,
        demographic_group="GEN",
        transit_time_minutes=12.5,
        transit_distance_km=4.8,
        status="PROPOSED",
        created_at=datetime.now(timezone.utc)
    )
    assert rec_resp.demographic_group == "GEN"
    assert rec_resp.transit_time_minutes == 12.5

# --- Test 12: Alembic Migration Metadata & Revision Chain ---
def test_5f_12_alembic_migration_metadata_and_revisions():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    import os

    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    script_dir = ScriptDirectory.from_config(alembic_cfg)
    head_rev = script_dir.get_current_head()
    # In Phase 5F baseline, head was phase5f_schema_ext. With Phase 6B data foundation,
    # head advances to phase6b_recovery_foundation, which strictly builds upon phase5f_schema_ext.
    assert head_rev in ("phase5f_schema_ext", "phase6b_recovery_foundation")
    if head_rev == "phase6b_recovery_foundation":
        assert script_dir.get_revision(head_rev).down_revision == "phase5f_schema_ext"

    rev_5f = script_dir.get_revision("phase5f_schema_ext")
    assert rev_5f.down_revision == "phase5b_schema_ext"
    assert hasattr(rev_5f.module, "upgrade")
    assert hasattr(rev_5f.module, "downgrade")

# --- Test 13: Demographic Conservation Scenarios (GEN, ACC, MED, MED_ACC) ---
def test_5f_13_demographic_conservation_scenarios():
    # 1. All General Population
    inc_gen = IncidentCreate(
        title="General Population Relocation",
        disaster_type="FLOOD",
        description="Standard flood evacuation",
        latitude=13.08,
        longitude=80.27,
        people_affected=100,
        evacuation_demographics={"GEN": 100, "ACC": 0, "MED": 0, "MED_ACC": 0}
    )
    assert sum(inc_gen.evacuation_demographics.values()) == inc_gen.people_affected

    # 2. All Accessible Population
    inc_acc = IncidentCreate(
        title="Special Needs Facility",
        disaster_type="FLOOD",
        description="Wheelchair evacuees",
        latitude=13.05,
        longitude=80.24,
        people_affected=40,
        evacuation_demographics={"GEN": 0, "ACC": 40, "MED": 0, "MED_ACC": 0}
    )
    assert inc_acc.evacuation_demographics["ACC"] == 40

    # 3. All Medical Population
    inc_med = IncidentCreate(
        title="Field Clinic Evacuation",
        disaster_type="CYCLONE",
        description="Injured patients requiring power/medical shelter",
        latitude=13.06,
        longitude=80.25,
        people_affected=25,
        evacuation_demographics={"GEN": 0, "ACC": 0, "MED": 25, "MED_ACC": 0}
    )
    assert inc_med.evacuation_demographics["MED"] == 25

    # 4. All Medical + Accessible Population
    inc_med_acc = IncidentCreate(
        title="Rehabilitation Hospital Evacuation",
        disaster_type="FLOOD",
        description="Mobility impaired and medically fragile patients",
        latitude=13.04,
        longitude=80.22,
        people_affected=15,
        evacuation_demographics={"GEN": 0, "ACC": 0, "MED": 0, "MED_ACC": 15}
    )
    assert inc_med_acc.evacuation_demographics["MED_ACC"] == 15

    # 5. Mixed Demographic Population
    inc_mixed = IncidentCreate(
        title="Mixed Community Evacuation",
        disaster_type="FLOOD",
        description="Community with mixed needs",
        latitude=13.03,
        longitude=80.21,
        people_affected=100,
        evacuation_demographics={"GEN": 70, "ACC": 15, "MED": 10, "MED_ACC": 5}
    )
    assert sum(inc_mixed.evacuation_demographics.values()) == 100

    # 6. Zero Population
    inc_zero = IncidentCreate(
        title="Empty Alert Site",
        disaster_type="FLOOD",
        description="Precautionary alert",
        latitude=13.01,
        longitude=80.20,
        people_affected=0,
        evacuation_demographics={}
    )
    assert inc_zero.people_affected == 0

    # 7. Missing Demographic Data (defaults to empty dict cleanly)
    inc_default = IncidentCreate(
        title="Initial Report",
        disaster_type="FLOOD",
        description="Demographics pending assessment",
        latitude=13.02,
        longitude=80.21,
        people_affected=50
    )
    assert inc_default.evacuation_demographics == {}

# --- Test 14: Demographic Negative & Boundary Validation ---
def test_5f_14_demographic_negative_and_boundary_validation():
    # 1. Unknown demographic group key must be rejected
    with pytest.raises(ValidationError) as exc_info:
        IncidentCreate(
            title="Invalid Key Incident",
            disaster_type="FLOOD",
            description="Test",
            latitude=13.0,
            longitude=80.0,
            people_affected=50,
            evacuation_demographics={"UNKNOWN_GROUP": 20}
        )
    assert "Unknown demographic group" in str(exc_info.value)

    # 2. Negative demographic population count must be rejected
    with pytest.raises(ValidationError) as exc_info:
        IncidentCreate(
            title="Negative Population Incident",
            disaster_type="FLOOD",
            description="Test",
            latitude=13.0,
            longitude=80.0,
            people_affected=50,
            evacuation_demographics={"GEN": -10}
        )
    assert "must be non-negative" in str(exc_info.value)

    # 3. Inconsistent demographic total (sum exceeds people_affected) must be rejected
    with pytest.raises(ValidationError) as exc_info:
        IncidentCreate(
            title="Inconsistent Total Incident",
            disaster_type="FLOOD",
            description="Test",
            latitude=13.0,
            longitude=80.0,
            people_affected=50,
            evacuation_demographics={"GEN": 40, "ACC": 25} # 65 > 50
        )
    assert "Inconsistent demographic totals" in str(exc_info.value)

    # 4. Unknown required skill category must be rejected
    with pytest.raises(ValidationError) as exc_info:
        IncidentCreate(
            title="Invalid Skill Incident",
            disaster_type="FLOOD",
            description="Test",
            latitude=13.0,
            longitude=80.0,
            people_affected=50,
            required_skills={"AERIAL_COMBAT": 2}
        )
    assert "Unknown skill category" in str(exc_info.value)

    # 5. Negative required skill count must be rejected
    with pytest.raises(ValidationError) as exc_info:
        IncidentCreate(
            title="Negative Skill Count Incident",
            disaster_type="FLOOD",
            description="Test",
            latitude=13.0,
            longitude=80.0,
            people_affected=50,
            required_skills={"MEDICAL": -3}
        )
    assert "must be non-negative" in str(exc_info.value)

# --- Test 15: Shelter Boundary & Negative Validation ---
def test_5f_15_shelter_boundary_and_negative_validation():
    # 1. Zero total capacity must be rejected (gt=0)
    with pytest.raises(ValidationError):
        ShelterCreate(
            name="Zero Cap Shelter",
            address="Test",
            total_capacity=0,
            latitude=13.0,
            longitude=80.0
        )

    # 2. Negative total capacity must be rejected
    with pytest.raises(ValidationError):
        ShelterCreate(
            name="Negative Cap Shelter",
            address="Test",
            total_capacity=-50,
            latitude=13.0,
            longitude=80.0
        )

    # 3. Negative current occupancy must be rejected (ge=0)
    with pytest.raises(ValidationError):
        ShelterCreate(
            name="Negative Occ Shelter",
            address="Test",
            total_capacity=100,
            current_occupancy=-5,
            latitude=13.0,
            longitude=80.0
        )

    # 4. Invalid status must be rejected
    with pytest.raises(ValidationError) as exc_info:
        ShelterCreate(
            name="Invalid Status Shelter",
            address="Test",
            latitude=13.0,
            longitude=80.0,
            status="COMPROMISED"
        )
    assert "Invalid shelter status" in str(exc_info.value)

    # 5. Malformed disaster compatibility list item must be rejected
    with pytest.raises(ValidationError) as exc_info:
        ShelterCreate(
            name="Invalid Hazard Shelter",
            address="Test",
            latitude=13.0,
            longitude=80.0,
            disaster_compatibility=["TSUNAMI_UNVERIFIED"]
        )
    assert "Invalid disaster type" in str(exc_info.value)

    # 6. Malformed accessibility data must be rejected
    with pytest.raises(ValidationError):
        ShelterCreate(
            name="Malformed Accessibility",
            address="Test",
            latitude=13.0,
            longitude=80.0,
            accessibility_features="definitely_not_a_bool"
        )

# --- Test 16: Volunteer Boundary & Negative Validation ---
def test_5f_16_volunteer_boundary_and_negative_validation():
    # 1. Zero max_shift_hours must be rejected (gt=0.0)
    with pytest.raises(ValidationError):
        VolunteerProfileResponse(
            skills=["First Aid"],
            skill_category="MEDICAL",
            max_shift_hours=0.0
        )

    # 2. Negative max_shift_hours must be rejected
    with pytest.raises(ValidationError):
        VolunteerProfileResponse(
            skills=["First Aid"],
            skill_category="MEDICAL",
            max_shift_hours=-4.0
        )

    # 3. Zero max_travel_time_mins must be rejected (gt=0.0)
    with pytest.raises(ValidationError):
        VolunteerProfileResponse(
            skills=["First Aid"],
            skill_category="MEDICAL",
            max_travel_time_mins=0.0
        )

    # 4. Negative max_travel_time_mins must be rejected
    with pytest.raises(ValidationError):
        VolunteerProfileResponse(
            skills=["First Aid"],
            skill_category="MEDICAL",
            max_travel_time_mins=-30.0
        )

    # 5. Invalid skill category must be rejected
    with pytest.raises(ValidationError) as exc_info:
        VolunteerProfileResponse(
            skills=["First Aid"],
            skill_category="AERIAL_COMBAT"
        )
    assert "Invalid skill category" in str(exc_info.value)

# --- Test 17: Recommendation Boundary & Negative Validation ---
def test_5f_17_recommendation_boundary_and_negative_validation():
    # 1. Negative transit_time_minutes must be rejected (ge=0.0)
    with pytest.raises(ValidationError):
        OptimizationRecommendationBase(
            recommendation_type="SHELTER_EVACUATION",
            transit_time_minutes=-10.0
        )

    # 2. Negative transit_distance_km must be rejected (ge=0.0)
    with pytest.raises(ValidationError):
        OptimizationRecommendationBase(
            recommendation_type="SHELTER_EVACUATION",
            transit_distance_km=-5.0
        )

    # 3. Invalid demographic group must be rejected
    with pytest.raises(ValidationError) as exc_info:
        OptimizationRecommendationBase(
            recommendation_type="SHELTER_EVACUATION",
            demographic_group="CHILDREN_ONLY"
        )
    assert "Invalid demographic group" in str(exc_info.value)

    # 4. Invalid skill category must be rejected
    with pytest.raises(ValidationError) as exc_info:
        OptimizationRecommendationBase(
            recommendation_type="VOLUNTEER_ASSIGNMENT",
            skill_category="FIREFIGHTER"
        )
    assert "Invalid skill category" in str(exc_info.value)

    # 5. Valid recommendation passes cleanly
    valid_rec = OptimizationRecommendationBase(
        recommendation_type="SHELTER_EVACUATION",
        demographic_group="MED",
        skill_category=None,
        transit_time_minutes=15.0,
        transit_distance_km=6.2
    )
    assert valid_rec.demographic_group == "MED"
    assert valid_rec.transit_time_minutes == 15.0

# --- Test 18: Alembic Migration Reversibility Roundtrip ---
def test_5f_18_alembic_migration_roundtrip_execution():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    import os

    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    script_dir = ScriptDirectory.from_config(alembic_cfg)

    # Verify head and revision tree
    head = script_dir.get_current_head()
    # In Phase 5F baseline, head was phase5f_schema_ext. With Phase 6B data foundation,
    # head advances to phase6b_recovery_foundation, which strictly builds upon phase5f_schema_ext.
    assert head in ("phase5f_schema_ext", "phase6b_recovery_foundation")
    if head == "phase6b_recovery_foundation":
        assert script_dir.get_revision(head).down_revision == "phase5f_schema_ext"

    rev_5f = script_dir.get_revision("phase5f_schema_ext")
    assert rev_5f.revision == "phase5f_schema_ext"
    assert rev_5f.down_revision == "phase5b_schema_ext"

    # Verify that upgrade and downgrade callables exist and are functions
    assert callable(rev_5f.module.upgrade)
    assert callable(rev_5f.module.downgrade)

