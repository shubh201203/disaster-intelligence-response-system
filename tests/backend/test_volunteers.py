import sys
import os
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth(role="VOLUNTEER"):
    email = f"{role.lower()}_{uuid.uuid4().hex[:6]}@dirs.org"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Pass!", "full_name": f"{role} Tester", "role": role})
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "Pass!"}).json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}

def test_volunteer_me_endpoint():
    token, headers = get_auth("VOLUNTEER")
    res = client.get("/api/v1/volunteers/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["role"] == "VOLUNTEER"

def test_volunteer_recommended_ranking():
    _, govt_headers = get_auth("GOVT")
    inc = client.post("/api/v1/incidents", json={"title": "Test", "disaster_type": "FLOOD", "description": "d", "latitude": 13.0, "longitude": 80.0}, headers=govt_headers).json()

    res = client.get(f"/api/v1/volunteers/recommended/{inc['id']}", headers=govt_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_rescue_task_assignment():
    _, govt_headers = get_auth("GOVT")
    vol_token, _ = get_auth("VOLUNTEER")
    vol_user = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {vol_token}"}).json()
    inc = client.post("/api/v1/incidents", json={"title": "Test", "disaster_type": "FLOOD", "description": "d", "latitude": 13.0, "longitude": 80.0}, headers=govt_headers).json()

    res = client.post(f"/api/v1/volunteers/assign?incident_id={inc['id']}&volunteer_id={vol_user['id']}", headers=govt_headers)
    assert res.status_code == 201
    assert "task_id" in res.json()

def test_task_state_transition_sequence():
    _, govt_headers = get_auth("GOVT")
    vol_token, vol_headers = get_auth("VOLUNTEER")
    vol_user = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {vol_token}"}).json()
    inc = client.post("/api/v1/incidents", json={"title": "Test", "disaster_type": "FLOOD", "description": "d", "latitude": 13.0, "longitude": 80.0}, headers=govt_headers).json()

    task_id = client.post(f"/api/v1/volunteers/assign?incident_id={inc['id']}&volunteer_id={vol_user['id']}", headers=govt_headers).json()["task_id"]

    # ASSIGNED -> ACCEPTED
    res1 = client.patch(f"/api/v1/volunteers/tasks/{task_id}/status?target_status=ACCEPTED", headers=vol_headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "ACCEPTED"

    # ACCEPTED -> EN_ROUTE
    res2 = client.patch(f"/api/v1/volunteers/tasks/{task_id}/status?target_status=EN_ROUTE", headers=vol_headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "EN_ROUTE"

def test_unauthorized_task_transition_blocked():
    _, govt_headers = get_auth("GOVT")
    vol1_token, _ = get_auth("VOLUNTEER")
    _, vol2_headers = get_auth("VOLUNTEER")
    vol1_user = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {vol1_token}"}).json()
    inc = client.post("/api/v1/incidents", json={"title": "Test", "disaster_type": "FLOOD", "description": "d", "latitude": 13.0, "longitude": 80.0}, headers=govt_headers).json()
    task_id = client.post(f"/api/v1/volunteers/assign?incident_id={inc['id']}&volunteer_id={vol1_user['id']}", headers=govt_headers).json()["task_id"]

    # Vol 2 tries to update Vol 1's task
    res = client.patch(f"/api/v1/volunteers/tasks/{task_id}/status?target_status=ACCEPTED", headers=vol2_headers)
    assert res.status_code == 400
    assert "Volunteers can only update their own assigned" in res.json()["detail"]
