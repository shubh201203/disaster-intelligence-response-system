import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.resource import Resource

client = TestClient(app)

def get_auth(role="GOVT"):
    email = f"{role.lower()}_{uuid.uuid4().hex[:6]}@dirs.gov.in"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": f"{role} Acceptance Tester",
        "role": role
    })
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "Password123!"}).json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}

# ==============================================================================
# DEF-03: GIS Spatial KNN Query Contract & Feature Collection
# ==============================================================================
def test_batch2_def03_knn_nearest_shelter():
    _, headers = get_auth("GOVT")
    payload = {
        "query_type": "NEAREST_SHELTER",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "radius_km": 15.0
    }
    res = client.post("/api/v1/gis/spatial-query", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["query_type"] == "NEAREST_SHELTER"
    assert "features" in data
    assert len(data["features"]) > 0
    first_feat = data["features"][0]
    assert first_feat["type"] == "Feature"
    assert first_feat["geometry"]["type"] == "Point"
    assert "distance_km" in first_feat["properties"]
    assert "shelter_id" in first_feat["properties"]

def test_batch2_def03_knn_with_target_layer_mapping():
    payload = {
        "query_type": "KNN",
        "target_layer": "depot",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "k_nearest": 3
    }
    res = client.post("/api/v1/gis/spatial-query", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["query_type"] == "NEAREST_DEPOT"
    assert len(data["features"]) > 0
    assert "depot_id" in data["features"][0]["properties"]

# ==============================================================================
# DEF-04: Scenario Laboratory Scenario Submission & Singular Delta Response
# ==============================================================================
def test_batch2_def04_simulation_returns_scenario_delta():
    _, headers = get_auth("GOVT")

    # Create scenario in test database
    create_res = client.post("/api/v1/simulation/scenarios", json={
        "name": "Mass Casualty Flood Surge",
        "description": "Simulated surge in evacuees",
        "hazard_type": "FLOOD",
        "severity_multiplier": 1.5,
        "affected_area_multiplier": 1.2,
        "new_incidents": [{"id": "inc-surge-1", "latitude": 13.0827, "longitude": 80.2707, "evacuees": 150}],
        "seed": 42
    }, headers=headers)
    assert create_res.status_code == 201
    scen_id = create_res.json()["id"]

    payload = {
        "scenario_id": scen_id,
        "base_workload": "DIRS-GIS-10",
        "seed": 42
    }
    res = client.post("/api/v1/simulation/run", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["scenario_id"] == scen_id
    assert data["scenario_name"] == "Mass Casualty Flood Surge"
    assert "delta" in data, "Backend contract returns singular 'delta'"
    delta = data["delta"]
    assert isinstance(delta, dict)
    assert "shelter" in delta
    assert "resources" in delta
    assert "vehicles" in delta
    assert "network" in delta
    assert delta["shelter"]["delta_sheltered"] >= 0
    assert len(data.get("intelligence_observations", [])) > 0

# ==============================================================================
# DEF-05: Multi-Scenario Comparison Payload & Computed Differences
# ==============================================================================
def test_batch2_def05_multi_scenario_compare_with_scenario_ids():
    _, headers = get_auth("GOVT")

    # Create two scenarios in test database
    scen1 = client.post("/api/v1/simulation/scenarios", json={
        "name": "Compare Scenario A",
        "hazard_type": "FLOOD",
        "severity_multiplier": 1.2,
        "affected_area_multiplier": 1.0,
        "new_incidents": [{"id": "inc-c1", "latitude": 13.08, "longitude": 80.27, "evacuees": 100}],
        "seed": 42
    }, headers=headers).json()

    scen2 = client.post("/api/v1/simulation/scenarios", json={
        "name": "Compare Scenario B",
        "hazard_type": "FLOOD",
        "severity_multiplier": 1.4,
        "affected_area_multiplier": 1.1,
        "new_incidents": [{"id": "inc-c2", "latitude": 13.09, "longitude": 80.28, "evacuees": 80}],
        "seed": 43
    }, headers=headers).json()

    payload = {
        "scenario_ids": [scen1["id"], scen2["id"]],
        "base_workload": "DIRS-GIS-10",
        "seed": 42
    }
    res = client.post("/api/v1/simulation/compare", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "base_metrics" in data
    assert "comparisons" in data
    assert len(data["comparisons"]) == 2
    for comp in data["comparisons"]:
        assert "delta_unmet_evacuation" in comp
        assert "delta_unmet_resources" in comp
        assert "delta_unrouted_shipments" in comp
        assert comp["scenario_id"] in [scen1["id"], scen2["id"]]

# ==============================================================================
# DEF-11: NGO Resource Inventory Dispatch & Error Serialization
# ==============================================================================
def test_batch2_def11_dispatch_with_quantity_query_param():
    _, ngo_headers = get_auth("NGO")
    
    # 1. Create a test resource inventory
    create_res = client.post("/api/v1/resources", json={
        "owner_type": "NGO",
        "category": "MEDICAL",
        "resource_name": "Emergency Trauma Bandages",
        "total_quantity": 200,
        "unit": "packs",
        "location_lat": 13.085,
        "location_lng": 80.275
    }, headers=ngo_headers)
    assert create_res.status_code == 201
    resource_id = create_res.json()["id"]

    # 2. Dispatch with ?quantity=35
    dispatch_res = client.post(f"/api/v1/resources/{resource_id}/dispatch?quantity=35", headers=ngo_headers)
    assert dispatch_res.status_code == 200
    data = dispatch_res.json()
    assert data["available_quantity"] == 165

    # 3. Verify exactly 35 was decremented in database
    db = SessionLocal()
    res_db = db.query(Resource).filter(Resource.id == resource_id).first()
    assert res_db.available_quantity == 165
    db.close()

def test_batch2_def11_dispatch_insufficient_stock_preserves_inventory():
    _, ngo_headers = get_auth("NGO")
    
    create_res = client.post("/api/v1/resources", json={
        "owner_type": "NGO",
        "category": "FOOD",
        "resource_name": "Rations Box",
        "total_quantity": 50,
        "unit": "boxes",
        "location_lat": 13.085,
        "location_lng": 80.275
    }, headers=ngo_headers)
    assert create_res.status_code == 201
    resource_id = create_res.json()["id"]

    # Dispatch excessive quantity (100 > 50)
    dispatch_res = client.post(f"/api/v1/resources/{resource_id}/dispatch?quantity=100", headers=ngo_headers)
    assert dispatch_res.status_code == 400
    detail = dispatch_res.json()["detail"]
    assert "insufficient" in detail.lower()

    # Verify inventory was NOT decremented
    db = SessionLocal()
    res_db = db.query(Resource).filter(Resource.id == resource_id).first()
    assert res_db.available_quantity == 50
    db.close()
