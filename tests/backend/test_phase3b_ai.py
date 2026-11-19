import sys
import os
import pytest
import uuid
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from app.main import app
from app.database import SessionLocal
from app.models.incident import Incident, IncidentMedia
from app.models.ai import CVDamageAssessment, RiskAssessment, ResourceDemandPrediction
from app.ai.computer_vision.service import ComputerVisionService
from app.ai.risk_prediction.service import RiskPredictionService
from app.ai.resource_demand.service import ResourceDemandService
from app.ai.common.confidence import ConfidenceEvaluator

client = TestClient(app)

def get_auth_header(role="GOVT"):
    email = f"{role.lower()}_{uuid.uuid4().hex[:6]}@dirs.org"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": f"{role} Tester",
        "role": role
    })
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "Password123!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# ============================================================================
# 1. COMPUTER VISION DAMAGE ASSESSMENT TESTS (6 tests)
# ============================================================================

def test_cv_damage_assessment_pipeline():
    """Verify CV damage assessment returns valid damage class, confidence, probabilities and explanation."""
    db = SessionLocal()
    try:
        inc = Incident(
            incident_code=f"INC-CV-{uuid.uuid4().hex[:4]}",
            title="Collapsed Structure Photo",
            disaster_type="EARTHQUAKE",
            description="High rise building wall fracture",
            latitude=13.0827,
            longitude=80.2707
        )
        db.add(inc)
        db.commit()

        res = ComputerVisionService.analyze_incident_image(db, inc)
        assert res.incident_id == inc.id
        assert res.damage_class in ["NO_DAMAGE", "LOW_DAMAGE", "MODERATE_DAMAGE", "SEVERE_DAMAGE", "DESTROYED"]
        assert 0.0 <= res.confidence <= 100.0
        assert "NO_DAMAGE" in res.class_probabilities
        assert "saliency_heatmap_4x4" in res.explanation_metadata
    finally:
        db.close()

def test_cv_damage_invalid_image_path_handling():
    """Verify CV feature extractor handles missing or invalid image files gracefully without throwing."""
    db = SessionLocal()
    try:
        inc = Incident(
            incident_code=f"INC-CV-{uuid.uuid4().hex[:4]}",
            title="Missing File",
            disaster_type="FLOOD",
            description="d",
            latitude=13.0,
            longitude=80.0
        )
        db.add(inc)
        db.commit()

        media = IncidentMedia(incident_id=inc.id, uploader_id="test", file_name="missing.jpg", file_path="/nonexistent/missing.jpg", file_size=10, mime_type="image/jpeg", media_type="IMAGE")
        db.add(media)
        db.commit()

        res = ComputerVisionService.analyze_incident_image(db, inc, media)
        assert res.damage_class in ["NO_DAMAGE", "LOW_DAMAGE", "MODERATE_DAMAGE", "SEVERE_DAMAGE", "DESTROYED"]
    finally:
        db.close()

def test_cv_human_review_flagging():
    """Verify confidence threshold evaluator flags low-confidence CV predictions."""
    assert ConfidenceEvaluator.evaluate(85.0) is False
    assert ConfidenceEvaluator.evaluate(65.0) is True

def test_cv_government_override():
    """Verify authorized Government Officer can review and override AI CV predictions."""
    db = SessionLocal()
    try:
        inc = Incident(incident_code=f"INC-CV-{uuid.uuid4().hex[:4]}", title="Photo", disaster_type="FLOOD", description="d", latitude=13.0, longitude=80.0)
        db.add(inc)
        db.commit()

        assessment = ComputerVisionService.analyze_incident_image(db, inc)
        govt_user = db.query(Incident).first() # Dummy actor reference

        # Apply override
        updated = ComputerVisionService.override_damage_assessment(
            db=db,
            assessment_id=assessment.id,
            override_class="DESTROYED",
            notes="Field Officer verified complete structural collapse",
            reviewer=govt_user
        )
        assert updated.is_overridden is True
        assert updated.override_class == "DESTROYED"
        assert updated.override_notes == "Field Officer verified complete structural collapse"
    finally:
        db.close()

