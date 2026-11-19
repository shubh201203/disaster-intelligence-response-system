"""
DIRS Phase 5C — Calibrated Regional Road Network Benchmark Graph Generator
Coverage: Coastal Chennai / Tamil Nadu Disaster Corridor (ECR, OMR, GST Arterials)
Classification: SYNTHETIC CALIBRATED BENCHMARK GRAPH
"""
import math
import random
from typing import Optional, List
from app.ai.optimization.graph import RoadGraphEngine, haversine_distance

def create_chennai_benchmark_graph(num_nodes: int = 50, seed: int = 42) -> RoadGraphEngine:
    """
    Generates a deterministic calibrated road network graph covering coastal Chennai.
    Anchored around real major transportation hubs (MGR Central, Guindy, ECR, OMR, Tambaram).
    
    Node count parameter (num_nodes) scales graph size for performance benchmarking:
    10, 50, 100, 500, 1000 nodes.
    """
    engine = RoadGraphEngine(default_speed_kmh=50.0)
    rng = random.Random(seed)

    # Key Anchor Landmarks (WGS84 Coordinates)
    anchors = [
        ("HUB_CENTRAL", 13.0827, 80.2707, "MGR Central Depot"),
        ("HUB_GUINDY", 13.0067, 80.2020, "Guindy Transport Warehouse"),
        ("HUB_TAMBARAM", 12.9249, 80.1000, "Tambaram Relief Stockpile"),
        ("HUB_KOVALAM", 12.7900, 80.2500, "Kovalam Bridge Hub"),
        ("HUB_KELAMBAKKAM", 12.7800, 80.2200, "Kelambakkam Junction"),
        ("HUB_VELACHERY", 12.9780, 80.2180, "Velachery Evacuation Shelter"),
        ("HUB_MARINA", 13.0500, 80.2800, "Marina Beach Relief Station"),
        ("HUB_CHENGALPATTU", 12.6800, 79.9800, "Chengalpattu Emergency Depot"),
        ("HUB_OMR_IT_PARK", 12.9000, 80.2270, "OMR IT Corridor Node"),
        ("HUB_ECR_TOLL", 12.8700, 80.2400, "ECR Toll Station Node")
    ]

    # 1. Add Anchor Nodes
    num_anchors = min(len(anchors), num_nodes)
    for i in range(num_anchors):
        node_id, lat, lng, name = anchors[i]
        engine.add_node(node_id, lat, lng, node_type="DEPOT" if "Depot" in name or "Stockpile" in name else "INTERSECTION", name=name)

    # 2. Add Synthetic Intermediate Nodes if num_nodes > 10
    if num_nodes > num_anchors:
        # Bounding box: Lat [12.65, 13.15], Lng [79.95, 80.30]
        min_lat, max_lat = 12.65, 13.15
        min_lng, max_lng = 79.95, 80.30

        for idx in range(num_anchors, num_nodes):
            node_id = f"NODE_{idx:04d}"
            lat = rng.uniform(min_lat, max_lat)
            lng = rng.uniform(min_lng, max_lng)
            engine.add_node(node_id, lat, lng, node_type="INTERSECTION", name=f"Road Node {idx}")

    # 3. Connect Nodes into Road Topologies (k-Nearest Neighbors)
    node_ids = list(engine.graph.nodes.keys())
    coords = [(n, engine.graph.nodes[n]['lat'], engine.graph.nodes[n]['lng']) for n in node_ids]

    k_neighbors = 4 if num_nodes <= 100 else 6

    for n1, lat1, lng1 in coords:
        # Calculate distances to all other nodes
        dists = []
        for n2, lat2, lng2 in coords:
            if n1 == n2:
                continue
            d = haversine_distance(lat1, lng1, lat2, lng2)
            dists.append((d, n2))

        dists.sort(key=lambda x: x[0])
        # Connect to nearest k neighbors
        for d, n2 in dists[:k_neighbors]:
            if not engine.graph.has_edge(n1, n2):
                # Variable speed limit based on road type
                speed = 60.0 if "ECR" in n1 or "OMR" in n1 or "GST" in n1 else 45.0
                engine.add_edge(n1, n2, distance_km=d, base_speed_kmh=speed, road_name=f"Road {n1}-{n2}")

    return engine
