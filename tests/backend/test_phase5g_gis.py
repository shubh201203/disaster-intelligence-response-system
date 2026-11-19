"""
DIRS Phase 5G — Advanced GIS Situation Layer & Spatial Query Test Suite
Covers 22 comprehensive tests verifying:
  - 12 canonical GeoJSON situation layers
  - Coordinate system consistency (WGS-84 EPSG:4326, [lng, lat] GeoJSON order)
  - Feature property schema & simulation metadata
  - 30-minute response coverage envelope abstraction & reachable node preservation
  - Spatial geometric algorithms: Ray-casting Point-in-Polygon, Convex Hull, Haversine
  - Spatial Query Engine: K-nearest neighbor, radius search, bounding box, route-blockage intersection
  - REST API endpoint contracts for GIS Situation Layers and Spatial Queries
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
from app.ai.simulation.gis_situation import (
    GISSituationLayerBuilder,
    haversine_distance,
    create_radial_polygon,
    compute_convex_hull,
    CANONICAL_GIS_LAYERS
)
from app.ai.simulation.gis_query import SpatialQueryEngine
from app.ai.simulation.scenario_engine import OperationalStateSnapshot
from app.models.incident import Incident
from app.models.shelter import Shelter
from app.models.rescue import RoadBlockage

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


@pytest.fixture
def benchmark_graph():
    return create_chennai_benchmark_graph(num_nodes=25, seed=42)


@pytest.fixture
def mock_operational_state(benchmark_graph):
    incidents = [
        Incident(id="inc-1", incident_code="INC-G-1", title="Flooding A", latitude=13.0827, longitude=80.2707, severity_level="CRITICAL", status="REPORTED", priority_score=85.0, description="Flooding"),
        Incident(id="inc-2", incident_code="INC-G-2", title="Waterlogging B", latitude=13.0900, longitude=80.2800, severity_level="HIGH", status="VERIFIED", priority_score=70.0, description="Waterlogging"),
    ]
    shelters = [
        Shelter(id="sh-1", name="Shelter Central", address="Central Chennai", latitude=13.0800, longitude=80.2750, total_capacity=500, current_occupancy=100, status="OPEN"),
        Shelter(id="sh-2", name="Shelter North", address="North Chennai", latitude=13.0950, longitude=80.2850, total_capacity=300, current_occupancy=50, status="OPEN"),
    ]
    depots = [
        {"id": "depot-1", "name": "Central Depot", "latitude": 13.0850, "longitude": 80.2700, "supplies": {"WATER": 5000, "FOOD": 3000}},
    ]
    vehicles = [
        {"id": "veh-1", "vehicle_type": "TRUCK_HEAVY", "latitude": 13.0850, "longitude": 80.2700, "capacity_kg": 5000.0, "status": "AVAILABLE"},
        {"id": "veh-2", "vehicle_type": "VAN", "latitude": 13.0860, "longitude": 80.2710, "capacity_kg": 1500.0, "status": "AVAILABLE"},
    ]
    volunteers = [
        {"id": "vol-1", "full_name": "Dr. Sarah", "latitude": 13.0820, "longitude": 80.2720, "medical_certified": True, "status": "AVAILABLE"},
        {"id": "vol-2", "full_name": "John Doe", "latitude": 13.0830, "longitude": 80.2730, "medical_certified": False, "status": "AVAILABLE"},
    ]
    blockages = [
        RoadBlockage(id="blk-1", title="Waterlogging", hazard_type="FLOOD", latitude=13.0827, longitude=80.2707, blockage_status="IMPASSABLE")
    ]
    return OperationalStateSnapshot(
        incidents=incidents,
        shelters=shelters,
        depots=depots,
        vehicles=vehicles,
        volunteers=volunteers,
        road_blockages=blockages,
        graph_engine=benchmark_graph
    )


# --- GIS Situation Layer Tests ---

def test_canonical_layers_defined():
    """Verify that all 12 canonical GIS layers are formally defined."""
    assert len(CANONICAL_GIS_LAYERS) == 12
    assert "INCIDENTS" in CANONICAL_GIS_LAYERS
    assert "RESPONSE_COVERAGE" in CANONICAL_GIS_LAYERS
    assert "ROAD_BLOCKAGES" in CANONICAL_GIS_LAYERS


def test_gis_feature_collection_schema(mock_operational_state):
    """Verify that build_situation_layers returns a valid GeoJSON FeatureCollection."""
    builder = GISSituationLayerBuilder()
    fc = builder.build_situation_layers(mock_operational_state)
    assert fc["type"] == "FeatureCollection"
    assert "features" in fc
    assert isinstance(fc["features"], list)
    assert len(fc["features"]) > 0


def test_layer_filtering(mock_operational_state):
    """Verify that specific layers can be selected and filtered."""
    builder = GISSituationLayerBuilder()
    fc = builder.build_situation_layers(mock_operational_state, active_layers=["INCIDENTS"])
    for feat in fc["features"]:
        assert feat["properties"]["layer_type"] == "INCIDENTS"


def test_feature_coordinates_crs_and_order(mock_operational_state):
    """Verify WGS-84 EPSG:4326 and [longitude, latitude] coordinate ordering in Point features."""
    builder = GISSituationLayerBuilder()
    fc = builder.build_situation_layers(mock_operational_state, active_layers=["INCIDENTS", "SHELTERS"])
    for feat in fc["features"]:
        if feat["geometry"]["type"] == "Point":
            lng, lat = feat["geometry"]["coordinates"]
            # Chennai bounds check
            assert 80.0 <= lng <= 80.5
            assert 12.8 <= lat <= 13.3


def test_feature_simulation_metadata(mock_operational_state):
    """Verify simulation metadata and tags on features."""
    builder = GISSituationLayerBuilder()
    fc = builder.build_situation_layers(mock_operational_state, is_simulation=True)
    for feat in fc["features"]:
        assert feat["properties"]["is_simulation"] is True
        assert "timestamp" in feat["properties"]


def test_coverage_envelope_layer_properties(mock_operational_state):
    """Verify 30-minute coverage envelope contains explicit disclaimer and reachable node count."""
    builder = GISSituationLayerBuilder()
    fc = builder.build_situation_layers(mock_operational_state, active_layers=["RESPONSE_COVERAGE"])
    coverage_features = [f for f in fc["features"] if f["properties"]["layer_type"] == "RESPONSE_COVERAGE"]
    assert len(coverage_features) >= 1
    envelope = coverage_features[0]
    assert envelope["geometry"]["type"] == "Polygon"
    assert "disclaimer" in envelope["properties"]
    assert "visualization abstraction" in envelope["properties"]["disclaimer"].lower()
    assert "reachable_network_nodes_count" in envelope["properties"]


def test_radial_polygon_generation():
    """Verify that create_radial_polygon produces a closed polygon ring."""
    poly = create_radial_polygon(13.0827, 80.2707, radius_km=2.0, num_points=16)
    assert len(poly) == 17  # 16 + 1 to close ring
    assert poly[0] == poly[-1]  # Closed polygon


def test_convex_hull_computation():
    """Verify convex hull calculation on a set of 2D points."""
    points = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0), (1.0, 1.0)]
    hull = compute_convex_hull(points)
    assert len(hull) == 5  # 4 vertices + 1 closing point
    assert hull[0] == hull[-1]
    assert (1.0, 1.0) not in hull[:-1]  # Interior point excluded from vertices


def test_haversine_distance():
    """Verify haversine distance calculation between known coordinates."""
    # Distance between Chennai Central (13.0827, 80.2707) and Marina Beach (13.0500, 80.2824) is ~4 km
    d = haversine_distance(13.0827, 80.2707, 13.0500, 80.2824)
    assert 3.5 <= d <= 4.5


# --- Spatial Query Engine Tests ---

def test_point_in_polygon_ray_casting():
    """Verify point-in-polygon ray-casting test."""
    polygon = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0], [0.0, 0.0]]
    assert SpatialQueryEngine.point_in_polygon([2.0, 2.0], polygon) is True
    assert SpatialQueryEngine.point_in_polygon([5.0, 5.0], polygon) is False
    assert SpatialQueryEngine.point_in_polygon([-1.0, 2.0], polygon) is False


def test_line_segments_intersect():
    """Verify line segment intersection detection."""
    # Crossing segments: (0,0)-(2,2) and (0,2)-(2,0)
    assert SpatialQueryEngine.line_segments_intersect([0, 0], [2, 2], [0, 2], [2, 0]) is True
    # Parallel disjoint segments
    assert SpatialQueryEngine.line_segments_intersect([0, 0], [2, 0], [0, 1], [2, 1]) is False


def test_nearest_shelters_query(mock_operational_state):
    """Verify K-nearest shelter spatial query."""
    engine = SpatialQueryEngine()
    results = engine.find_nearest_shelters(mock_operational_state, query_lat=13.0810, query_lng=80.2740, k=2)
    assert len(results) == 2
    assert results[0]["id"] == "sh-1"
    assert results[0]["distance_km"] < results[1]["distance_km"]


def test_nearest_depots_query(mock_operational_state):
    """Verify K-nearest depot spatial query."""
    engine = SpatialQueryEngine()
    results = engine.find_nearest_depots(mock_operational_state, query_lat=13.0850, query_lng=80.2700, k=1)
    assert len(results) == 1
    assert results[0]["id"] == "depot-1"
    assert results[0]["distance_km"] < 0.1


def test_nearest_vehicles_query(mock_operational_state):
    """Verify K-nearest vehicle spatial query."""
    engine = SpatialQueryEngine()
    results = engine.find_nearest_vehicles(mock_operational_state, query_lat=13.0850, query_lng=80.2700, k=2)
    assert len(results) == 2
    assert results[0]["distance_km"] <= results[1]["distance_km"]


def test_nearest_volunteers_query(mock_operational_state):
    """Verify K-nearest volunteer spatial query with medical filtering."""
    engine = SpatialQueryEngine()
    # Medical certified only
    med_results = engine.find_nearest_volunteers(mock_operational_state, query_lat=13.0820, query_lng=80.2720, k=5, medical_only=True)
    assert len(med_results) == 1
    assert med_results[0]["id"] == "vol-1"


def test_radius_spatial_filter(mock_operational_state):
    """Verify features within a specified radius are correctly filtered."""
    engine = SpatialQueryEngine()
    builder = GISSituationLayerBuilder()
    fc = builder.build_situation_layers(mock_operational_state, active_layers=["INCIDENTS"])
    filtered = engine.filter_features_by_radius(fc["features"], center_lat=13.0827, center_lng=80.2707, radius_km=1.0)
    assert len(filtered) >= 1
    assert filtered[0]["id"] == "inc-1"


def test_bounding_box_filter(mock_operational_state):
    """Verify features within a bounding box are correctly extracted."""
    engine = SpatialQueryEngine()
    builder = GISSituationLayerBuilder()
    fc = builder.build_situation_layers(mock_operational_state, active_layers=["SHELTERS"])
    # Box enclosing shelter-1 but excluding shelter-2
    bbox = engine.filter_features_by_bbox(fc["features"], min_lng=80.270, min_lat=13.075, max_lng=80.280, max_lat=13.085)
    assert len(bbox) == 1
    assert bbox[0]["id"] == "sh-1"


def test_route_blockage_intersection():
    """Verify detection of route intersecting a road blockage polygon."""
    engine = SpatialQueryEngine()
    route_coords = [[80.2700, 13.0800], [80.2750, 13.0850], [80.2800, 13.0900]]
    # Blockage polygon intersecting the route segment
    blockage_poly = [[80.2740, 13.0840], [80.2760, 13.0840], [80.2760, 13.0860], [80.2740, 13.0860], [80.2740, 13.0840]]
    assert engine.route_intersects_blockage(route_coords, blockage_poly) is True

    # Blockage polygon far away from route
    far_poly = [[80.3000, 13.1000], [80.3050, 13.1000], [80.3050, 13.1050], [80.3000, 13.1050], [80.3000, 13.1000]]
    assert engine.route_intersects_blockage(route_coords, far_poly) is False


def test_gis_layers_api_integration():
    """Verify REST API GET /api/v1/gis/layers endpoint."""
    headers = get_auth_header("GOVT")
    response = client.get("/api/v1/gis/layers?layers=INCIDENTS,SHELTERS", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data


def test_gis_spatial_query_api_integration():
    """Verify REST API POST /api/v1/gis/spatial-query endpoint."""
    headers = get_auth_header("GOVT")
    payload = {
        "query_type": "NEAREST_SHELTER",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "radius_km": 10.0
    }
    response = client.post("/api/v1/gis/spatial-query", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "features" in data
    assert "results_count" in data


def test_gis_empty_layers_parameter():
    """Verify default behavior when layers query parameter is omitted."""
    headers = get_auth_header("GOVT")
    response = client.get("/api/v1/gis/layers", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
