import os
import uuid
import base64
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from PIL import Image
import io

from app.main import app
from app.database import SessionLocal
from app.models.incident import Incident
from app.models.recovery import RecoveryAssessment, RecoveryNeed, RecoveryOverrideLog
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
def sample_incident():
    db = SessionLocal()
    try:
        inc = Incident(
            incident_code=f"INC-TEST-{uuid.uuid4().hex[:4].upper()}",
            title="Cyclone Recovery Zone - Ennore Ward 4",
            disaster_type="CYCLONE",
            status="VERIFIED",
            latitude=13.2000,
            longitude=80.3200,
            description="Severe coastal structural damage following cyclone landfall"
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)
        return inc
    finally:
        db.close()


@pytest.fixture(scope="module")
def synthetic_test_image_b64():
    """Generates a small in-memory synthetic image as base64 for controlled CV testing."""
    img = Image.new("RGB", (128, 128), color=(120, 100, 90))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ==============================================================================
# 1. CV INTEGRATION & TIER-1 SCREENING TESTS
# ==============================================================================

def test_cv_tier1_damage_screening_lifecycle(auth_headers, sample_incident, synthetic_test_image_b64):
    govt_hdr = auth_headers["GOVT"]
    cit_hdr = auth_headers["CITIZEN"]
    vol_hdr = auth_headers["VOLUNTEER"]

    # Citizen cannot access screening
    res_cit = client.post("/api/v1/recovery/damage-assessments/screen-image", headers=cit_hdr, json={
        "image_base64": synthetic_test_image_b64,
        "incident_id": sample_incident.id
    })
    assert res_cit.status_code == 403

    # Volunteer / Inspector triggers Tier-1 screening
    res_vol = client.post("/api/v1/recovery/damage-assessments/screen-image", headers=vol_hdr, json={
        "image_base64": synthetic_test_image_b64,
        "incident_id": sample_incident.id
    })
    assert res_vol.status_code == 200
    data = res_vol.json()

    assert "cv_assessment_id" in data
    assert data["model_name"] == "cv-damage-classifier-resnet18"
    assert data["model_version"] == "2.0.0-realworld"
    assert data["predicted_damage_class"] in ["NO_DAMAGE", "LOW_DAMAGE", "MODERATE_DAMAGE", "SEVERE_DAMAGE", "DESTROYED"]
    assert data["mapped_recovery_damage_level"] in ["NONE", "MINOR", "MODERATE", "SEVERE", "DESTROYED"]
    assert 0.0 <= data["confidence_score"] <= 100.0
    assert len(data["image_sha256"]) == 64  # Valid SHA-256 hex string
    assert "Tier-1 AI screening only" in data["screening_disclaimer"]
    assert "structural engineering verification" in data["screening_disclaimer"]


def test_cv_screening_invalid_and_corrupt_inputs(auth_headers, sample_incident):
    vol_hdr = auth_headers["VOLUNTEER"]

    # Empty request
    res_empty = client.post("/api/v1/recovery/damage-assessments/screen-image", headers=vol_hdr, json={})
    assert res_empty.status_code == 400
    assert "Either image_path or image_bytes must be provided" in res_empty.json()["detail"]

    # Corrupt base64 string
    res_corrupt = client.post("/api/v1/recovery/damage-assessments/screen-image", headers=vol_hdr, json={
        "image_base64": "NOT_A_VALID_BASE64_IMAGE!@#$",
        "incident_id": sample_incident.id
    })
    assert res_corrupt.status_code in (400, 422)

    # Missing file path
    res_missing_file = client.post("/api/v1/recovery/damage-assessments/screen-image", headers=vol_hdr, json={
        "image_path": "/nonexistent/path/to/evidence_img_404.jpg",
        "incident_id": sample_incident.id
    })
    assert res_missing_file.status_code == 404


# ==============================================================================
# 2. FIELD INSPECTION, ENGINEERING VERIFICATION & SUPERSESSION
# ==============================================================================

