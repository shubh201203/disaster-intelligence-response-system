import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models.incident import Incident
from app.models.recovery import (
    RecoveryAssessment,
    RecoveryNeed,
    RecoveryProject,
    ProjectDependency,
    RecoveryResource,
    CommunityRecoveryMetric,
    RecoveryOverrideLog
)
from app.core.security import hash_beneficiary_id, mask_person_name

client = TestClient(app)


def create_test_user(role: str):
    email = f"test_{role.lower()}_{uuid.uuid4().hex[:6]}@dirs.gov.in"
    password = "TestPassword123!"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": f"{role} Test User",
        "role": role
    })
    res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def auth_headers():
    _, govt_h = create_test_user("GOVT")
    _, vol_h = create_test_user("VOLUNTEER")
    _, cit_h = create_test_user("CITIZEN")
    _, ngo_h = create_test_user("NGO")
    return {
        "GOVT": govt_h,
        "VOLUNTEER": vol_h,
        "CITIZEN": cit_h,
        "NGO": ngo_h
    }


@pytest.fixture(scope="module")
def sample_incident(db_session: Session):
    inc = db_session.query(Incident).first()
    if not inc:
        inc = Incident(
            incident_code=f"INC-TEST-{uuid.uuid4().hex[:4].upper()}",
            title="Severe Flood Inundation",
            disaster_type="FLOOD",
            description="Flooding near medical clinic",
            latitude=13.0827,
            longitude=80.2707,
            people_affected=100
        )
        db_session.add(inc)
        db_session.commit()
        db_session.refresh(inc)
    return inc


# ==============================================================================
# 1. ASSESSMENT CREATION, VERIFICATION & VERSIONING
# ==============================================================================

def test_recovery_assessment_lifecycle(auth_headers, sample_incident):
    govt_hdr = auth_headers["GOVT"]
    vol_hdr = auth_headers["VOLUNTEER"]
    cit_hdr = auth_headers["CITIZEN"]

    # Citizen cannot create assessment
    res_cit = client.post("/api/v1/recovery/assessments", headers=cit_hdr, json={
        "incident_id": sample_incident.id,
        "sector": "HEALTH",
        "facility_name": "Ward 4 Primary Clinic",
        "damage_level": "MODERATE",
        "estimated_reconstruction_cost": 500000.0,
        "latitude": 13.0827,
        "longitude": 80.2707
    })
    assert res_cit.status_code == 403

    # Volunteer can submit assessment
    res_vol = client.post("/api/v1/recovery/assessments", headers=vol_hdr, json={
        "incident_id": sample_incident.id,
        "sector": "HEALTH",
        "facility_name": "Ward 4 Primary Clinic",
        "damage_level": "MODERATE",
        "is_operational": False,
        "estimated_reconstruction_cost": 500000.0,
        "structural_notes": "Roof damaged by falling tree; walls intact.",
        "latitude": 13.0827,
        "longitude": 80.2707
    })
    assert res_vol.status_code == 201
    asm_data = res_vol.json()
    asm_id = asm_data["id"]
    assert asm_data["assessment_version"] == 1
    assert asm_data["is_current_version"] is True
    assert asm_data["verification_status"] == "PENDING_VERIFICATION"
    assert asm_data["assessment_code"].startswith("ASM-")

    # Volunteer cannot verify assessment
    res_vol_ver = client.post(f"/api/v1/recovery/assessments/{asm_id}/verify", headers=vol_hdr, json={
        "action": "VERIFY"
    })
    assert res_vol_ver.status_code == 403

    # Government officer verifies assessment
    res_gov_ver = client.post(f"/api/v1/recovery/assessments/{asm_id}/verify", headers=govt_hdr, json={
        "action": "VERIFY",
        "verified_cost": 480000.0,
        "notes": "Verified by PWD Assistant Engineer."
    })
    assert res_gov_ver.status_code == 200
    assert res_gov_ver.json()["verification_status"] == "VERIFIED"
    assert res_gov_ver.json()["estimated_reconstruction_cost"] == 480000.0

    # Government supersedes assessment with Version 2
    res_sup = client.post(f"/api/v1/recovery/assessments/{asm_id}/supersede", headers=govt_hdr, json={
        "new_damage_level": "SEVERE",
        "new_estimated_cost": 750000.0,
        "is_operational": False,
        "structural_notes": "Foundation crack observed upon re-inspection.",
        "justification_reason": "Detailed geotechnical inspection revealed subsurface foundation damage."
    })
    assert res_sup.status_code == 201
    v2_data = res_sup.json()
    assert v2_data["assessment_version"] == 2
    assert v2_data["is_current_version"] is True
    assert v2_data["damage_level"] == "SEVERE"
    assert v2_data["estimated_reconstruction_cost"] == 750000.0

    # Check that Version 1 is preserved historically but marked is_current_version=False
    res_v1 = client.get(f"/api/v1/recovery/assessments/{asm_id}", headers=govt_hdr)
    assert res_v1.status_code == 200
    assert res_v1.json()["is_current_version"] is False
    assert res_v1.json()["superseded_by_id"] == v2_data["id"]
    assert res_v1.json()["reconciliation_status"] == "SUPERSEDED"