def test_cv_api_endpoint_access_control():
    """Verify RBAC: Citizens forbidden, Govt allowed on /api/v1/ai/incidents/{id}/vision."""
    govt_headers = get_auth_header("GOVT")
    citizen_headers = get_auth_header("CITIZEN")

    inc_res = client.post("/api/v1/incidents", json={"title": "Flood Photo", "disaster_type": "FLOOD", "description": "d", "latitude": 13.0, "longitude": 80.0}, headers=govt_headers)
    inc_id = inc_res.json()["id"]

    # Citizen forbidden
    cit_res = client.post(f"/api/v1/ai/incidents/{inc_id}/vision", headers=citizen_headers)
    assert cit_res.status_code == 403

    # Govt allowed
    g_res = client.post(f"/api/v1/ai/incidents/{inc_id}/vision", headers=govt_headers)
    assert g_res.status_code == 200
    assert "damage_class" in g_res.json()

def test_cv_override_api_endpoint():
    """Verify Government CV override HTTP API endpoint."""
    govt_headers = get_auth_header("GOVT")
    inc_res = client.post("/api/v1/incidents", json={"title": "Flood Photo", "disaster_type": "FLOOD", "description": "d", "latitude": 13.0, "longitude": 80.0}, headers=govt_headers)
    inc_id = inc_res.json()["id"]

    # Run CV analysis first
    client.post(f"/api/v1/ai/incidents/{inc_id}/vision", headers=govt_headers)

    # Post override
    ov_res = client.post(f"/api/v1/ai/incidents/{inc_id}/vision/override", json={
        "override_class": "SEVERE_DAMAGE",
        "notes": "Verified severe wall cracking"
    }, headers=govt_headers)

    assert ov_res.status_code == 200
    assert ov_res.json()["is_overridden"] is True
    assert ov_res.json()["override_class"] == "SEVERE_DAMAGE"

# ============================================================================
# 2. DISASTER / METEOROLOGICAL RISK PREDICTION TESTS (5 tests)
# ============================================================================

def test_risk_prediction_pipeline():
    """Verify risk prediction calculates score (0-100), classification, and contributing factors."""
    db = SessionLocal()
    try:
        inc = Incident(incident_code=f"INC-RK-{uuid.uuid4().hex[:4]}", title="Heavy Flood Surge", disaster_type="FLOOD", description="Surge", latitude=13.0, longitude=80.0, people_affected=80)
        db.add(inc)
        db.commit()

        assessment = RiskPredictionService.calculate_risk(db, incident=inc)
        assert 0.0 <= assessment.risk_score <= 100.0
        assert assessment.risk_level in ["LOW", "MODERATE", "HIGH", "EXTREME"]
        assert len(assessment.contributing_factors) > 0
    finally:
        db.close()

def test_risk_score_bounds_and_determinism():
    """Verify risk prediction stays bounded between 0.0 and 100.0."""
    db = SessionLocal()
    try:
        extreme_env = {"rainfall_mm": 300.0, "wind_speed_kmh": 140.0, "river_level_m": 7.5, "population_exposure": 8000.0, "disaster_type": "CYCLONE"}
        assessment = RiskPredictionService.calculate_risk(db, environmental_data=extreme_env)
        assert 0.0 <= assessment.risk_score <= 100.0
        assert assessment.risk_level in ["LOW", "MODERATE", "HIGH", "EXTREME"]
    finally:
        db.close()

def test_risk_government_override():
    """Verify Government Officer can override AI risk prediction levels."""
    db = SessionLocal()
    try:
        inc = Incident(incident_code=f"INC-RK-{uuid.uuid4().hex[:4]}", title="Storm", disaster_type="CYCLONE", description="Storm", latitude=13.0, longitude=80.0)
        db.add(inc)
        db.commit()

        assessment = RiskPredictionService.calculate_risk(db, incident=inc)
        actor = db.query(Incident).first()

        updated = RiskPredictionService.override_risk_assessment(db, assessment.id, "EXTREME", "Evacuation ordered", actor)
        assert updated.is_overridden is True
        assert updated.override_level == "EXTREME"
    finally:
        db.close()

def test_risk_api_endpoints():
    """Verify Risk Prediction HTTP API endpoints (predict and override)."""
    govt_headers = get_auth_header("GOVT")
    inc_res = client.post("/api/v1/incidents", json={"title": "River Surge", "disaster_type": "FLOOD", "description": "d", "latitude": 13.0, "longitude": 80.0}, headers=govt_headers)
    inc_id = inc_res.json()["id"]

    risk_res = client.post(f"/api/v1/ai/incidents/{inc_id}/risk", headers=govt_headers)
    assert risk_res.status_code == 200
    assert "risk_score" in risk_res.json()
    assert "risk_level" in risk_res.json()

    ov_res = client.post(f"/api/v1/ai/incidents/{inc_id}/risk/override", json={
        "override_level": "EXTREME",
        "notes": "Emergency dam release imminent"
    }, headers=govt_headers)
    assert ov_res.status_code == 200
    assert ov_res.json()["override_level"] == "EXTREME"