def test_field_inspection_and_engineering_verification_gate(auth_headers, sample_incident, synthetic_test_image_b64):
    govt_hdr = auth_headers["GOVT"]
    vol_hdr = auth_headers["VOLUNTEER"]
    cit_hdr = auth_headers["CITIZEN"]

    # 1. Screen image first
    res_screen = client.post("/api/v1/recovery/damage-assessments/screen-image", headers=vol_hdr, json={
        "image_base64": synthetic_test_image_b64,
        "incident_id": sample_incident.id
    })
    cv_id = res_screen.json()["cv_assessment_id"]

    # 2. Submit formal field inspection linked to CV screening
    res_field = client.post("/api/v1/recovery/damage-assessments/field-inspection", headers=vol_hdr, json={
        "incident_id": sample_incident.id,
        "sector": "EDUCATION",
        "facility_name": "Ennore Government Higher Secondary School",
        "damage_level": "MODERATE",
        "is_operational": False,
        "estimated_reconstruction_cost": 750000.0,
        "structural_notes": "Main classroom block roof tiles dislodged; structural beams sound.",
        "cv_assessment_id": cv_id,
        "latitude": 13.2050,
        "longitude": 80.3220,
        "assessor_confidence": 92.0
    })
    assert res_field.status_code == 201
    asm = res_field.json()
    asm_id = asm["id"]
    assert asm["verification_status"] == "PENDING_VERIFICATION"
    assert asm["assessment_version"] == 1
    assert asm["is_current_version"] is True
    assert asm["cv_assessment_id"] == cv_id

    # 3. Citizen / Volunteer cannot verify engineering assessments
    res_cit_ver = client.post(f"/api/v1/recovery/damage-assessments/{asm_id}/verify", headers=vol_hdr, json={
        "action": "VERIFY",
        "engineering_notes": "Volunteer attempt to approve."
    })
    assert res_cit_ver.status_code == 403

    # 4. Government Engineer verifies and upgrades damage level
    res_gov_ver = client.post(f"/api/v1/recovery/damage-assessments/{asm_id}/verify", headers=govt_hdr, json={
        "action": "VERIFY",
        "verified_damage_level": "SEVERE",
        "engineering_notes": "Chief Structural Engineer Inspection: Beam joint micro-cracking observed under magnification. Escalated to SEVERE."
    })
    assert res_gov_ver.status_code == 200
    ver_data = res_gov_ver.json()
    assert ver_data["verification_status"] == "VERIFIED"
    assert ver_data["damage_level"] == "SEVERE"
    assert ver_data["verified_by_id"] is not None

    # 5. Monotonic supersession (V1 -> V2)
    res_sup = client.post(f"/api/v1/recovery/damage-assessments/{asm_id}/supersede", headers=vol_hdr, json={
        "new_damage_level": "DESTROYED",
        "new_estimated_cost": 2500000.0,
        "is_operational": False,
        "structural_notes": "Subsequent aftershock caused full collapse of east wing.",
        "supersede_reason": "Total structural collapse during secondary seismic event."
    })
    assert res_sup.status_code == 200
    v2_asm = res_sup.json()
    assert v2_asm["assessment_version"] == 2
    assert v2_asm["is_current_version"] is True
    assert v2_asm["damage_level"] == "DESTROYED"

    # 6. Retrieve version lineage history
    res_hist = client.get(f"/api/v1/recovery/damage-assessments/{asm_id}/history", headers=vol_hdr)
    assert res_hist.status_code == 200
    hist = res_hist.json()
    assert hist["total_versions"] == 2
    assert hist["current_version"] == 2
    assert len(hist["version_lineage"]) == 2


# ==============================================================================
# 3. STRUCTURED RECOVERY NEEDS & DEMOGRAPHIC CONSERVATION
# ==============================================================================

