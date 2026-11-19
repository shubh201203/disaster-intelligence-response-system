import sys
import os
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth(role="NGO"):
    email = f"{role.lower()}_{uuid.uuid4().hex[:6]}@dirs.org"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Pass!", "full_name": f"{role} Tester", "role": role})
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "Pass!"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_resource_creation():
    headers = get_auth("NGO")
    res = client.post("/api/v1/resources", json={
        "owner_type": "NGO",
        "category": "FOOD",
        "resource_name": "Emergency Ration Packs",
        "total_quantity": 1000,
        "unit": "packets",
        "location_lat": 13.08,
        "location_lng": 80.27
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["available_quantity"] == 1000

def test_resource_list():
    res = client.get("/api/v1/resources")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_resource_dispatch_success():
    headers = get_auth("NGO")
    stock = client.post("/api/v1/resources", json={
        "owner_type": "NGO", "category": "WATER", "resource_name": "Water Bottles", "total_quantity": 500, "unit": "bottles"
    }, headers=headers).json()

    res = client.post(f"/api/v1/resources/{stock['id']}/dispatch?quantity=150", headers=headers)
    assert res.status_code == 200
    assert res.json()["available_quantity"] == 350

def test_resource_dispatch_insufficient_stock_fails():
    headers = get_auth("NGO")
    stock = client.post("/api/v1/resources", json={
        "owner_type": "NGO", "category": "MEDICINE", "resource_name": "Kits", "total_quantity": 50, "unit": "kits"
    }, headers=headers).json()

    # Attempt to dispatch 200 when only 50 available
    res = client.post(f"/api/v1/resources/{stock['id']}/dispatch?quantity=200", headers=headers)
    assert res.status_code == 400
    assert "Insufficient stock available" in res.json()["detail"]

def test_resource_request_submission():
    headers = get_auth("CITIZEN")
    res = client.post("/api/v1/resources/request", json={
        "incident_id": str(uuid.uuid4()),
        "category": "FOOD",
        "quantity_requested": 100,
        "priority": "HIGH"
    }, headers=headers)
    assert res.status_code == 201
    assert "request_id" in res.json()
