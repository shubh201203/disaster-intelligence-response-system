import pytest
import math
import networkx as nx
from app.ai.optimization.graph import (
    RoadGraphEngine,
    haversine_distance,
    create_synthetic_toy_graph,
    RouteResult,
    DistanceTimeMatrix
)
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph


def test_haversine_known_coordinates():
    """Verify Haversine distance formula against known coordinate pair ground truth."""
    # MGR Central Depot (13.0827, 80.2707) to Guindy Depot (13.0067, 80.2020) ~11.5 km
    dist = haversine_distance(13.0827, 80.2707, 13.0067, 80.2020)
    assert 10.0 <= dist <= 13.0
    # Symmetry property
    assert haversine_distance(13.0067, 80.2020, 13.0827, 80.2707) == dist
    # Zero distance property
    assert haversine_distance(13.0827, 80.2707, 13.0827, 80.2707) == 0.0


def test_5c_01_normal_shortest_path():
    """TEST-5C-01: Normal weighted shortest path computation on toy graph."""
    engine = create_synthetic_toy_graph()
    
    # Path A -> B -> C: (10 min + 15 min = 25 min, distance 25 km)
    # Path A -> D -> E -> F -> C: (5 + 8 + 12 + 20 = 45 min)
    route = engine.compute_shortest_path("A", "C", algorithm="DIJKSTRA")
    
    assert route.status == "FEASIBLE"
    assert route.node_sequence == ["A", "B", "C"]
    assert route.distance_km == 25.0
    assert route.travel_time_minutes == 25.0

    # Test A* algorithm correctness
    route_astar = engine.compute_shortest_path("A", "C", algorithm="ASTAR")
    assert route_astar.status == "FEASIBLE"
    assert route_astar.node_sequence == ["A", "B", "C"]
    assert route_astar.travel_time_minutes == route.travel_time_minutes


def test_5c_02_blocked_edge_rerouting():
    """TEST-5C-02: Automatic rerouting when primary edge is marked IMPASSABLE."""
    engine = create_synthetic_toy_graph()
    
    # Apply IMPASSABLE blockage to edge A-B
    engine.apply_blockage("BLK-01", "A", "B", blockage_status="IMPASSABLE")
    
    route = engine.compute_shortest_path("A", "C", algorithm="DIJKSTRA")
    
    assert route.status == "FEASIBLE"
    # Rerouted path must be A -> D -> E -> F -> C
    assert route.node_sequence == ["A", "D", "E", "F", "C"]
    assert route.travel_time_minutes == 45.0  # 5 + 8 + 12 + 20


def test_5c_03_partial_blockage_penalty():
    """TEST-5C-03: Travel-time delay penalty application for PARTIALLY_BLOCKED / DELAYED edge."""
    engine = create_synthetic_toy_graph()
    
    # Apply +30 min delay penalty to A-B edge (original 10 min -> 40 min total)
    # Route A-B-C becomes 40 + 15 = 55 min.
    # Alternate A-D-E-F-C is 45 min, so solver should now choose alternate route A-D-E-F-C!
    engine.apply_blockage("BLK-02", "A", "B", blockage_status="DELAYED", delay_penalty_mins=30.0)
    
    route = engine.compute_shortest_path("A", "C", algorithm="DIJKSTRA")
    
    assert route.status == "FEASIBLE"
    assert route.node_sequence == ["A", "D", "E", "F", "C"]
    assert route.travel_time_minutes == 45.0


def test_5c_04_fully_unreachable_destination():
    """TEST-5C-04: Graceful handling of fully unreachable destination node."""
    engine = create_synthetic_toy_graph()
    
    # Block all incoming edges to node C (B-C and F-C)
    engine.apply_blockage("BLK-03", "B", "C", blockage_status="IMPASSABLE")
    engine.apply_blockage("BLK-04", "F", "C", blockage_status="IMPASSABLE")
    
    route = engine.compute_shortest_path("A", "C", algorithm="DIJKSTRA")
    
    assert route.status == "UNREACHABLE"
    assert route.node_sequence == []
    assert route.distance_km == float('inf')
    assert route.travel_time_minutes == float('inf')
    assert "No feasible" in route.unreachable_reason


