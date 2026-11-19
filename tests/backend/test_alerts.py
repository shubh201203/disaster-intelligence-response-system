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

def test_government_alert_creation():
    headers = get_auth("GOVT")
    res = client.post("/api/v1/alerts", json={
        "title": "Evacuation Warning",
        "message": "Move to higher ground",
        "alert_type": "EVACUATION",
        "target_zone_lat": 13.08,
        "target_zone_lng": 80.27,
        "radius_km": 5.0
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["alert_type"] == "EVACUATION"

def test_alerts_list():
    res = client.get("/api/v1/alerts")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_citizen_cannot_create_alert():
    citizen_headers = get_auth("CITIZEN")
    res = client.post("/api/v1/alerts", json={
        "title": "Fake Alert",
        "message": "Fake",
        "alert_type": "WARNING"
    }, headers=citizen_headers)
    assert res.status_code == 403
