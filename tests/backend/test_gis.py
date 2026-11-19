import sys
import os
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.services.gis_service import haversine_distance_km

client = TestClient(app)

def test_haversine_distance_calculation():
    # Distance between Chennai (13.0827, 80.2707) and nearby point (~2.5km)
    dist = haversine_distance_km(13.0827, 80.2707, 13.0850, 80.2900)
    assert 1.5 < dist < 3.5

def test_nearby_incidents_spatial_query():
    res = client.get("/api/v1/incidents/nearby?lat=13.0827&lng=80.2707&radius_km=10.0")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_nearby_shelters_spatial_query():
    res = client.get("/api/v1/shelters/nearby?lat=13.0827&lng=80.2707&radius_km=15.0")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
