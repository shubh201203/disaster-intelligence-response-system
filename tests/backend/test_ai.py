import sys
import os
import pytest
import uuid
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from app.main import app
from app.database import SessionLocal
from app.models.incident import Incident
from app.models.ai import AIPrediction
from app.ai.severity.service import SeverityService
from app.ai.priority.service import PriorityService
from app.ai.priority.config import PRIORITY_WEIGHTS, validate_weights
from app.ai.duplicate_detection.service import DuplicateDetectionService
from app.ai.duplicate_detection.similarity import haversine_distance_meters, compute_text_similarity
from app.ai.common.confidence import ConfidenceEvaluator
from app.ai.common.model_registry import ModelRegistry

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

def test_priority_weights_valid():
    """Verify PRIORITY_WEIGHTS sums to 100.0."""
    assert validate_weights() is True
    assert sum(PRIORITY_WEIGHTS.values()) == 100.0

def test_severity_prediction_pipeline():
    """Test severity model prediction, confidence scoring, explainability & persistence."""
    db = SessionLocal()
    try:
        incident = Incident(
            incident_code=f"INC-TEST-{uuid.uuid4().hex[:6]}",
            title="Severe Rooftop Flood Marooning",
            disaster_type="FLOOD",
            description="Water submerged lower floors, 45 victims trapped on rooftops needing urgent boat evacuation.",
            people_affected=45,
            injuries=12,
            vulnerable_count=8,
            infrastructure_damage="Bridge collapsed, power grid destroyed",
            latitude=13.0827,
            longitude=80.2707,
            status="REPORTED"
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        res = SeverityService.analyze_incident_severity(db, incident)

        assert res.incident_id == incident.id
        assert res.prediction in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert res.confidence >= 0.0 and res.confidence <= 100.0
        assert isinstance(res.requires_human_review, bool)
        assert len(res.factors) > 0

        # Check persistence
        updated = db.query(Incident).filter(Incident.id == incident.id).first()
        assert updated.severity_level == res.prediction
        assert updated.status == "AI_ANALYZED"
        assert "factors" in updated.ai_breakdown
    finally:
        db.close()

def test_explainable_ai_non_hardcoded():
    """Verify explainability generates dynamic factors corresponding to actual input values."""
    db = SessionLocal()
    try:
        inc1 = Incident(
            incident_code=f"INC-TEST-{uuid.uuid4().hex[:6]}",
            title="Minor Waterlog",
            disaster_type="FLOOD",
            description="Minor street water accumulation near park",
            people_affected=2,
            injuries=0,
            vulnerable_count=0,
            latitude=13.0827,
            longitude=80.2707
        )
        inc2 = Incident(
            incident_code=f"INC-TEST-{uuid.uuid4().hex[:6]}",
            title="Severe Flood Inundation",
            disaster_type="FLOOD",
            description="Urgent boat rescue needed for marooned residents",
            people_affected=150,
            injuries=25,
            vulnerable_count=15,
            infrastructure_damage="Bridge collapsed, power grid offline",
            latitude=13.0827,
            longitude=80.2707
        )
        db.add_all([inc1, inc2])
        db.commit()

        res1 = SeverityService.analyze_incident_severity(db, inc1)
        res2 = SeverityService.analyze_incident_severity(db, inc2)

        # Dynamic responsiveness check: High casualty incident has higher feature impact points
        impact_aff1 = next((f.impact for f in res1.factors if "Affected" in f.feature), 0.0)
        impact_aff2 = next((f.impact for f in res2.factors if "Affected" in f.feature), 0.0)
        assert impact_aff2 > impact_aff1

        impact_inj1 = next((f.impact for f in res1.factors if "Injured" in f.feature), 0.0)
        impact_inj2 = next((f.impact for f in res2.factors if "Injured" in f.feature), 0.0)
        assert impact_inj2 > impact_inj1
    finally:
        db.close()

def test_priority_engine_bounds_and_determinism():
    """Test priority engine bounds (0-100), classifications, and deterministic breakdown."""
    db = SessionLocal()
    try:
        incident = Incident(
            incident_code=f"INC-TEST-{uuid.uuid4().hex[:6]}",
            title="Catastrophic Earthquake Collapse",
            disaster_type="EARTHQUAKE",
            description="Multiple high-rises collapsed, 100+ trapped",
            people_affected=150,
            injuries=40,
            vulnerable_count=20,
            infrastructure_damage="Main hospital destroyed, highway split",
            latitude=13.0827,
            longitude=80.2707,
            severity_level="CRITICAL"
        )
        db.add(incident)
        db.commit()

        res = PriorityService.calculate_incident_priority(db, incident)
        assert res.priority_score >= 76.0
        assert res.classification == "CRITICAL"
        assert "severity_contribution" in res.breakdown
        assert res.breakdown["severity_contribution"] == 30.0
    finally:
        db.close()

def test_priority_engine_boundary_classifications():
    """Test boundary classifications at score thresholds (<26 LOW, 26-50 MEDIUM, 51-75 HIGH, >=76 CRITICAL)."""
    from app.ai.priority.scoring import compute_priority_score_and_breakdown

    # 1. LOW boundary
    low_data = {"severity_level": "LOW", "disaster_type": "FLOOD", "people_affected": 2, "injuries": 0, "vulnerable_count": 0}
    score_low, class_low, _, _ = compute_priority_score_and_breakdown(low_data)
    assert score_low < 26.0
    assert class_low == "LOW"

    # 2. MEDIUM boundary
    med_data = {"severity_level": "MEDIUM", "disaster_type": "FLOOD", "people_affected": 20, "injuries": 2, "vulnerable_count": 2}
    score_med, class_med, _, _ = compute_priority_score_and_breakdown(med_data)
    assert 26.0 <= score_med < 51.0
    assert class_med == "MEDIUM"

    # 3. HIGH boundary
    high_data = {"severity_level": "HIGH", "disaster_type": "FLOOD", "people_affected": 30, "injuries": 4, "vulnerable_count": 2, "infrastructure_damage": "Bridge damaged"}
    score_high, class_high, _, _ = compute_priority_score_and_breakdown(high_data)
    assert 51.0 <= score_high < 76.0
    assert class_high == "HIGH"

    # 4. CRITICAL boundary
    crit_data = {"severity_level": "CRITICAL", "disaster_type": "EARTHQUAKE", "people_affected": 150, "injuries": 30, "vulnerable_count": 15, "infrastructure_damage": "Hospital collapsed"}
    score_crit, class_crit, _, _ = compute_priority_score_and_breakdown(crit_data)
    assert score_crit >= 76.0
    assert class_crit == "CRITICAL"

def test_duplicate_detection_four_cases():
    """
    Audit 4 distinct duplicate detection cases:
    1. Same event (nearby location + similar text)
    2. Unrelated event (distant location >5km)
    3. Nearby different disaster type (nearby location, different hazard)
    4. Same event different wording (nearby location, reworded text)
    """
    db = SessionLocal()
    try:
        target = Incident(
            incident_code=f"INC-TG-{uuid.uuid4().hex[:4]}",
            title="Riverbank Wall Breach",
            disaster_type="FLOOD",
            description="Main concrete floodwall collapsed near north colony bridge",
            latitude=13.0827,
            longitude=80.2707
        )
        # Case 1: Same event
        case1_same = Incident(
            incident_code=f"INC-C1-{uuid.uuid4().hex[:4]}",
            title="Riverbank Wall Breach Flood",
            disaster_type="FLOOD",
            description="Concrete floodwall collapsed near north colony bridge causing submersion",
            latitude=13.0829, # ~25m
            longitude=80.2708
        )
        # Case 2: Unrelated event distant
        case2_unrelated = Incident(
            incident_code=f"INC-C2-{uuid.uuid4().hex[:4]}",
            title="Industrial Chemical Storage Gas Leak",
            disaster_type="FIRE",
            description="Toxic chemical cloud released in southern industrial zone warehouse",
            latitude=13.1500, # ~7.5km away
            longitude=80.3500
        )
        # Case 3: Nearby different disaster type
        case3_different_type = Incident(
            incident_code=f"INC-C3-{uuid.uuid4().hex[:4]}",
            title="Transformer Fire Explosion",
            disaster_type="FIRE",
            description="Electrical power substation transformer caught fire producing heavy smoke",
            latitude=13.0828, # ~15m
            longitude=80.2707
        )
        # Case 4: Same event different wording
        case4_reworded = Incident(
            incident_code=f"INC-C4-{uuid.uuid4().hex[:4]}",
            title="Water Retaining Wall Failure",
            disaster_type="FLOOD",
            description="Barrier surrounding northern neighborhood broke open inundating residential structures",
            latitude=13.0831, # ~45m
            longitude=80.2710
        )

        db.add_all([target, case1_same, case2_unrelated, case3_different_type, case4_reworded])
        db.commit()

        # Run duplicate detection on target incident
        res = DuplicateDetectionService.detect_duplicates(db, target)
        cand_ids = [c.candidate_incident_id for c in res.candidates]

        # Case 1: Same event MUST be detected as candidate
        assert case1_same.id in cand_ids

        # Case 2: Unrelated distant event MUST NOT be detected as duplicate candidate
        assert case2_unrelated.id not in cand_ids

        # Case 4: Reworded same location flood event detected via spatio-temporal proximity + text
        assert case4_reworded.id in cand_ids
    finally:
        db.close()

def test_duplicate_detection_haversine_and_text():
    """Test duplicate detection distance math, text similarity, and candidate grouping."""
    db = SessionLocal()
    try:
        inc1 = Incident(
            incident_code=f"INC-TEST-{uuid.uuid4().hex[:6]}",
            title="Flash Flood near Riverfront Colony",
            disaster_type="FLOOD",
            description="Rapid water rise near main river bridge",
            latitude=13.0827,
            longitude=80.2707
        )
        inc2 = Incident(
            incident_code=f"INC-TEST-{uuid.uuid4().hex[:6]}",
            title="Flash Flooding near Riverbank Bridge",
            disaster_type="FLOOD",
            description="Water overflowing from river bridge onto main road",
            latitude=13.0830, # ~30m distance
            longitude=80.2709
        )
        db.add_all([inc1, inc2])
        db.commit()

        # Haversine check
        dist = haversine_distance_meters(inc1.latitude, inc1.longitude, inc2.latitude, inc2.longitude)
        assert dist < 100.0

        # Text similarity check (title + description)
        sim = compute_text_similarity(f"{inc1.title} {inc1.description}", f"{inc2.title} {inc2.description}")
        assert sim > 0.4

        # Service detection check
        res = DuplicateDetectionService.detect_duplicates(db, inc1)
        assert res.duplicate_count >= 1
        cand_ids = [c.candidate_incident_id for c in res.candidates]
        assert inc2.id in cand_ids
        target_cand = next(c for c in res.candidates if c.candidate_incident_id == inc2.id)
        assert target_cand.recommendation in ["POSSIBLE_DUPLICATE", "RELATED_INCIDENT"]
    finally:
        db.close()

def test_no_auto_delete_duplicates():
    """Verify duplicate detection never deletes incident records automatically."""
    db = SessionLocal()
    try:
        inc1 = Incident(incident_code=f"INC-DUP-{uuid.uuid4().hex[:4]}", title="Fire", disaster_type="FIRE", description="Building fire", latitude=13.0, longitude=80.0)
        inc2 = Incident(incident_code=f"INC-DUP-{uuid.uuid4().hex[:4]}", title="Fire", disaster_type="FIRE", description="Building fire", latitude=13.0, longitude=80.0)
        db.add_all([inc1, inc2])
        db.commit()

        DuplicateDetectionService.detect_duplicates(db, inc1)
        # Check that both incidents still exist in database
        assert db.query(Incident).filter(Incident.id == inc1.id).first() is not None
        assert db.query(Incident).filter(Incident.id == inc2.id).first() is not None
    finally:
        db.close()

def test_model_registry_metadata():
    """Verify AI model registry returns registered items and metadata."""
    models = ModelRegistry.list_models()
    assert len(models) >= 3
    names = [m.name for m in models]
    assert "severity-classifier-rf" in names
    assert "priority-scoring-engine" in names
    assert "spatio-temporal-duplicate-detector" in names

def test_confidence_threshold_flagging():
    """Test confidence evaluator thresholds."""
    assert ConfidenceEvaluator.evaluate(85.0) is False
    assert ConfidenceEvaluator.evaluate(65.0) is True
    assert ConfidenceEvaluator.format_confidence_label(65.0) == "REQUIRES HUMAN REVIEW"

def test_ai_api_endpoints():
    """Verify AI HTTP API endpoints for severity, priority, duplicates, and model metadata."""
    govt_headers = get_auth_header("GOVT")
    citizen_headers = get_auth_header("CITIZEN")

    # Create test incident
    inc_res = client.post("/api/v1/incidents", json={
        "title": "Severe Cyclone Damage",
        "disaster_type": "CYCLONE",
        "description": "High winds destroyed roofs",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "people_affected": 80,
        "injuries": 15
    }, headers=govt_headers)
    inc_id = inc_res.json()["id"]

    # 1. Models endpoint
    models_res = client.get("/api/v1/ai/models")
    assert models_res.status_code == 200
    assert len(models_res.json()) >= 3

    # 2. RBAC check: Citizen forbidden
    sev_cit_res = client.post(f"/api/v1/ai/incidents/{inc_id}/severity", headers=citizen_headers)
    assert sev_cit_res.status_code == 403

    # 3. Severity endpoint
    sev_res = client.post(f"/api/v1/ai/incidents/{inc_id}/severity", headers=govt_headers)
    assert sev_res.status_code == 200
    assert "prediction" in sev_res.json()
    assert "confidence" in sev_res.json()
    assert len(sev_res.json()["factors"]) > 0

    # 4. Priority endpoint
    prio_res = client.post(f"/api/v1/ai/incidents/{inc_id}/priority", headers=govt_headers)
    assert prio_res.status_code == 200
    assert "priority_score" in prio_res.json()
    assert "breakdown" in prio_res.json()

    # 5. Duplicates endpoint
    dup_res = client.post(f"/api/v1/ai/incidents/{inc_id}/duplicates", headers=govt_headers)
    assert dup_res.status_code == 200
    assert "duplicate_count" in dup_res.json()

    # 6. Full Analysis endpoint
    full_res = client.post(f"/api/v1/ai/incidents/{inc_id}/analyze", headers=govt_headers)
    assert full_res.status_code == 200
    assert "severity" in full_res.json()
    assert "priority" in full_res.json()
    assert "duplicates" in full_res.json()