def test_structured_needs_and_demographic_conservation(auth_headers, sample_incident):
    govt_hdr = auth_headers["GOVT"]
    ngo_hdr = auth_headers["NGO"]
    cit_hdr = auth_headers["CITIZEN"]

    # Citizen cannot submit structured recovery needs
    res_cit = client.post("/api/v1/recovery/needs/structured", headers=cit_hdr, json={
        "ward_code": "WARD-04",
        "district": "Chennai North",
        "sector": "HOUSING",
        "affected_households": 40,
        "census_baseline_population": 5000
    })
    assert res_cit.status_code == 403

    # Rejection of negative population
    res_neg = client.post("/api/v1/recovery/needs/structured", headers=ngo_hdr, json={
        "ward_code": "WARD-04",
        "district": "Chennai North",
        "sector": "HOUSING",
        "affected_households": 25,
        "affected_population_gen": -10,
        "affected_population_acc": 5,
        "affected_population_med": 2,
        "affected_population_med_acc": 1,
        "census_baseline_population": 5000
    })
    assert res_neg.status_code in (400, 422)

    # Successful creation with Demographic Conservation (GEN + ACC + MED + MED_ACC)
    # GEN: 80, ACC: 12, MED: 8, MED_ACC: 4 => Total = 104
    res_ngo = client.post("/api/v1/recovery/needs/structured", headers=ngo_hdr, json={
        "ward_code": "WARD-04",
        "district": "Chennai North",
        "sector": "HOUSING",
        "affected_households": 26,
        "displaced_persons": 45,
        "affected_population_gen": 80,
        "affected_population_acc": 12,
        "affected_population_med": 8,
        "affected_population_med_acc": 4,
        "raw_beneficiary_id": "AADHAAR-9988-7766-5544",
        "raw_household_head_name": "Ramesh Swaminathan",
        "potable_water_demand_liters_day": 1500.0,
        "temporary_shelter_units_needed": 26,
        "census_baseline_population": 10000,
        "urgency_tier": "HIGH_TIER2"
    })
    assert res_ngo.status_code == 201
    need_data = res_ngo.json()

    assert need_data["total_affected_population"] == 104
    assert need_data["vulnerable_persons"] == (12 + 8 + 4)  # ACC + MED + MED_ACC = 24
    assert need_data["beneficiary_id_hash"] is not None
    assert len(need_data["beneficiary_id_hash"]) == 64
    assert "9988" not in need_data["beneficiary_id_hash"]  # Plaintext never persisted
    assert need_data["household_head_name_masked"] == "R****h S*********n"
    assert need_data["exceeds_census_cap"] is False


# ==============================================================================
# 4. POPULATION RECONCILIATION & CENSUS CAPPING
# ==============================================================================

def test_population_reconciliation_deduplication_and_conflicts(auth_headers):
    govt_hdr = auth_headers["GOVT"]
    ngo_hdr = auth_headers["NGO"]

    ward = f"WARD-{uuid.uuid4().hex[:4].upper()}"

    # Ingest 2 needs with IDENTICAL raw_beneficiary_id to test deduplication
    shared_ben_id = f"RATION-{uuid.uuid4().hex[:8]}"

    # Observation 1
    client.post("/api/v1/recovery/needs/structured", headers=ngo_hdr, json={
        "ward_code": ward,
        "district": "Chennai South",
        "sector": "WASH",
        "affected_households": 5,
        "displaced_persons": 15,
        "affected_population_gen": 15,
        "raw_beneficiary_id": shared_ben_id,
        "raw_household_head_name": "Kavitha Sundaram",
        "census_baseline_population": 2000
    })

    # Observation 2 (Duplicate observation of same beneficiary)
    client.post("/api/v1/recovery/needs/structured", headers=ngo_hdr, json={
        "ward_code": ward,
        "district": "Chennai South",
        "sector": "HEALTH",
        "affected_households": 5,
        "displaced_persons": 15,
        "affected_population_gen": 15,
        "raw_beneficiary_id": shared_ben_id,
        "raw_household_head_name": "Kavitha Sundaram",
        "census_baseline_population": 2000
    })

    # Trigger population reconciliation
    res_rec = client.post("/api/v1/recovery/reconciliation/reconcile-population", headers=govt_hdr, json={
        "ward_code": ward
    })
    assert res_rec.status_code == 200
    rec = res_rec.json()

    assert rec["source_record_count"] == 2
    assert rec["unique_beneficiary_count"] == 1  # Successfully deduplicated!
    assert rec["reconciled_affected_households"] == 5  # Not double-counted to 10
    assert len(rec["duplicate_candidates"]) == 1
    assert rec["duplicate_candidates"][0]["record_count"] == 2
    assert rec["reconciliation_status"] in ("RECONCILED_DEDUPLICATED", "FULLY_RECONCILED")