# ==============================================================================
# 2. RECOVERY NEEDS & DOUBLE-COUNT RECONCILIATION
# ==============================================================================

def test_recovery_needs_and_privacy(auth_headers, sample_incident):
    govt_hdr = auth_headers["GOVT"]
    cit_hdr = auth_headers["CITIZEN"]

    # Beneficiary ID hashing and name masking unit tests
    raw_beneficiary_id = "AADHAAR-8839-4401-9923"
    hashed = hash_beneficiary_id(raw_beneficiary_id)
    assert hashed != raw_beneficiary_id
    assert len(hashed) == 64  # SHA-256 hex digest
    assert hash_beneficiary_id(raw_beneficiary_id) == hashed  # Deterministic with salt

    masked_name = mask_person_name("Ramesh Kumar")
    assert masked_name == "R****h K***r"

    # Create Recovery Need with population exceeding census cap (Double-counting test)
    res_need = client.post("/api/v1/recovery/needs", headers=govt_hdr, json={
        "ward_code": "WARD-14",
        "district": "Chennai Central",
        "sector": "WASH",
        "affected_households": 2500,
        "displaced_persons": 15000,  # Exceeds census baseline 10,000!
        "vulnerable_persons": 2000,
        "raw_beneficiary_id": raw_beneficiary_id,
        "household_head_name": "Ramesh Kumar",
        "potable_water_demand_liters_day": 75000.0,
        "census_baseline_population": 10000
    })
    assert res_need.status_code == 201
    need_data = res_need.json()
    assert need_data["displaced_persons"] == 10000  # Capped!
    assert need_data["is_reconciled"] is True
    assert "capped" in need_data["reconciliation_notes"].lower()
    assert need_data["beneficiary_id_hash"] == hashed
    assert need_data["household_head_name_masked"] == "R****h K***r"

    # Verify PII access restriction: Citizen does NOT receive beneficiary hash or masked name
    res_cit_needs = client.get("/api/v1/recovery/needs?ward_code=WARD-14", headers=cit_hdr)
    assert res_cit_needs.status_code == 200
    for n in res_cit_needs.json():
        assert "beneficiary_id_hash" not in n
        assert "household_head_name_masked" not in n
        assert "ward_code" in n


# ==============================================================================
# 3. RECOVERY PROJECTS & GOVT APPROVAL GATE
# ==============================================================================

