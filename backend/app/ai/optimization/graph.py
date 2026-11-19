import math
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import networkx as nx

# --- 1. Geodesic / Haversine Distance Calculation ---

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Computes the Haversine (great-circle) distance in kilometers between two WGS84 coordinate points.
    Properties: Non-negative, symmetric, deterministic.
    """
    R = 6371.0  # Earth's mean radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


# --- 2. Data Transfer & Result Schemas ---

@dataclass
class RouteResult:
    origin_id: str
    destination_id: str
    node_sequence: List[str]
    distance_km: float
    travel_time_minutes: float
    status: str  # FEASIBLE, UNREACHABLE, BLOCKED, INVALID
    unreachable_reason: Optional[str] = None
    algorithm_used: str = "DIJKSTRA"
    graph_version: str = ""

@dataclass
class DistanceTimeMatrix:
    origins: List[str]
    destinations: List[str]
    distance_matrix: List[List[float]]
    time_matrix: List[List[float]]
    route_metadata: Dict[str, RouteResult] = field(default_factory=dict)
    graph_version: str = ""


# --- 3. Road Graph Engine Implementation ---

class RoadGraphEngine:
    def __init__(self, default_speed_kmh: float = 50.0):
        self.graph = nx.DiGraph()
        self.default_speed_kmh = default_speed_kmh
        self.active_blockages: Dict[str, Dict[str, Any]] = {}
        self._cached_version: Optional[str] = None

    def add_node(self, node_id: str, latitude: float, longitude: float, node_type: str = "INTERSECTION", name: Optional[str] = None):
        """Adds a spatial node to the road graph."""
        self.graph.add_node(
            node_id,
            lat=latitude,
            lng=longitude,
            node_type=node_type,
            name=name or node_id
        )
        self._cached_version = None

    def add_edge(self, source_id: str, target_id: str, distance_km: Optional[float] = None, 
                 base_speed_kmh: Optional[float] = None, road_name: Optional[str] = None, one_way: bool = False):
        """
        Adds a road segment edge between source_id and target_id.
        Calculates distance and travel time automatically if not provided.
        """
        if not self.graph.has_node(source_id) or not self.graph.has_node(target_id):
            raise ValueError(f"Both nodes ({source_id}, {target_id}) must exist before adding an edge.")

        src_node = self.graph.nodes[source_id]
        tgt_node = self.graph.nodes[target_id]

        if distance_km is None:
            distance_km = haversine_distance(src_node['lat'], src_node['lng'], tgt_node['lat'], tgt_node['lng'])

        speed = base_speed_kmh or self.default_speed_kmh
        base_time_min = (distance_km / speed) * 60.0 if speed > 0 else float('inf')

        edge_attrs = {
            'distance_km': distance_km,
            'base_speed_kmh': speed,
            'base_travel_time_min': base_time_min,
            'effective_travel_time_min': base_time_min,
            'blockage_status': "OPEN",
            'delay_penalty_mins': 0.0,
            'road_name': road_name or f"{source_id}-{target_id}"
        }

        self.graph.add_edge(source_id, target_id, **edge_attrs)
        if not one_way:
            self.graph.add_edge(target_id, source_id, **edge_attrs)

        self._cached_version = None

    def apply_blockage(self, blockage_id: str, source_id: str, target_id: str, 
                       blockage_status: str = "IMPASSABLE", delay_penalty_mins: float = 0.0):
        """
        Ingests a Phase 5B RoadBlockage state and updates target edge weights dynamically.
        Supported statuses: OPEN, DELAYED, IMPASSABLE, RESOLVED.
        """
        edges_to_update = []
        if self.graph.has_edge(source_id, target_id):
            edges_to_update.append((source_id, target_id))
        if self.graph.has_edge(target_id, source_id):
            edges_to_update.append((target_id, source_id))

        if not edges_to_update:
            raise ValueError(f"Edge ({source_id}, {target_id}) not found in graph for blockage application.")

        for u, v in edges_to_update:
            edge = self.graph.edges[u, v]
            if blockage_status in ("IMPASSABLE", "BLOCKED"):
                edge['blockage_status'] = "IMPASSABLE"
                edge['effective_travel_time_min'] = float('inf')
            elif blockage_status == "DELAYED":
                edge['blockage_status'] = "DELAYED"
                edge['delay_penalty_mins'] = delay_penalty_mins
                edge['effective_travel_time_min'] = edge['base_travel_time_min'] + delay_penalty_mins
            elif blockage_status in ("OPEN", "RESOLVED", "CLEARING"):
                edge['blockage_status'] = "OPEN"
                edge['delay_penalty_mins'] = 0.0
                edge['effective_travel_time_min'] = edge['base_travel_time_min']

        self.active_blockages[blockage_id] = {
            "source_id": source_id,
            "target_id": target_id,
            "blockage_status": blockage_status,
            "delay_penalty_mins": delay_penalty_mins
        }
        self._cached_version = None

    def find_nearest_node(self, latitude: float, longitude: float, max_distance_km: float = 100.0) -> Optional[str]:
        """
        Finds the graph node ID nearest to the given (latitude, longitude) coordinates.
        Returns None if graph is empty or nearest node is beyond max_distance_km.
        """
        if not self.graph.nodes:
            return None
        min_dist = float('inf')
        nearest_node = None
        for node_id, data in self.graph.nodes(data=True):
            dist = haversine_distance(latitude, longitude, data['lat'], data['lng'])
            if dist < min_dist:
                min_dist = dist
                nearest_node = node_id
        if nearest_node is not None and min_dist <= max_distance_km:
            return nearest_node
        return None

    def get_graph_version(self) -> str:
        """Computes a deterministic SHA-256 version hash for the current graph state."""
        if self._cached_version:
            return self._cached_version

        nodes_data = sorted([(n, d['lat'], d['lng']) for n, d in self.graph.nodes(data=True)])
        edges_data = sorted([(u, v, d['effective_travel_time_min'], d['blockage_status']) 
                             for u, v, d in self.graph.edges(data=True)])
        
        state_repr = json.dumps({"nodes": nodes_data, "edges": edges_data}, sort_keys=True)
        self._cached_version = hashlib.sha256(state_repr.encode('utf-8')).hexdigest()[:16]
        return self._cached_version

    def _astar_heuristic(self, node_u: str, node_v: str, max_speed_kmh: float = 80.0) -> float:
        """Admissible A* lower-bound travel time heuristic in minutes."""
        u_lat, u_lng = self.graph.nodes[node_u]['lat'], self.graph.nodes[node_u]['lng']
        v_lat, v_lng = self.graph.nodes[node_v]['lat'], self.graph.nodes[node_v]['lng']
        dist_km = haversine_distance(u_lat, u_lng, v_lat, v_lng)
        return (dist_km / max_speed_kmh) * 60.0

    def compute_shortest_path(self, origin_id: str, destination_id: str, algorithm: str = "DIJKSTRA") -> RouteResult:
        """
        Computes weighted shortest path from origin_id to destination_id using Dijkstra or A*.
        Returns structured RouteResult with explicit status (FEASIBLE, UNREACHABLE, INVALID).
        """
        version = self.get_graph_version()
        if not self.graph.has_node(origin_id) or not self.graph.has_node(destination_id):
            return RouteResult(
                origin_id=origin_id,
                destination_id=destination_id,
                node_sequence=[],
                distance_km=float('inf'),
                travel_time_minutes=float('inf'),
                status="INVALID",
                unreachable_reason=f"Origin '{origin_id}' or Destination '{destination_id}' not found in graph.",
                algorithm_used=algorithm,
                graph_version=version
            )

        if origin_id == destination_id:
            return RouteResult(
                origin_id=origin_id,
                destination_id=destination_id,
                node_sequence=[origin_id],
                distance_km=0.0,
                travel_time_minutes=0.0,
                status="FEASIBLE",
                algorithm_used=algorithm,
                graph_version=version
            )

        try:
            if algorithm.upper() == "ASTAR":
                path = nx.astar_path(
                    self.graph,
                    origin_id,
                    destination_id,
                    heuristic=lambda u, v: self._astar_heuristic(u, v),
                    weight='effective_travel_time_min'
                )
            else:
                path = nx.dijkstra_path(
                    self.graph,
                    origin_id,
                    destination_id,
                    weight='effective_travel_time_min'
                )

            # Calculate total distance and travel time along path
            total_dist = 0.0
            total_time = 0.0
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge = self.graph.edges[u, v]
                if edge['effective_travel_time_min'] == float('inf') or edge['blockage_status'] == "IMPASSABLE":
                    raise nx.NetworkXNoPath(f"Edge ({u}, {v}) is impassable")
                total_dist += edge['distance_km']
                total_time += edge['effective_travel_time_min']

            return RouteResult(
                origin_id=origin_id,
                destination_id=destination_id,
                node_sequence=path,
                distance_km=total_dist,
                travel_time_minutes=total_time,
                status="FEASIBLE",
                algorithm_used=algorithm.upper(),
                graph_version=version
            )

        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return RouteResult(
                origin_id=origin_id,
                destination_id=destination_id,
                node_sequence=[],
                distance_km=float('inf'),
                travel_time_minutes=float('inf'),
                status="UNREACHABLE",
                unreachable_reason="No feasible unblocked path exists between origin and destination.",
                algorithm_used=algorithm.upper(),
                graph_version=version
            )

    def generate_matrix(self, origins: List[str], destinations: List[str], algorithm: str = "DIJKSTRA") -> DistanceTimeMatrix:
        """
        Generates NxM distance ($km$) and travel-time ($mins$) matrices between origin and destination sets.
        Unreachable node pairs explicitly retain float('inf').
        """
        version = self.get_graph_version()
        dist_matrix: List[List[float]] = []
        time_matrix: List[List[float]] = []
        route_meta: Dict[str, RouteResult] = {}

        for orig in origins:
            dist_row: List[float] = []
            time_row: List[float] = []
            for dest in destinations:
                route = self.compute_shortest_path(orig, dest, algorithm=algorithm)
                dist_row.append(route.distance_km)
                time_row.append(route.travel_time_minutes)
                route_meta[f"{orig}->{dest}"] = route
            dist_matrix.append(dist_row)
            time_matrix.append(time_row)

        return DistanceTimeMatrix(
            origins=origins,
            destinations=destinations,
            distance_matrix=dist_matrix,
            time_matrix=time_matrix,
            route_metadata=route_meta,
            graph_version=version
        )


# --- 4. Toy Graph Generator for Brute-Force Optimality Verification ---

def create_synthetic_toy_graph() -> RoadGraphEngine:
    """
    Creates a deterministic 6-node toy graph (A-B-C-D-E-F) with fixed coordinates and known weights.
    
    Topology:
      A -- (10 min, 10 km) -- B -- (15 min, 15 km) -- C
      |                                              |
    (5 min, 5 km)                                (20 min, 20 km)
      |                                              |
      D -- (8 min, 8 km) ---- E -- (12 min, 12 km) -- F
    """
    engine = RoadGraphEngine(default_speed_kmh=60.0)
    
    # Fixed coordinates
    engine.add_node("A", 13.00, 80.00, name="Node A")
    engine.add_node("B", 13.00, 80.10, name="Node B")
    engine.add_node("C", 13.00, 80.25, name="Node C")
    engine.add_node("D", 12.95, 80.00, name="Node D")
    engine.add_node("E", 12.95, 80.10, name="Node E")
    engine.add_node("F", 12.95, 80.25, name="Node F")

    # Add edges with explicit distance_km and base travel speed
    # Speed 60 km/h means 1 km = 1 min
    engine.add_edge("A", "B", distance_km=10.0, base_speed_kmh=60.0) # 10 min
    engine.add_edge("B", "C", distance_km=15.0, base_speed_kmh=60.0) # 15 min
    engine.add_edge("A", "D", distance_km=5.0,  base_speed_kmh=60.0) # 5 min
    engine.add_edge("D", "E", distance_km=8.0,  base_speed_kmh=60.0) # 8 min
    engine.add_edge("E", "F", distance_km=12.0, base_speed_kmh=60.0) # 12 min
    engine.add_edge("C", "F", distance_km=20.0, base_speed_kmh=60.0) # 20 min

    return engine