# ==============================================================================
# 5. SPATIAL RECOVERY INTELLIGENCE & ANALYTICS SUMMARY
# ==============================================================================

def test_spatial_recovery_queries_and_public_analytics(auth_headers, sample_incident):
    govt_hdr = auth_headers["GOVT"]
    cit_hdr = auth_headers["CITIZEN"]

    # 1. Radius Query
    res_rad = client.get("/api/v1/recovery/spatial/radius?latitude=13.2000&longitude=80.3200&radius_km=10.0", headers=govt_hdr)
    assert res_rad.status_code == 200
    assert isinstance(res_rad.json(), list)

    # 2. Invalid Coordinate Rejection
    res_inv = client.get("/api/v1/recovery/spatial/radius?latitude=195.0&longitude=80.0&radius_km=10.0", headers=govt_hdr)
    assert res_inv.status_code == 400
    assert "Invalid search coordinates" in res_inv.json()["detail"]

    # 3. Ward Spatial Summary (Synthetic GeoJSON)
    res_ward = client.get("/api/v1/recovery/spatial/damage-summary?ward_code=WARD-01", headers=govt_hdr)
    assert res_ward.status_code == 200
    w_data = res_ward.json()
    assert w_data["ward_code"] == "WARD-01"
    assert w_data["is_synthetic_boundary"] is True
    assert "disclaimer" in w_data["spatial_boundary_geojson"]["properties"]

    # 4. Public Analytics Summary (No Auth Required)
    res_pub = client.get("/api/v1/recovery/analytics/summary")
    assert res_pub.status_code == 200
    pub = res_pub.json()
    assert "total_facilities_assessed" in pub
    assert "damage_distribution" in pub
    assert "average_power_restoration_pct" in pub
    # Verify zero PII leakage
    assert "beneficiary" not in str(pub).lower()
    assert "aadhaar" not in str(pub).lower()


# ==============================================================================
# 6. REMEDIATION REGRESSION TESTS (DEF-6C-SPA-01 & DEF-6C-SEC-01)
# ==============================================================================

