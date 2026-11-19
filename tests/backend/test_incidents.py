import sys
import os
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth_header(role="CITIZEN"):
    email = f"{role.lower()}_{uuid.uuid4().hex[:6]}@dirs.org"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": f"{role} Tester",
        "role": role
    })
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "Password123!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_incident_creation():
    headers = get_auth_header("CITIZEN")
    res = client.post("/api/v1/incidents", json={
        "title": "Flash flood near market",
        "disaster_type": "FLOOD",
        "description": "High water levels",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "people_affected": 30
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["incident_code"].startswith("INC-")

def test_incident_list_query():
    res = client.get("/api/v1/incidents")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_valid_incident_status_transition():
    govt_headers = get_auth_header("GOVT")
    inc = client.post("/api/v1/incidents", json={
        "title": "Fire outbreak", "disaster_type": "FIRE", "description": "Smoke", "latitude": 13.0, "longitude": 80.0
    }, headers=govt_headers).json()

    res = client.patch(f"/api/v1/incidents/{inc['id']}/status?target_status=VERIFIED", headers=govt_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "VERIFIED"

def test_invalid_incident_status_transition_blocked():
    govt_headers = get_auth_header("GOVT")
    inc = client.post("/api/v1/incidents", json={
        "title": "Landslide", "disaster_type": "LANDSLIDE", "description": "Debris", "latitude": 13.0, "longitude": 80.0
    }, headers=govt_headers).json()

    # REPORTED -> RESOLVED directly is invalid
    res = client.patch(f"/api/v1/incidents/{inc['id']}/status?target_status=RESOLVED", headers=govt_headers)
    assert res.status_code == 400
    assert "Invalid incident state transition" in res.json()["detail"]

def test_government_incident_verification():
    govt_headers = get_auth_header("GOVT")
    inc = client.post("/api/v1/incidents", json={
        "title": "Verification test", "disaster_type": "FLOOD", "description": "Water", "latitude": 13.0, "longitude": 80.0
    }, headers=govt_headers).json()

    res = client.put(f"/api/v1/incidents/{inc['id']}/verify", json={"action": "VERIFY", "notes": "Approved"}, headers=govt_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "VERIFIED"

def test_incident_manual_duplicate_merge():
    govt_headers = get_auth_header("GOVT")
    inc1 = client.post("/api/v1/incidents", json={"title": "Main report", "disaster_type": "FLOOD", "description": "Water", "latitude": 13.0, "longitude": 80.0}, headers=govt_headers).json()
    inc2 = client.post("/api/v1/incidents", json={"title": "Duplicate report", "disaster_type": "FLOOD", "description": "Same water", "latitude": 13.0, "longitude": 80.0}, headers=govt_headers).json()

    res = client.post(f"/api/v1/incidents/{inc1['id']}/merge", json={"duplicate_incident_ids": [inc2['id']]}, headers=govt_headers)
    assert res.status_code == 200
    assert "cluster_code" in res.json()