def test_recovery_project_governance(auth_headers):
    govt_hdr = auth_headers["GOVT"]
    cit_hdr = auth_headers["CITIZEN"]
    vol_hdr = auth_headers["VOLUNTEER"]

    # Citizen and Volunteer cannot create projects
    res_cit_prj = client.post("/api/v1/recovery/projects", headers=cit_hdr, json={
        "title": "Substation Cable Replacement",
        "sector": "POWER",
        "estimated_cost": 1500000.0,
        "estimated_duration_days": 14,
        "lead_agency": "TANGEDCO"
    })
    assert res_cit_prj.status_code == 403

    # Government creates project
    res_gov_prj = client.post("/api/v1/recovery/projects", headers=govt_hdr, json={
        "title": "Substation Cable Replacement",
        "sector": "POWER",
        "priority_tier": "TIER_1",
        "priority_score": 88.5,
        "estimated_cost": 1500000.0,
        "estimated_duration_days": 14,
        "lead_agency": "TANGEDCO",
        "latitude": 13.0827,
        "longitude": 80.2707
    })
    assert res_gov_prj.status_code == 201
    prj_data = res_gov_prj.json()
    prj_id = prj_data["id"]
    assert prj_data["status"] == "PROPOSED"
    assert prj_data["approval_status"] == "PENDING_APPROVAL"
    assert prj_data["actual_expenditure"] == 0.0

    # Volunteer cannot approve project
    res_vol_app = client.post(f"/api/v1/recovery/projects/{prj_id}/approve", headers=vol_hdr, json={
        "approved_budget": 1500000.0,
        "funding_source": "STATE_SDRF",
        "sanction_order_number": "SDRF/2026/ORD-101"
    })
    assert res_vol_app.status_code == 403

    # Government officer approves project with Sanction Order
    res_gov_app = client.post(f"/api/v1/recovery/projects/{prj_id}/approve", headers=govt_hdr, json={
        "approved_budget": 1450000.0,
        "funding_source": "STATE_SDRF",
        "sanction_order_number": "SDRF/2026/ORD-101",
        "notes": "Approved by District Collector."
    })
    assert res_gov_app.status_code == 200
    assert res_gov_app.json()["status"] == "APPROVED"
    assert res_gov_app.json()["approval_status"] == "APPROVED"
    assert res_gov_app.json()["sanction_order_number"] == "SDRF/2026/ORD-101"

    # Government updates progress and expenditure
    res_status = client.patch(f"/api/v1/recovery/projects/{prj_id}/status", headers=govt_hdr, json={
        "status": "IN_PROGRESS",
        "actual_expenditure_increment": 350000.0,
        "notes": "Contractor commenced civil excavation."
    })
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "IN_PROGRESS"
    assert res_status.json()["actual_expenditure"] == 350000.0


# ==============================================================================
# 4. DEPENDENCY GRAPH & KAHN'S CYCLE DETECTION
# ==============================================================================

def test_dependency_graph_cycle_detection(auth_headers):
    govt_hdr = auth_headers["GOVT"]

    # Create 3 projects: P_A, P_B, P_C
    def make_prj(title):
        r = client.post("/api/v1/recovery/projects", headers=govt_hdr, json={
            "title": title,
            "sector": "TRANSPORT",
            "estimated_cost": 100000.0,
            "estimated_duration_days": 5,
            "lead_agency": "PWD Highways"
        })
        return r.json()["id"]

    id_a = make_prj("Access Road A")
    id_b = make_prj("Culvert Repair B")
    id_c = make_prj("Asphalt Resurfacing C")

    # Add Edge A -> B
    res_ab = client.post("/api/v1/recovery/dependencies", headers=govt_hdr, json={
        "predecessor_project_id": id_a,
        "successor_project_id": id_b,
        "lag_days": 1
    })
    assert res_ab.status_code == 201

    # Add Edge B -> C
    res_bc = client.post("/api/v1/recovery/dependencies", headers=govt_hdr, json={
        "predecessor_project_id": id_b,
        "successor_project_id": id_c,
        "lag_days": 0
    })
    assert res_bc.status_code == 201

    # Self-loop rejection test: C -> C
    res_self = client.post("/api/v1/recovery/dependencies", headers=govt_hdr, json={
        "predecessor_project_id": id_c,
        "successor_project_id": id_c
    })
    assert res_self.status_code == 400
    assert res_self.json()["detail"]["error_code"] == "ERR_SELF_LOOP"

    # Cycle creation test: C -> A would create A -> B -> C -> A
    res_cycle = client.post("/api/v1/recovery/dependencies", headers=govt_hdr, json={
        "predecessor_project_id": id_c,
        "successor_project_id": id_a
    })
    assert res_cycle.status_code == 400
    assert res_cycle.json()["detail"]["error_code"] == "ERR_CYCLIC_DEPENDENCY"