def test_public_analytics_segregation_of_verified_pending_and_rejected(auth_headers, sample_incident):
    """
    DEF-6C-SPA-01: Verifies that public situational analytics strictly includes
    only VERIFIED assessments in official totals, segregates preliminary unverified
    screenings, excludes REJECTED assessments, and scrubs all household PII.
    """
    govt_hdr = auth_headers["GOVT"]
    vol_hdr = auth_headers["VOLUNTEER"]

    # 1. Create Assessment A -> will be VERIFIED
    res_a = client.post("/api/v1/recovery/damage-assessments/field-inspection", headers=vol_hdr, json={
        "incident_id": sample_incident.id,
        "sector": "HEALTH",
        "facility_name": "Remediation Health Center Alpha",
        "damage_level": "MODERATE",
        "is_operational": True,
        "estimated_reconstruction_cost": 300000.0,
        "latitude": 13.0850,
        "longitude": 80.2800
    })
    assert res_a.status_code == 201
    asm_a_id = res_a.json()["id"]

    # GOVT verifies Assessment A
    res_ver_a = client.post(f"/api/v1/recovery/damage-assessments/{asm_a_id}/verify", headers=govt_hdr, json={
        "action": "VERIFY",
        "verified_damage_level": "MODERATE",
        "engineering_notes": "Structural integrity confirmed by Municipal Engineer."
    })
    assert res_ver_a.status_code == 200

    # 2. Create Assessment B -> remains PENDING_VERIFICATION (Preliminary unverified)
    res_b = client.post("/api/v1/recovery/damage-assessments/field-inspection", headers=vol_hdr, json={
        "incident_id": sample_incident.id,
        "sector": "EDUCATION",
        "facility_name": "Remediation Primary School Beta",
        "damage_level": "DESTROYED",
        "is_operational": False,
        "estimated_reconstruction_cost": 1200000.0,
        "latitude": 13.0910,
        "longitude": 80.2850
    })
    assert res_b.status_code == 201
    asm_b_id = res_b.json()["id"]

    # 3. Create Assessment C -> will be REJECTED
    res_c = client.post("/api/v1/recovery/damage-assessments/field-inspection", headers=vol_hdr, json={
        "incident_id": sample_incident.id,
        "sector": "HOUSING",
        "facility_name": "Remediation Spurious Claim Gamma",
        "damage_level": "SEVERE",
        "is_operational": False,
        "estimated_reconstruction_cost": 900000.0,
        "latitude": 13.0950,
        "longitude": 80.2900
    })
    assert res_c.status_code == 201
    asm_c_id = res_c.json()["id"]

    # GOVT rejects Assessment C
    res_ver_c = client.post(f"/api/v1/recovery/damage-assessments/{asm_c_id}/verify", headers=govt_hdr, json={
        "action": "REJECT",
        "engineering_notes": "Duplicate/spurious field report. Rejected."
    })
    assert res_ver_c.status_code == 200

    # 4. Query Public Analytics
    res_pub = client.get("/api/v1/recovery/analytics/summary")
    assert res_pub.status_code == 200
    pub = res_pub.json()

    # Assertions:
    # A. Verified assessments included in verified totals
    assert pub["verified_facilities_count"] >= 1
    # B. Preliminary unverified assessments segregated
    assert pub["preliminary_screening_count"] >= 1
    # C. Rejected assessments recorded separately
    assert pub["rejected_assessments_count"] >= 1
    # D. Verified damage distribution includes Assessment A (MODERATE)
    assert pub["damage_distribution"].get("MODERATE", 0) >= 1
    # E. Preliminary damage distribution includes Assessment B (DESTROYED) separately
    assert pub["preliminary_damage_distribution"].get("DESTROYED", 0) >= 1
    # F. Exclude household-level PII
    assert "beneficiary" not in str(pub).lower()
    assert "household_head" not in str(pub).lower()
    assert "Remediation Health Center" not in str(pub)  # Facility names scrubbed in summary


def test_beneficiary_hash_salt_missing_fails_closed(monkeypatch):
    """
    DEF-6C-SEC-01: Verifies that beneficiary pseudonymization strictly fails closed
    with a clear RuntimeError when BENEFICIARY_HASH_SALT is missing or empty,
    rather than silently falling back to an insecure default.
    """
    from app.core.security import hash_beneficiary_id
    from app.config import settings

    raw_id = "AADHAAR-SEC-TEST-9988-1122"

    # 1. With configured salt -> works and is deterministic
    configured_salt = "prod_disaster_recovery_salt_2026_xyz"
    monkeypatch.setattr(settings, "BENEFICIARY_HASH_SALT", configured_salt)
    monkeypatch.setenv("BENEFICIARY_HASH_SALT", configured_salt)

    hash1 = hash_beneficiary_id(raw_id)
    assert len(hash1) == 64
    assert hash_beneficiary_id(raw_id) == hash1

    # 2. When salt is empty or unconfigured -> fails closed with RuntimeError
    monkeypatch.setattr(settings, "BENEFICIARY_HASH_SALT", "")
    monkeypatch.setenv("BENEFICIARY_HASH_SALT", "")

    with pytest.raises(RuntimeError) as exc_info:
        hash_beneficiary_id(raw_id)

    assert "CRITICAL SECURITY CONFIGURATION ERROR" in str(exc_info.value)
    assert "BENEFICIARY_HASH_SALT is not configured" in str(exc_info.value)

    # 3. None / absent salt -> also fails closed
    monkeypatch.setattr(settings, "BENEFICIARY_HASH_SALT", None)
    monkeypatch.delenv("BENEFICIARY_HASH_SALT", raising=False)

    with pytest.raises(RuntimeError) as exc_info_none:
        hash_beneficiary_id(raw_id)

    assert "CRITICAL SECURITY CONFIGURATION ERROR" in str(exc_info_none.value)

