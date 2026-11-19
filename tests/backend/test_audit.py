import sys
import os
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth(role="GOVT"):
    email = f"{role.lower()}_{uuid.uuid4().hex[:6]}@dirs.org"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Pass!", "full_name": f"{role} Tester", "role": role})
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "Pass!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_audit_log_created_on_incident_creation():
    headers = get_auth("CITIZEN")
    res = client.post("/api/v1/incidents", json={
        "title": "Audit log test incident",
        "disaster_type": "FLOOD",
        "description": "Test",
        "latitude": 13.0,
        "longitude": 80.0
    }, headers=headers)
    assert res.status_code == 201
    # Incident creation automatically triggers AuditService.log_action

def test_analytics_summary_endpoint():
    res = client.get("/api/v1/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "active_incidents" in data
    assert "people_affected" in data
    assert "shelter_occupancy_rate" in data
