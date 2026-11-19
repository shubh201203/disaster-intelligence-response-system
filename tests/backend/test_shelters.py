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

def test_shelter_creation():
    headers = get_auth("GOVT")
    res = client.post("/api/v1/shelters", json={
        "name": "Central Safe Haven S-200",
        "address": "Sector 5",
        "total_capacity": 400,
        "current_occupancy": 50,
        "latitude": 13.0850,
        "longitude": 80.2750
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["name"] == "Central Safe Haven S-200"

def test_shelters_list():
    res = client.get("/api/v1/shelters")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_nearby_shelter_suitability_ranking():
    res = client.get("/api/v1/shelters/nearby?lat=13.0827&lng=80.2707&radius_km=25")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

def test_update_shelter_occupancy():
    headers = get_auth("GOVT")
    sh = client.post("/api/v1/shelters", json={
        "name": "Update Test Shelter", "address": "S", "total_capacity": 100, "current_occupancy": 10, "latitude": 13.0, "longitude": 80.0
    }, headers=headers).json()

    res = client.patch(f"/api/v1/shelters/{sh['id']}?occupancy=65", headers=headers)
    assert res.status_code == 200
    assert res.json()["current_occupancy"] == 65
