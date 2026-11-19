"""
DIRS Phase 5G-C: Spatial Impact Propagation
Computes deterministic spatial impact zones and network reachability propagation.
Terminology: Strictly 'SIMULATED IMPACT' (Not real-world disaster prediction).
Classification: SYNTHETIC CALIBRATED SIMULATION / DECISION SUPPORT
"""
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple

from app.ai.optimization.orchestrator import IncidentIntakeInput
from app.ai.optimization.shelter import ShelterInput
from app.ai.optimization.allocation import DepotSupplyInput
from app.ai.optimization.graph import RoadGraphEngine
from app.ai.simulation.gis_situation import haversine_distance, create_radial_polygon
from app.ai.simulation.gis_query import point_in_polygon


# ------------------------------------------------------------------------------
# 1. Documented Simulation Impact Thresholds
# ------------------------------------------------------------------------------
# These are deterministic prototype simulation thresholds.
# They are not empirically validated hazard boundaries.

SIMULATION_ZONE_THRESHOLDS = {
    "CRITICAL": {
        "max_distance_km": 1.5,
        "min_priority_score": 80.0,
        "description": "Distance <= 1.5 km OR Priority >= 80 OR physically isolated by blockages."
    },
    "HIGH": {
        "max_distance_km": 3.5,
        "min_priority_score": 60.0,
        "description": "Distance <= 3.5 km OR Priority >= 60."
    },
    "MEDIUM": {
        "max_distance_km": 7.0,
        "min_priority_score": 40.0,
        "description": "Distance <= 7.0 km OR Priority >= 40."
    },
    "LOW": {
        "max_distance_km": 12.0,
        "min_priority_score": 0.0,
        "description": "Distance <= 12.0 km OR Priority < 40."
    }
}


@dataclass
class ImpactZone:
    """Represents a simulated impact zone boundary."""
    incident_id: str
    tier: str # CRITICAL, HIGH, MEDIUM, LOW
    center_lat: float
    center_lng: float
    radius_km: float
    polygon_coordinates: List[List[float]] # [[lng, lat], ...]
    threshold_rule: str
    classification: str = "SIMULATED IMPACT"

    def to_geojson_feature(self) -> Dict[str, Any]:
        return {
            "type": "Feature",
            "id": f"ZONE_{self.incident_id}_{self.tier}",
            "geometry": {
                "type": "Polygon",
                "coordinates": [self.polygon_coordinates]
            },
            "properties": {
                "incident_id": self.incident_id,
                "tier": self.tier,
                "radius_km": self.radius_km,
                "rule": self.threshold_rule,
                "classification": self.classification,
                "disclaimer": "SIMULATED IMPACT: Deterministic prototype simulation threshold only."
            }
        }


@dataclass
class SpatialImpactReport:
    """Complete summary of spatial and network impact under a simulated scenario."""
    impact_zones: List[ImpactZone]
    affected_incident_ids: List[str]
    affected_shelter_ids: List[str]
    affected_depot_ids: List[str]
    unreachable_nodes: List[str]
    isolated_shelter_ids: List[str]
    isolated_depot_ids: List[str]
    total_hazard_area_km2: float
    disclaimer: str = (
        "SIMULATED IMPACT: Prototype scenario impact model for decision-support. "
        "Not a real-world physical disaster forecast."
    )