def test_5c_05_one_way_edge_behavior():
    """TEST-5C-05: One-way edge directional constraint enforcement."""
    engine = RoadGraphEngine(default_speed_kmh=60.0)
    engine.add_node("N1", 13.00, 80.00)
    engine.add_node("N2", 13.00, 80.10)
    
    # Add one-way edge N1 -> N2
    engine.add_edge("N1", "N2", distance_km=10.0, one_way=True)
    
    # Path N1 -> N2 should succeed
    r1 = engine.compute_shortest_path("N1", "N2")
    assert r1.status == "FEASIBLE"
    assert r1.node_sequence == ["N1", "N2"]
    
    # Path N2 -> N1 should be UNREACHABLE
    r2 = engine.compute_shortest_path("N2", "N1")
    assert r2.status == "UNREACHABLE"


def test_5c_06_deterministic_result():
    """TEST-5C-06: Verification of 100% deterministic graph execution."""
    engine = create_chennai_benchmark_graph(num_nodes=50, seed=123)
    
    first_route = engine.compute_shortest_path("HUB_CENTRAL", "HUB_KOVALAM")
    first_version = engine.get_graph_version()
    
    for _ in range(50):
        r = engine.compute_shortest_path("HUB_CENTRAL", "HUB_KOVALAM")
        assert r.node_sequence == first_route.node_sequence
        assert r.travel_time_minutes == first_route.travel_time_minutes
        assert engine.get_graph_version() == first_version


def test_5c_07_distance_matrix_correctness():
    """TEST-5C-07: Distance matrix generation correctness."""
    engine = create_synthetic_toy_graph()
    origins = ["A", "D"]
    destinations = ["B", "C", "F"]
    
    matrix = engine.generate_matrix(origins, destinations)
    
    assert len(matrix.distance_matrix) == 2
    assert len(matrix.distance_matrix[0]) == 3
    # Distance A -> B = 10.0 km
    assert matrix.distance_matrix[0][0] == 10.0
    # Distance A -> C = 25.0 km
    assert matrix.distance_matrix[0][1] == 25.0
    # Distance D -> F = 20.0 km (8 + 12)
    assert matrix.distance_matrix[1][2] == 20.0


def test_5c_08_travel_time_matrix_correctness():
    """TEST-5C-08: Travel-time matrix generation correctness."""
    engine = create_synthetic_toy_graph()
    origins = ["A", "E"]
    destinations = ["C", "F"]
    
    matrix = engine.generate_matrix(origins, destinations)
    
    # Travel time A -> C = 25.0 mins
    assert matrix.time_matrix[0][0] == 25.0
    # Travel time E -> F = 12.0 mins
    assert matrix.time_matrix[1][1] == 12.0


def test_5c_09_graph_version_change():
    """TEST-5C-09: Graph version SHA-256 hash updates after network state modifications."""
    engine = create_synthetic_toy_graph()
    v1 = engine.get_graph_version()
    
    # Apply blockage
    engine.apply_blockage("BLK-10", "B", "C", blockage_status="IMPASSABLE")
    v2 = engine.get_graph_version()
    
    assert v1 != v2
    
    # Clear blockage
    engine.apply_blockage("BLK-10", "B", "C", blockage_status="RESOLVED")
    v3 = engine.get_graph_version()
    
    assert v3 == v1


def test_5c_10_invalid_input_handling():
    """TEST-5C-10: Non-existent node query error handling."""
    engine = create_synthetic_toy_graph()
    
    route = engine.compute_shortest_path("NON_EXISTENT_NODE", "C")
    assert route.status == "INVALID"
    assert route.distance_km == float('inf')
    assert "not found" in route.unreachable_reason


def test_brute_force_optimality_ground_truth():
    """Brute-force path enumeration verifying Dijkstra optimality on small graph."""
    engine = create_synthetic_toy_graph()
    
    # Enumerate all simple paths from A to C manually in NetworkX
    all_paths = list(nx.all_simple_paths(engine.graph, "A", "C"))
    path_costs = []
    for path in all_paths:
        cost = sum(engine.graph.edges[path[i], path[i+1]]['effective_travel_time_min'] for i in range(len(path)-1))
        path_costs.append((cost, path))
    
    min_brute_force_cost, min_brute_force_path = min(path_costs, key=lambda x: x[0])
    
    dijkstra_route = engine.compute_shortest_path("A", "C")
    
    assert dijkstra_route.travel_time_minutes == min_brute_force_cost
    assert dijkstra_route.node_sequence == min_brute_force_path