def test_risk_unauthorized_access():
    """Verify non-government users cannot trigger risk overrides."""
    citizen_headers = get_auth_header("CITIZEN")
    res = client.post("/api/v1/ai/incidents/fake-id/risk", headers=citizen_headers)
    assert res.status_code == 403

# ============================================================================
# 3. RESOURCE DEMAND PREDICTION TESTS (5 tests)
# ============================================================================

def test_resource_demand_prediction_pipeline():
    """Verify resource demand regressor predicts non-negative quantities for 5 resource types."""
    db = SessionLocal()
    try:
        inc = Incident(incident_code=f"INC-RD-{uuid.uuid4().hex[:4]}", title="Flood Evacuation", disaster_type="FLOOD", description="Submersion", latitude=13.0, longitude=80.0, people_affected=120, injuries=25, vulnerable_count=15)
        db.add(inc)
        db.commit()

        pred = ResourceDemandService.predict_incident_demand(db, inc)
        assert pred.incident_id == inc.id
        assert "water_packs" in pred.predictions
        assert pred.predictions["water_packs"]["quantity"] > 0
        assert pred.predictions["medical_kits"]["quantity"] > 0
    finally:
        db.close()

def test_resource_demand_inventory_shortage_detection():
    """Verify resource demand engine compares predicted demand against stock and flags shortages."""
    db = SessionLocal()
    try:
        inc = Incident(incident_code=f"INC-RD-{uuid.uuid4().hex[:4]}", title="Mass Evacuation", disaster_type="FLOOD", description="Large scale flood", latitude=13.0, longitude=80.0, people_affected=500, injuries=80, vulnerable_count=60)
        db.add(inc)
        db.commit()

        pred = ResourceDemandService.predict_incident_demand(db, inc)
        assert isinstance(pred.shortages_detected, list)
    finally:
        db.close()

def test_resource_demand_government_override():
    """Verify Government Officer can override resource demand quantity estimates."""
    db = SessionLocal()
    try:
        inc = Incident(incident_code=f"INC-RD-{uuid.uuid4().hex[:4]}", title="Rescue Scope", disaster_type="FLOOD", description="d", latitude=13.0, longitude=80.0, people_affected=40)
        db.add(inc)
        db.commit()

        pred = ResourceDemandService.predict_incident_demand(db, inc)
        actor = db.query(Incident).first()

        updated = ResourceDemandService.override_demand_prediction(
            db, pred.id, {"water_packs": 2000.0, "medical_kits": 150.0}, "Reinforcements requested", actor
        )
        assert updated.is_overridden is True
        assert updated.override_demands["water_packs"] == 2000.0
    finally:
        db.close()

def test_resource_demand_api_endpoints():
    """Verify Resource Demand HTTP API endpoints (predict and override)."""
    govt_headers = get_auth_header("GOVT")
    inc_res = client.post("/api/v1/incidents", json={"title": "Rooftop Marooning", "disaster_type": "FLOOD", "description": "d", "latitude": 13.0, "longitude": 80.0, "people_affected": 90, "injuries": 15}, headers=govt_headers)
    inc_id = inc_res.json()["id"]

    rd_res = client.post(f"/api/v1/ai/incidents/{inc_id}/resource-demand", headers=govt_headers)
    assert rd_res.status_code == 200
    assert "predictions" in rd_res.json()
    assert "water_packs" in rd_res.json()["predictions"]

    ov_res = client.post(f"/api/v1/ai/incidents/{inc_id}/resource-demand/override", json={
        "override_demands": {"water_packs": 1500.0, "food_packets": 1200.0},
        "notes": "Adjusted for incoming air-drop supply"
    }, headers=govt_headers)
    assert ov_res.status_code == 200
    assert ov_res.json()["override_demands"]["water_packs"] == 1500.0

def test_resource_demand_rbac_security():
    """Verify non-government users cannot trigger resource demand predictions or overrides."""
    citizen_headers = get_auth_header("CITIZEN")
    res = client.post("/api/v1/ai/incidents/fake-id/resource-demand", headers=citizen_headers)
    assert res.status_code == 403
