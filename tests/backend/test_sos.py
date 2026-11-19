import sys
import os
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth_header(role="CITIZEN"):
    email = f"{role.lower()}_{uuid.uuid4().hex[:6]}@dirs.org"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Pass!", "full_name": f"{role} Tester", "role": role})
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "Pass!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_sos_distress_trigger():
    headers = get_auth_header("CITIZEN")
    res = client.post("/api/v1/incidents/sos?lat=13.0827&lng=80.2707&description=Trapped", headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["priority_level"] == "CRITICAL"
    assert data["priority_score"] == 99.0

def test_sos_creates_valid_incident_code():
    headers = get_auth_header("CITIZEN")
    res = client.post("/api/v1/incidents/sos?lat=13.0&lng=80.0", headers=headers)
    assert res.status_code == 201
    assert res.json()["incident_code"].startswith("INC-")

def test_sos_requires_authentication():
    res = client.post("/api/v1/incidents/sos?lat=13.0&lng=80.0")
    assert res.status_code == 401
