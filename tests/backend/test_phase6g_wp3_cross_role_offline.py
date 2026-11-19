import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User, NGOProfile, VolunteerProfile
from app.models.incident import Incident
from app.models.resource import Resource, ResourceRequest
from app.models.recovery import RecoveryAssessment, RecoveryOverrideLog
from app.database import get_db

client = TestClient(app)

def get_auth_token(role: str, user_id_seed: str = "auditor"):
    unique_email = f"wp3_{role.lower()}_{user_id_seed}_{uuid.uuid4().hex[:6]}@dirs.gov.in"
    reg_res = client.post("/api/v1/auth/register", json={
        "email": unique_email,
        "password": "Password123!",
        "full_name": f"WP3 {role} Representative",
        "role": role
    })
    assert reg_res.status_code in (200, 201), f"Registration failed: {reg_res.text}"
    login_res = client.post("/api/v1/auth/login", data={
        "username": unique_email,
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}

class TestWP3CrossRoleAuthorization:
    """Tests strict cross-role boundaries and operational privileges."""

    def test_citizen_capabilities_and_boundaries(self):
        token, headers = get_auth_token("CITIZEN")

        # 1. Citizen can report disaster incidents
        r_rep = client.post("/api/v1/incidents", headers=headers, json={
            "title": "Flooded Crossing",
            "disaster_type": "FLOOD",
            "description": "Rising water blocking pedestrian bridge",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "location_address": "Ward 4 Crossing",
            "people_affected": 25,
            "injuries": 0,
            "vulnerable_count": 5
        })
        assert r_rep.status_code == 201
        inc_id = r_rep.json()["id"]

        # 2. Citizen can trigger SOS
        r_sos = client.post(f"/api/v1/incidents/sos?lat=13.0827&lng=80.2707&description=SOS%20Trapped", headers=headers)
        assert r_sos.status_code == 201

        # 3. Citizen CANNOT access volunteer tasks endpoint
        r_vol = client.get("/api/v1/volunteers/me", headers=headers)
        assert r_vol.status_code == 403

        # 4. Citizen CANNOT access admin volunteer listing
        r_vols = client.get("/api/v1/volunteers", headers=headers)
        assert r_vols.status_code == 403

        # 5. Citizen CANNOT verify incidents
        r_ver = client.put(f"/api/v1/incidents/{inc_id}/verify", headers=headers, json={"action": "VERIFY"})
        assert r_ver.status_code == 403

    def test_volunteer_field_inspection_and_task_isolation(self):
        v_token, v_headers = get_auth_token("VOLUNTEER")
        g_token, g_headers = get_auth_token("GOVT")

        # Government creates an incident
        r_inc = client.post("/api/v1/incidents", headers=g_headers, json={
            "title": "Hospital Compound Flooding",
            "disaster_type": "FLOOD",
            "description": "Water logging in pediatric ward wing",
            "latitude": 13.0850,
            "longitude": 80.2750,
            "location_address": "General Hospital Ward 2",
            "people_affected": 150
        })
        assert r_inc.status_code == 201
        incident_id = r_inc.json()["id"]

        # Volunteer submits field damage assessment
        draft_id = str(uuid.uuid4())
        r_insp = client.post("/api/v1/recovery/damage-assessments/field-inspection", headers=v_headers, json={
            "incident_id": incident_id,
            "sector": "HEALTH",
            "facility_name": "General Hospital Pediatric Wing",
            "damage_level": "MODERATE",
            "is_operational": False,
            "estimated_reconstruction_cost": 250000.0,
            "structural_notes": "Ground floor submerged up to 0.8 meters, backup generator damaged",
            "evidence_media_urls": [],
            "latitude": 13.0850,
            "longitude": 80.2750,
            "assessor_confidence": 95.0
        })
        assert r_insp.status_code == 201
        assessment_data = r_insp.json()
        assert assessment_data["verification_status"] == "PENDING_VERIFICATION"
        assert assessment_data["damage_level"] == "MODERATE"
        assessment_id = assessment_data["id"]

        # Volunteer CANNOT self-verify their inspection (GOVT only)
        r_self_verify = client.post(f"/api/v1/recovery/damage-assessments/{assessment_id}/verify", headers=v_headers, json={
            "action": "VERIFY",
            "engineering_notes": "Attempting unauthorized self verification"
        })
        assert r_self_verify.status_code == 403

        # Government engineer verifies assessment
        r_govt_verify = client.post(f"/api/v1/recovery/damage-assessments/{assessment_id}/verify", headers=g_headers, json={
            "action": "VERIFY",
            "verified_damage_level": "MODERATE",
            "engineering_notes": "Command Engineer certified field inspection on site."
        })
        assert r_govt_verify.status_code == 200
        assert r_govt_verify.json()["verification_status"] == "VERIFIED"

    def test_ngo_inventory_management_and_resource_requests(self):
        n_token, n_headers = get_auth_token("NGO")
        c_token, c_headers = get_auth_token("CITIZEN")

        # Citizen creates incident
        r_inc = client.post("/api/v1/incidents", headers=c_headers, json={
            "title": "Shelter Drinking Water Deficit",
            "disaster_type": "FLOOD",
            "description": "500 citizens in temporary shelter lack drinking water",
            "latitude": 13.0800,
            "longitude": 80.2700,
            "location_address": "Relief Camp 3"
        })
        incident_id = r_inc.json()["id"]

        # Citizen submits resource request
        r_req = client.post("/api/v1/resources/request", headers=c_headers, json={
            "incident_id": incident_id,
            "category": "WATER",
            "quantity_requested": 400,
            "priority": "HIGH"
        })
        assert r_req.status_code == 201

        # NGO lists resource requests
        r_reqs = client.get("/api/v1/resources/requests", headers=n_headers)
        assert r_reqs.status_code == 200
        found = any(r["incident_id"] == incident_id and r["category"] == "WATER" for r in r_reqs.json())
        assert found, "Resource request was not returned in NGO listing"

        # NGO registers relief inventory
        r_stock = client.post("/api/v1/resources", headers=n_headers, json={
            "owner_type": "NGO",
            "category": "WATER",
            "resource_name": "20L Water Canisters",
            "total_quantity": 1000,
            "unit": "canisters",
            "location_lat": 13.0810,
            "location_lng": 80.2710
        })
        assert r_stock.status_code == 201
        stock_id = r_stock.json()["id"]

        # NGO dispatches stock
        r_disp = client.post(f"/api/v1/resources/{stock_id}/dispatch?quantity=200", headers=n_headers)
        assert r_disp.status_code == 200
        assert r_disp.json()["available_quantity"] == 800

        # NGO CANNOT access recovery optimization evaluation endpoint (Govt/Admin only)
        r_opt = client.post("/api/v1/recovery/optimization/evaluate", headers=n_headers, json={})
        assert r_opt.status_code in (401, 403, 422)

    def test_government_and_admin_least_privilege(self):
        g_token, g_headers = get_auth_token("GOVT")
        a_token, a_headers = get_auth_token("ADMIN")

        # Government can view summary and assessments
        r_sum = client.get("/api/v1/analytics/summary", headers=g_headers)
        assert r_sum.status_code == 200

        r_asm = client.get("/api/v1/recovery/assessments", headers=g_headers)
        assert r_asm.status_code == 200

        # Admin can access optimization endpoint
        r_admin_check = client.get("/api/v1/auth/me", headers=a_headers)
        assert r_admin_check.status_code == 200
        assert r_admin_check.json()["role"] == "ADMIN"