class SpatialImpactPropagator:
    """
    Propagates scenario hazards radially and through the Phase 5C road network graph.
    """

    @classmethod
    def propagate_impact(
        cls,
        incidents: List[Any],
        shelters: List[Any],
        depots: List[Any],
        graph_engine: RoadGraphEngine,
        area_multiplier: float = 1.0
    ) -> SpatialImpactReport:
        """
        Executes deterministic impact zone generation and network reachability audit.
        Accepts both DTO objects (IncidentIntakeInput / ShelterInput / DepotSupplyInput)
        and plain dicts (as produced by scenario new_incidents injection).
        """
        zones: List[ImpactZone] = []
        affected_inc_ids: Set[str] = set()
        affected_shelter_ids: Set[str] = set()
        affected_depot_ids: Set[str] = set()
        total_area_km2 = 0.0

        # Helper extractors — handle both DTO and dict
        def _inc_id(x):
            if isinstance(x, dict):
                return str(x.get('incident_id', x.get('id', 'INC-?')))
            return str(getattr(x, 'incident_id', getattr(x, 'id', 'INC-?')))

        def _inc_lat(x):
            if isinstance(x, dict):
                return float(x.get('latitude', 13.0827))
            return float(getattr(x, 'latitude', 13.0827))

        def _inc_lng(x):
            if isinstance(x, dict):
                return float(x.get('longitude', 80.2707))
            return float(getattr(x, 'longitude', 80.2707))

        def _sh_id(x):
            if isinstance(x, dict):
                return str(x.get('shelter_id', x.get('id', 'SH-?')))
            return str(getattr(x, 'shelter_id', getattr(x, 'id', 'SH-?')))

        def _sh_lat(x):
            if isinstance(x, dict):
                return float(x.get('latitude', 13.08))
            return float(getattr(x, 'latitude', 13.08))

        def _sh_lng(x):
            if isinstance(x, dict):
                return float(x.get('longitude', 80.27))
            return float(getattr(x, 'longitude', 80.27))

        def _dep_id(x):
            if isinstance(x, dict):
                return str(x.get('depot_id', x.get('id', 'DEPOT-?')))
            return str(getattr(x, 'depot_id', getattr(x, 'id', 'DEPOT-?')))

        def _dep_lat(x):
            if isinstance(x, dict):
                return float(x.get('latitude', 13.085))
            return float(getattr(x, 'latitude', 13.085))

        def _dep_lng(x):
            if isinstance(x, dict):
                return float(x.get('longitude', 80.27))
            return float(getattr(x, 'longitude', 80.27))

        # 1. Generate radial impact zones around incidents
        for inc in incidents:
            inc_id = _inc_id(inc)
            inc_lat = _inc_lat(inc)
            inc_lng = _inc_lng(inc)
            affected_inc_ids.add(inc_id)

            for tier, spec in SIMULATION_ZONE_THRESHOLDS.items():
                r_km = spec["max_distance_km"] * area_multiplier
                poly_coords = create_radial_polygon(inc_lat, inc_lng, r_km)

                zone = ImpactZone(
                    incident_id=inc_id,
                    tier=tier,
                    center_lat=inc_lat,
                    center_lng=inc_lng,
                    radius_km=round(r_km, 3),
                    polygon_coordinates=poly_coords,
                    threshold_rule=spec["description"]
                )
                zones.append(zone)

                if tier == "CRITICAL":
                    total_area_km2 += math.pi * (r_km ** 2)

                # Check which shelters fall inside this impact zone
                for s in shelters:
                    if point_in_polygon(_sh_lng(s), _sh_lat(s), poly_coords):
                        affected_shelter_ids.add(_sh_id(s))

                # Check which depots fall inside this impact zone
                for d in depots:
                    if point_in_polygon(_dep_lng(d), _dep_lat(d), poly_coords):
                        affected_depot_ids.add(_dep_id(d))

        # 2. Graph Connectivity & Reachability Propagation
        unreachable_nodes = set()
        isolated_shelters = set()
        isolated_depots = set()

        # Find depot nodes on the graph
        depot_nodes = {}
        for d in depots:
            d_id = _dep_id(d)
            d_lat = _dep_lat(d)
            d_lng = _dep_lng(d)
            depot_nodes[d_id] = graph_engine.find_nearest_node(d_lat, d_lng)

        # Test shelter reachability from at least one depot
        for s in shelters:
            s_node = graph_engine.find_nearest_node(_sh_lat(s), _sh_lng(s))
            can_reach = False
            for d_id, d_node in depot_nodes.items():
                if d_node and s_node:
                    route = graph_engine.compute_shortest_path(d_node, s_node)
                    if route.status == "FEASIBLE":
                        can_reach = True
                        break
            if not can_reach and depot_nodes:
                isolated_shelters.add(_sh_id(s))
                if s_node:
                    unreachable_nodes.add(s_node)

        # Check for isolated depots
        for d in depots:
            d_node = depot_nodes.get(_dep_id(d))
            if d_node:
                has_active_edges = any(
                    data.get("status") != "IMPASSABLE"
                    for _, _, data in graph_engine.graph.edges(d_node, data=True)
                )
                if not has_active_edges and graph_engine.graph.degree(d_node) > 0:
                    isolated_depots.add(_dep_id(d))

        return SpatialImpactReport(
            impact_zones=zones,
            affected_incident_ids=sorted(list(affected_inc_ids)),
            affected_shelter_ids=sorted(list(affected_shelter_ids)),
            affected_depot_ids=sorted(list(affected_depot_ids)),
            unreachable_nodes=sorted(list(unreachable_nodes)),
            isolated_shelter_ids=sorted(list(isolated_shelters)),
            isolated_depot_ids=sorted(list(isolated_depots)),
            total_hazard_area_km2=round(total_area_km2, 2)
        )

    def propagate_network_impact(
        self,
        graph_engine: RoadGraphEngine,
        blockages: List[Dict[str, Any]]
    ) -> SpatialImpactReport:
        """
        Instance method variant: evaluates network isolation effects of scenario blockages.
        Applies blockages to a cloned graph, then checks reachability.
        Used by the test suite directly.
        """
        import copy
        cloned_graph = copy.deepcopy(graph_engine)
        # Apply blockages to the cloned graph
        for blk in blockages:
            u = blk.get("u")
            v = blk.get("v")
            status = blk.get("status", "IMPASSABLE")
            if u and v and cloned_graph.graph.has_edge(u, v):
                blk_id = blk.get("blockage_id", f"BLK_{u}_{v}")
                cloned_graph.apply_blockage(
                    blockage_id=blk_id,
                    source_id=u,
                    target_id=v,
                    blockage_status=status,
                    delay_penalty_mins=blk.get("delay_factor", 1.0)
                )

        # Determine unreachable nodes after blockage
        unreachable_nodes = set()
        # Use graph's connected components (undirected) to find isolated groups
        import networkx as nx
        undirected = cloned_graph.graph.to_undirected()
        # Filter out IMPASSABLE edges for reachability analysis
        active_edges = [
            (u, v) for u, v, d in cloned_graph.graph.edges(data=True)
            if d.get("status") != "IMPASSABLE"
        ]
        active_graph = nx.Graph()
        active_graph.add_nodes_from(cloned_graph.graph.nodes())
        active_graph.add_edges_from(active_edges)
        components = list(nx.connected_components(active_graph))
        if len(components) > 1:
            # Nodes in minority components are unreachable from the majority
            largest = max(components, key=len)
            for comp in components:
                if comp is not largest:
                    unreachable_nodes.update(comp)

        return SpatialImpactReport(
            impact_zones=[],
            affected_incident_ids=[],
            affected_shelter_ids=[],
            affected_depot_ids=[],
            unreachable_nodes=sorted(list(unreachable_nodes)),
            isolated_shelter_ids=[],
            isolated_depot_ids=[],
            total_hazard_area_km2=0.0
        )