# ==============================================================================
# 5. RECOVERY RESOURCES & COMMUNITY METRICS
# ==============================================================================

def test_recovery_resources_and_community_metrics(auth_headers):
    govt_hdr = auth_headers["GOVT"]
    ngo_hdr = auth_headers["NGO"]
    cit_hdr = auth_headers["CITIZEN"]

    # Create Project
    prj_res = client.post("/api/v1/recovery/projects", headers=govt_hdr, json={
        "title": "Hospital Wing Rehabilitation",
        "sector": "HEALTH",
        "estimated_cost": 800000.0,
        "estimated_duration_days": 10,
        "lead_agency": "Health Dept"
    })
    prj_id = prj_res.json()["id"]

    # NGO allocates resources
    res_mat = client.post("/api/v1/recovery/resources", headers=ngo_hdr, json={
        "project_id": prj_id,
        "material_category": "CEMENT",
        "item_description": "Portland Pozzolana Cement (PPC)",
        "quantity_required": 50.0,
        "unit_of_measure": "METRIC_TONS",
        "unit_cost_estimate": 7000.0,
        "supplier_info": "Red Cross Emergency Logistics Depot"
    })
    assert res_mat.status_code == 201
    assert res_mat.json()["material_category"] == "CEMENT"
    assert res_mat.json()["quantity_required"] == 50.0

    # Ingest Community Recovery Metric
    res_metric = client.post("/api/v1/recovery/community-metrics", headers=govt_hdr, json={
        "ward_code": "WARD-08",
        "district": "Chennai North",
        "metric_date": "2026-11-15T00:00:00Z",
        "active_shelter_count": 2,
        "remaining_displaced_persons": 180,
        "power_grid_restoration_pct": 92.5,
        "potable_water_access_pct": 85.0,
        "healthcare_facility_operational_pct": 100.0,
        "schools_open_pct": 75.0,
        "livelihoods_resumed_pct": 60.0,
        "overall_recovery_score": 82.0
    })
    assert res_metric.status_code == 201
    assert res_metric.json()["freshness_status"] in ("FRESH", "MODERATE")

    # Citizen can query public community metrics
    res_pub = client.get("/api/v1/recovery/community-metrics?ward_code=WARD-08", headers=cit_hdr)
    assert res_pub.status_code == 200
    assert len(res_pub.json()) >= 1
    assert res_pub.json()[0]["power_grid_restoration_pct"] == 92.5


# ==============================================================================
# 6. OVERRIDE AUDIT LOG VERIFICATION
# ==============================================================================

def test_recovery_override_logs_audit(auth_headers):
    govt_hdr = auth_headers["GOVT"]
    cit_hdr = auth_headers["CITIZEN"]

    # Citizen cannot access override logs
    res_cit_over = client.get("/api/v1/recovery/overrides", headers=cit_hdr)
    assert res_cit_over.status_code == 403

    # Government accesses override logs
    res_gov_over = client.get("/api/v1/recovery/overrides", headers=govt_hdr)
    assert res_gov_over.status_code == 200
    logs = res_gov_over.json()
    assert len(logs) >= 1
    actions = [l["action"] for l in logs]
    assert any(a in ("PROJECT_APPROVE", "ASSESSMENT_SUPERSEDE") for a in actions)
