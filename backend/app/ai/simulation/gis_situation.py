"""
DIRS Phase 5G-A: Advanced GIS Situation Layer
Generates canonical 12 GIS GeoJSON FeatureCollections representing the complete spatial disaster state.
CRS: WGS-84 / EPSG:4326 (Coordinates formatted as [longitude, latitude])
Classification: SYNTHETIC CALIBRATED BENCHMARK / DECISION-SUPPORT VISUALIZATION
"""
import copy
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from app.ai.optimization.orchestrator import IncidentIntakeInput, IntegratedOptimizationResult
from app.ai.optimization.shelter import ShelterInput
from app.ai.optimization.allocation import DepotSupplyInput
from app.ai.optimization.routing import VehicleInput
from app.ai.optimization.volunteer import VolunteerInput
from app.ai.optimization.graph import RoadGraphEngine


CANONICAL_GIS_LAYERS: List[str] = [
    "INCIDENTS",
    "SHELTERS",
    "DEPOTS",
    "VEHICLES",
    "VOLUNTEERS",
    "ROAD_NETWORK",
    "ROAD_BLOCKAGES",
    "EVACUATION_ZONES",
    "RISK_ZONES",
    "RESOURCE_ROUTES",
    "VOLUNTEER_ASSIGNMENTS",
    "RESPONSE_COVERAGE"
]


# ------------------------------------------------------------------------------
# 1. Geometric Helper Utilities (WGS-84 / Haversine)
# ------------------------------------------------------------------------------

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance in kilometers between two WGS-84 points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2.0) ** 2))
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def create_radial_polygon(
    center_lat: float, center_lng: float, radius_km: float, num_points: int = 24
) -> List[List[float]]:
    """
    Generates a regular circular approximation polygon in WGS-84 [lng, lat] coordinates.
    Used for simulated hazard buffers and evacuation zones.
    """
    coordinates: List[List[float]] = []
    lat_r = math.radians(center_lat)
    
    # 1 deg lat approx 111.0 km, 1 deg lng approx 111.0 * cos(lat) km
    d_lat_deg = radius_km / 111.0
    cos_lat = math.cos(lat_r)
    d_lng_deg = radius_km / (111.0 * cos_lat) if abs(cos_lat) > 1e-6 else radius_km / 111.0

    for i in range(num_points):
        angle = (2.0 * math.pi * i) / num_points
        lat_pt = round(center_lat + d_lat_deg * math.sin(angle), 6)
        lng_pt = round(center_lng + d_lng_deg * math.cos(angle), 6)
        coordinates.append([lng_pt, lat_pt])

    # Close polygon
    coordinates.append(coordinates[0])
    return coordinates


def compute_convex_hull(points: List[Tuple[float, float]]) -> List[List[float]]:
    """
    Computes 2D Convex Hull of (lng, lat) tuples using Monotone Chain algorithm.
    Returns closed polygon coordinates [[lng, lat], ...].
    """
    if len(points) < 3:
        if not points:
            return []
        pts = [[p[0], p[1]] for p in points]
        if pts:
            pts.append(pts[0])
        return pts

    sorted_pts = sorted(set(points))
    if len(sorted_pts) < 3:
        pts = [[p[0], p[1]] for p in sorted_pts]
        pts.append(pts[0])
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in sorted_pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(sorted_pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = lower[:-1] + upper[:-1]
    res = [[round(p[0], 6), round(p[1], 6)] for p in hull]
    if res:
        res.append(res[0])
    return res


# ------------------------------------------------------------------------------
# 2. Canonical 12 GIS Layer Generators
# ------------------------------------------------------------------------------

class GISSituationLayerBuilder:
    """
    Generates the canonical 12 GIS GeoJSON FeatureCollections for DIRS.
    Strictly preserves provenance, CRS WGS-84, and non-prescriptive abstractions.
    """

    @staticmethod
    def build_incidents_layer(incidents: List[IncidentIntakeInput]) -> Dict[str, Any]:
        """Layer 1: INCIDENTS."""
        features = []
        for inc in incidents:
            features.append({
                "type": "Feature",
                "id": inc.incident_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(inc.longitude, 6), round(inc.latitude, 6)]
                },
                "properties": {
                    "layer": "INCIDENTS",
                    "incident_id": inc.incident_id,
                    "title": inc.title,
                    "severity_level": inc.severity_level,
                    "priority_score": inc.priority_score,
                    "disaster_type": inc.disaster_type,
                    "people_affected": inc.people_affected,
                    "vulnerable_count": inc.vulnerable_count,
                    "injuries": inc.injuries,
                    "status": inc.status,
                    "provenance": "PHASE_5G_INCIDENT_INTAKE"
                }
            })
        return {
            "type": "FeatureCollection",
            "layer_name": "INCIDENTS",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_shelters_layer(shelters: List[ShelterInput]) -> Dict[str, Any]:
        """Layer 2: SHELTERS."""
        features = []
        for s in shelters:
            features.append({
                "type": "Feature",
                "id": s.shelter_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(s.longitude, 6), round(s.latitude, 6)]
                },
                "properties": {
                    "layer": "SHELTERS",
                    "shelter_id": s.shelter_id,
                    "name": s.name,
                    "total_capacity": s.total_capacity,
                    "current_occupancy": s.current_occupancy,
                    "available_capacity": max(0, s.total_capacity - s.current_occupancy),
                    "status": s.status,
                    "accessibility_features": s.accessibility_features,
                    "has_medical": s.has_medical,
                    "power_available": s.power_available,
                    "sanitation_available": s.sanitation_available,
                    "disaster_compatibility": s.disaster_compatibility,
                    "provenance": "PHASE_5F_SHELTER_REGISTRY"
                }
            })
        return {
            "type": "FeatureCollection",
            "layer_name": "SHELTERS",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_depots_layer(depots: List[DepotSupplyInput]) -> Dict[str, Any]:
        """Layer 3: DEPOTS."""
        features = []
        for d in depots:
            features.append({
                "type": "Feature",
                "id": d.depot_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(d.longitude, 6), round(d.latitude, 6)]
                },
                "properties": {
                    "layer": "DEPOTS",
                    "depot_id": d.depot_id,
                    "name": d.name,
                    "supplies": d.supplies,
                    "total_supply_units": sum(d.supplies.values()),
                    "provenance": "PHASE_5D_RESOURCE_REGISTRY"
                }
            })
        return {
            "type": "FeatureCollection",
            "layer_name": "DEPOTS",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_vehicles_layer(vehicles: List[VehicleInput]) -> Dict[str, Any]:
        """Layer 4: VEHICLES."""
        features = []
        for v in vehicles:
            features.append({
                "type": "Feature",
                "id": v.vehicle_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(v.depot_lng, 6), round(v.depot_lat, 6)]
                },
                "properties": {
                    "layer": "VEHICLES",
                    "vehicle_id": v.vehicle_id,
                    "vehicle_code": v.vehicle_code,
                    "vehicle_type": v.vehicle_type,
                    "capacity_weight_kg": v.capacity_weight_kg,
                    "capacity_volume_m3": v.capacity_volume_m3,
                    "home_depot_id": v.depot_id,
                    "status": v.status,
                    "provenance": "PHASE_5E_FLEET_REGISTRY"
                }
            })
        return {
            "type": "FeatureCollection",
            "layer_name": "VEHICLES",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_volunteers_layer(volunteers: List[VolunteerInput]) -> Dict[str, Any]:
        """Layer 5: VOLUNTEERS."""
        features = []
        for vol in volunteers:
            features.append({
                "type": "Feature",
                "id": vol.volunteer_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(vol.longitude, 6), round(vol.latitude, 6)]
                },
                "properties": {
                    "layer": "VOLUNTEERS",
                    "volunteer_id": vol.volunteer_id,
                    "name": vol.name,
                    "skill_category": vol.skill_category,
                    "skills": vol.skills,
                    "medical_certified": vol.medical_certified,
                    "verification_status": vol.verification_status,
                    "is_available": vol.is_available,
                    "max_travel_time_mins": vol.max_travel_time_mins,
                    "provenance": "PHASE_5F_VOLUNTEER_REGISTRY"
                }
            })
        return {
            "type": "FeatureCollection",
            "layer_name": "VOLUNTEERS",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_road_network_layer(graph_engine: RoadGraphEngine) -> Dict[str, Any]:
        """Layer 6: ROAD_NETWORK (Derived strictly from Phase 5C graph)."""
        features = []
        edges_done = set()
        
        for u, v, data in graph_engine.graph.edges(data=True):
            edge_key = tuple(sorted([u, v]))
            if edge_key in edges_done:
                continue
            edges_done.add(edge_key)

            u_lat = graph_engine.graph.nodes[u].get("lat", 13.0827)
            u_lng = graph_engine.graph.nodes[u].get("lng", 80.2707)
            v_lat = graph_engine.graph.nodes[v].get("lat", 13.0827)
            v_lng = graph_engine.graph.nodes[v].get("lng", 80.2707)

            features.append({
                "type": "Feature",
                "id": f"EDGE_{u}_{v}",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(u_lng, 6), round(u_lat, 6)],
                        [round(v_lng, 6), round(v_lat, 6)]
                    ]
                },
                "properties": {
                    "layer": "ROAD_NETWORK",
                    "u": u,
                    "v": v,
                    "length_km": round(data.get("length_km", 1.0), 3),
                    "speed_kmh": data.get("speed_kmh", 40.0),
                    "road_type": data.get("road_type", "primary"),
                    "status": data.get("status", "NORMAL"),
                    "graph_version": graph_engine.get_graph_version(),
                    "provenance": "PHASE_5C_ROAD_GRAPH"
                }
            })
        return {
            "type": "FeatureCollection",
            "layer_name": "ROAD_NETWORK",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_road_blockages_layer(graph_engine: RoadGraphEngine) -> Dict[str, Any]:
        """Layer 7: ROAD_BLOCKAGES (IMPASSABLE and DELAYED edges)."""
        features = []
        blockage_dict = getattr(graph_engine, 'active_blockages', getattr(graph_engine, 'blockages', {}))
        for blockage_id, b in blockage_dict.items():
            if isinstance(b, dict):
                u = b.get("source_id", b.get("u"))
                v = b.get("target_id", b.get("v"))
                status = b.get("blockage_status", b.get("status", "IMPASSABLE"))
                delay = b.get("delay_penalty_mins", 0.0)
            else:
                u = getattr(b, "u", getattr(b, "source_id", None))
                v = getattr(b, "v", getattr(b, "target_id", None))
                status = getattr(b, "status", getattr(b, "blockage_status", "IMPASSABLE"))
                delay = getattr(b, "delay_factor", getattr(b, "delay_penalty_mins", 0.0))

            if u and v and graph_engine.graph.has_node(u) and graph_engine.graph.has_node(v):
                u_lat = graph_engine.graph.nodes[u].get("lat", 13.0827)
                u_lng = graph_engine.graph.nodes[u].get("lng", 80.2707)
                v_lat = graph_engine.graph.nodes[v].get("lat", 13.0827)
                v_lng = graph_engine.graph.nodes[v].get("lng", 80.2707)

                features.append({
                    "type": "Feature",
                    "id": blockage_id,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [round(u_lng, 6), round(u_lat, 6)],
                            [round(v_lng, 6), round(v_lat, 6)]
                        ]
                    },
                    "properties": {
                        "layer": "ROAD_BLOCKAGES",
                        "blockage_id": blockage_id,
                        "source_node": u,
                        "target_node": v,
                        "status": status,
                        "delay_penalty_mins": delay,
                        "provenance": "PHASE_5C_GRAPH_BLOCKAGE"
                    }
                })
        return {
            "type": "FeatureCollection",
            "layer_name": "ROAD_BLOCKAGES",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_evacuation_zones_layer(
        incidents: List[IncidentIntakeInput],
        multiplier: float = 1.0
    ) -> Dict[str, Any]:
        """
        Layer 8: EVACUATION_ZONES.
        Deterministic circular polygons around high-severity incidents.
        Explicitly labeled: SIMULATED EVACUATION ZONE.
        """
        features = []
        for inc in incidents:
            if inc.severity_level in ["CRITICAL", "HIGH"] or inc.people_affected >= 50:
                base_radius_km = 1.5 if inc.severity_level == "CRITICAL" else 1.0
                effective_radius_km = base_radius_km * multiplier
                poly_coords = create_radial_polygon(inc.latitude, inc.longitude, effective_radius_km)

                features.append({
                    "type": "Feature",
                    "id": f"EVAC_ZONE_{inc.incident_id}",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [poly_coords]
                    },
                    "properties": {
                        "layer": "EVACUATION_ZONES",
                        "incident_id": inc.incident_id,
                        "zone_label": f"SIMULATED EVACUATION ZONE — {inc.title}",
                        "severity_level": inc.severity_level,
                        "radius_km": round(effective_radius_km, 2),
                        "simulated_evacuees": inc.people_affected,
                        "disclaimer": "SIMULATED EVACUATION ZONE: Advisory simulation threshold only.",
                        "provenance": "PHASE_5G_SIMULATION"
                    }
                })
        return {
            "type": "FeatureCollection",
            "layer_name": "EVACUATION_ZONES",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_risk_zones_layer(
        incidents: List[IncidentIntakeInput],
        multiplier: float = 1.0
    ) -> Dict[str, Any]:
        """
        Layer 9: RISK_ZONES.
        Concentric deterministic simulation impact footprints (CRITICAL, HIGH, MEDIUM, LOW).
        """
        features = []
        zone_specs = [
            ("CRITICAL", 1.5 * multiplier, "Priority >= 80 or dist <= 1.5km"),
            ("HIGH", 3.5 * multiplier, "Priority >= 60 or dist <= 3.5km"),
            ("MEDIUM", 7.0 * multiplier, "Priority >= 40 or dist <= 7.0km"),
            ("LOW", 12.0 * multiplier, "Priority < 40 or dist <= 12.0km")
        ]

        for inc in incidents:
            for tier, r_km, rule in zone_specs:
                poly_coords = create_radial_polygon(inc.latitude, inc.longitude, r_km)
                features.append({
                    "type": "Feature",
                    "id": f"RISK_ZONE_{inc.incident_id}_{tier}",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [poly_coords]
                    },
                    "properties": {
                        "layer": "RISK_ZONES",
                        "incident_id": inc.incident_id,
                        "impact_tier": tier,
                        "radius_km": round(r_km, 2),
                        "threshold_definition": rule,
                        "classification": "SIMULATED IMPACT ZONE",
                        "provenance": "PHASE_5G_SPATIAL_PROPAGATION"
                    }
                })
        return {
            "type": "FeatureCollection",
            "layer_name": "RISK_ZONES",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_resource_routes_layer(
        response_result: IntegratedOptimizationResult,
        graph_engine: RoadGraphEngine,
        depots: List[DepotSupplyInput],
        incidents: List[IncidentIntakeInput]
    ) -> Dict[str, Any]:
        """
        Layer 10: RESOURCE_ROUTES.
        Renders the actual routes generated by Phase 5E without fabricating alternative geometry.
        """
        features = []
        if not response_result.routing_result or not response_result.routing_result.routes:
            return {
                "type": "FeatureCollection",
                "layer_name": "RESOURCE_ROUTES",
                "crs": "EPSG:4326",
                "features_count": 0,
                "features": []
            }

        # Build coordinate lookup maps
        node_coords = {
            n: (data.get("lat", 13.0827), data.get("lng", 80.2707))
            for n, data in graph_engine.graph.nodes(data=True)
        }
        depot_map = {d.depot_id: (d.latitude, d.longitude) for d in depots}
        inc_map = {inc.incident_id: (inc.latitude, inc.longitude) for inc in incidents}

        for route in response_result.routing_result.routes:
            # Build route coordinates from depot through each stop
            coords: List[List[float]] = []
            start_coord = depot_map.get(route.start_depot_id, (13.0810, 80.2710))
            coords.append([round(start_coord[1], 6), round(start_coord[0], 6)])

            for stop in route.stops:
                stop_coord = inc_map.get(stop.incident_id)
                if not stop_coord:
                    # Check nearest node if shelter demand
                    stop_coord = (13.0827, 80.2707)
                coords.append([round(stop_coord[1], 6), round(stop_coord[0], 6)])

            # Option A vehicle returns to start depot
            coords.append([round(start_coord[1], 6), round(start_coord[0], 6)])

            features.append({
                "type": "Feature",
                "id": route.route_id,
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                },
                "properties": {
                    "layer": "RESOURCE_ROUTES",
                    "route_id": route.route_id,
                    "vehicle_id": route.vehicle_id,
                    "vehicle_code": route.vehicle_code,
                    "vehicle_type": route.vehicle_type,
                    "start_depot_id": route.start_depot_id,
                    "stops_count": len(route.stops),
                    "total_distance_km": round(route.total_distance_km, 2),
                    "total_travel_time_min": round(route.total_travel_time_min, 2),
                    "weight_utilization_pct": route.weight_utilization_pct,
                    "provenance": "PHASE_5E_VEHICLE_ROUTING"
                }
            })

        return {
            "type": "FeatureCollection",
            "layer_name": "RESOURCE_ROUTES",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_volunteer_assignments_layer(
        response_result: IntegratedOptimizationResult,
        volunteers: List[VolunteerInput],
        incidents: List[IncidentIntakeInput],
        shelters: List[ShelterInput]
    ) -> Dict[str, Any]:
        """
        Layer 11: VOLUNTEER_ASSIGNMENTS.
        Renders assignment vectors from volunteer home locations to assigned incident/shelter tasks.
        """
        features = []
        if not response_result.volunteer_result or not response_result.volunteer_result.assignments:
            return {
                "type": "FeatureCollection",
                "layer_name": "VOLUNTEER_ASSIGNMENTS",
                "crs": "EPSG:4326",
                "features_count": 0,
                "features": []
            }

        vol_map = {v.volunteer_id: (v.latitude, v.longitude) for v in volunteers}
        target_map = {inc.incident_id: (inc.latitude, inc.longitude) for inc in incidents}
        for s in shelters:
            target_map[f"SHELTER_TASK_{s.shelter_id}"] = (s.latitude, s.longitude)
            target_map[s.shelter_id] = (s.latitude, s.longitude)

        for assign in response_result.volunteer_result.assignments:
            v_coord = vol_map.get(assign.volunteer_id, (13.0827, 80.2707))
            dest_coord = target_map.get(assign.incident_id, (13.0827, 80.2707))

            features.append({
                "type": "Feature",
                "id": f"VOL_ASSIGN_{assign.volunteer_id}_{assign.incident_id}",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(v_coord[1], 6), round(v_coord[0], 6)],
                        [round(dest_coord[1], 6), round(dest_coord[0], 6)]
                    ]
                },
                "properties": {
                    "layer": "VOLUNTEER_ASSIGNMENTS",
                    "volunteer_id": assign.volunteer_id,
                    "volunteer_name": assign.volunteer_name,
                    "target_id": assign.incident_id,
                    "skill_category": assign.skill_category,
                    "shift_id": assign.shift_id,
                    "transit_time_minutes": round(assign.transit_time_minutes, 1),
                    "transit_distance_km": round(assign.transit_distance_km, 2),
                    "provenance": "PHASE_5F_D_VOLUNTEER_OPTIMIZATION"
                }
            })

        return {
            "type": "FeatureCollection",
            "layer_name": "VOLUNTEER_ASSIGNMENTS",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @staticmethod
    def build_response_coverage_layer(
        graph_engine: RoadGraphEngine,
        depots: List[DepotSupplyInput],
        shelters: List[ShelterInput],
        max_transit_time_min: float = 30.0
    ) -> Dict[str, Any]:
        """
        Layer 12: RESPONSE_COVERAGE (30-MINUTE RESPONSE COVERAGE ENVELOPE).
        
        CRITICAL ARCHITECTURAL CONTRACT:
        - Terminology: '30-MINUTE RESPONSE COVERAGE ENVELOPE'.
        - It is an outer geometric visualization abstraction around reachable network locations.
        - NEVER claimed as exact point-by-point reachability for arbitrary interior terrain.
        - Preserves reachable graph node IDs in feature properties for factual spatial querying.
        """
        features = []
        origin_coords: List[Tuple[float, float]] = []

        # Find reachable road nodes within max_transit_time_min from depots and shelters
        reachable_nodes = set()
        speed_kmh = graph_engine.default_speed_kmh or 40.0
        max_dist_km = (max_transit_time_min / 60.0) * speed_kmh

        for d in depots:
            origin_coords.append((d.longitude, d.latitude))
            d_node = graph_engine.find_nearest_node(d.latitude, d.longitude)
            if d_node:
                reachable_nodes.add(d_node)

        for s in shelters:
            origin_coords.append((s.longitude, s.latitude))
            s_node = graph_engine.find_nearest_node(s.latitude, s.longitude)
            if s_node:
                reachable_nodes.add(s_node)

        # Collect reachable node coordinates
        envelope_points: List[Tuple[float, float]] = list(origin_coords)
        for n in reachable_nodes:
            if graph_engine.graph.has_node(n):
                lat = graph_engine.graph.nodes[n].get("lat", 13.0827)
                lng = graph_engine.graph.nodes[n].get("lng", 80.2707)
                # Expand buffer points representing the 30-min envelope
                radial_pts = create_radial_polygon(lat, lng, radius_km=max_dist_km, num_points=8)
                for pt in radial_pts:
                    envelope_points.append((pt[0], pt[1]))

        # Compute outer convex envelope
        hull_coords = compute_convex_hull(envelope_points)

        features.append({
            "type": "Feature",
            "id": "RESPONSE_COVERAGE_ENVELOPE_30MIN",
            "geometry": {
                "type": "Polygon",
                "coordinates": [hull_coords]
            },
            "properties": {
                "layer": "RESPONSE_COVERAGE",
                "label": "30-MINUTE RESPONSE COVERAGE ENVELOPE",
                "travel_time_threshold_min": max_transit_time_min,
                "reachable_network_nodes_count": len(reachable_nodes),
                "disclaimer": (
                    "30-MINUTE RESPONSE COVERAGE ENVELOPE: Visualization abstraction around reachable "
                    "network nodes. Does not guarantee that every interior coordinate off-network "
                    "is reachable within 30 minutes."
                ),
                "provenance": "PHASE_5G_GIS_SITUATION"
            }
        })

        return {
            "type": "FeatureCollection",
            "layer_name": "RESPONSE_COVERAGE",
            "crs": "EPSG:4326",
            "features_count": len(features),
            "features": features
        }

    @classmethod
    def build_all_12_layers(
        cls,
        incidents: List[IncidentIntakeInput],
        shelters: List[ShelterInput],
        depots: List[DepotSupplyInput],
        vehicles: List[VehicleInput],
        volunteers: List[VolunteerInput],
        graph_engine: RoadGraphEngine,
        response_result: Optional[IntegratedOptimizationResult] = None,
        area_multiplier: float = 1.0
    ) -> Dict[str, Dict[str, Any]]:
        """Constructs all 12 canonical GIS layers in a single pass."""
        dummy_result = response_result or IntegratedOptimizationResult(
            integration_run_id="EMPTY",
            graph_version=graph_engine.get_graph_version(),
            incident_ids=[inc.incident_id for inc in incidents],
            overall_status="PROPOSED",
            operational_feasibility="FEASIBLE"
        )

        return {
            "INCIDENTS": cls.build_incidents_layer(incidents),
            "SHELTERS": cls.build_shelters_layer(shelters),
            "DEPOTS": cls.build_depots_layer(depots),
            "VEHICLES": cls.build_vehicles_layer(vehicles),
            "VOLUNTEERS": cls.build_volunteers_layer(volunteers),
            "ROAD_NETWORK": cls.build_road_network_layer(graph_engine),
            "ROAD_BLOCKAGES": cls.build_road_blockages_layer(graph_engine),
            "EVACUATION_ZONES": cls.build_evacuation_zones_layer(incidents, multiplier=area_multiplier),
            "RISK_ZONES": cls.build_risk_zones_layer(incidents, multiplier=area_multiplier),
            "RESOURCE_ROUTES": cls.build_resource_routes_layer(dummy_result, graph_engine, depots, incidents),
            "VOLUNTEER_ASSIGNMENTS": cls.build_volunteer_assignments_layer(dummy_result, volunteers, incidents, shelters),
            "RESPONSE_COVERAGE": cls.build_response_coverage_layer(graph_engine, depots, shelters)
        }

    @classmethod
    def build_situation_layers(
        cls,
        operational_state: Any,
        active_layers: Optional[List[str]] = None,
        is_simulation: bool = False,
        response_result: Optional[IntegratedOptimizationResult] = None
    ) -> Dict[str, Any]:
        """
        Constructs an aggregate GeoJSON FeatureCollection containing features from the selected
        canonical layers for an operational state snapshot.
        """
        # Convert raw models to intake inputs if necessary
        incidents = []
        for inc in getattr(operational_state, 'incidents', []):
            if isinstance(inc, IncidentIntakeInput):
                incidents.append(inc)
            else:
                _people_affected = getattr(inc, 'people_affected', None)
                _vulnerable_count = getattr(inc, 'vulnerable_count', None)
                _injuries = getattr(inc, 'injuries', None)
                incidents.append(IncidentIntakeInput(
                    incident_id=str(getattr(inc, 'id', getattr(inc, 'incident_id', 'INC-1'))),
                    title=str(getattr(inc, 'title', 'Incident')),
                    latitude=float(getattr(inc, 'latitude', 13.0827)),
                    longitude=float(getattr(inc, 'longitude', 80.2707)),
                    disaster_type=str(getattr(inc, 'disaster_type', 'FLOOD')),
                    severity_level=str(getattr(inc, 'severity_level', 'CRITICAL')),
                    priority_score=float(getattr(inc, 'priority_score', 80.0) or 80.0),
                    people_affected=int(_people_affected) if _people_affected is not None else 50,
                    vulnerable_count=int(_vulnerable_count) if _vulnerable_count is not None else 10,
                    injuries=int(_injuries) if _injuries is not None else 5,
                    status=str(getattr(inc, 'status', 'REPORTED'))
                ))


        shelters = []
        for s in getattr(operational_state, 'shelters', []):
            if isinstance(s, ShelterInput):
                shelters.append(s)
            else:
                shelters.append(ShelterInput(
                    shelter_id=str(getattr(s, 'id', getattr(s, 'shelter_id', 'SH-1'))),
                    name=str(getattr(s, 'name', 'Shelter')),
                    latitude=float(getattr(s, 'latitude', 13.08)),
                    longitude=float(getattr(s, 'longitude', 80.27)),
                    total_capacity=int(getattr(s, 'total_capacity', 200)),
                    current_occupancy=int(getattr(s, 'current_occupancy', 0)),
                    status=str(getattr(s, 'status', 'OPEN'))
                ))

        depots = []
        for d in getattr(operational_state, 'depots', []):
            if isinstance(d, DepotSupplyInput):
                depots.append(d)
            elif isinstance(d, dict):
                depots.append(DepotSupplyInput(
                    depot_id=d.get("id", "DEPOT-1"),
                    name=d.get("name", "Depot"),
                    latitude=d.get("latitude", 13.085),
                    longitude=d.get("longitude", 80.27),
                    supplies=d.get("supplies", {"WATER": 1000.0, "FOOD": 500.0})
                ))
            else:
                depots.append(DepotSupplyInput(
                    depot_id=str(getattr(d, 'id', 'DEPOT-1')),
                    name=str(getattr(d, 'name', 'Depot')),
                    latitude=float(getattr(d, 'latitude', 13.085)),
                    longitude=float(getattr(d, 'longitude', 80.27)),
                    supplies={"WATER": 1000.0, "FOOD": 500.0}
                ))

        vehicles = []
        for v in getattr(operational_state, 'vehicles', []):
            if isinstance(v, VehicleInput):
                vehicles.append(v)
            elif isinstance(v, dict):
                vehicles.append(VehicleInput(
                    vehicle_id=v.get("id", "VEH-1"),
                    vehicle_code=v.get("vehicle_code", v.get("id", "VEH-1")),
                    vehicle_type=v.get("vehicle_type", "TRUCK_HEAVY"),
                    depot_id=v.get("depot_id", "depot-1"),
                    depot_lat=float(v.get("latitude", v.get("depot_lat", 13.085))),
                    depot_lng=float(v.get("longitude", v.get("depot_lng", 80.27))),
                    capacity_weight_kg=float(v.get("capacity_kg", v.get("capacity_weight_kg", 5000.0))),
                    capacity_volume_m3=float(v.get("capacity_volume_m3", 10.0)),
                    status=v.get("status", "AVAILABLE")
                ))

            else:
                vehicles.append(VehicleInput(
                    vehicle_id=str(getattr(v, 'id', getattr(v, 'vehicle_id', 'VEH-1'))),
                    vehicle_code=str(getattr(v, 'vehicle_code', getattr(v, 'id', 'VEH-1'))),
                    vehicle_type=str(getattr(v, 'vehicle_type', 'TRUCK_HEAVY')),
                    depot_id=str(getattr(v, 'depot_id', 'depot-1')),
                    depot_lat=float(getattr(v, 'depot_lat', getattr(v, 'latitude', 13.085))),
                    depot_lng=float(getattr(v, 'depot_lng', getattr(v, 'longitude', 80.27))),
                    capacity_weight_kg=float(getattr(v, 'capacity_kg', getattr(v, 'capacity_weight_kg', 5000.0))),
                    capacity_volume_m3=float(getattr(v, 'capacity_volume_m3', 10.0)),
                    status=str(getattr(v, 'status', 'AVAILABLE'))
                ))


        volunteers = []
        for vol in getattr(operational_state, 'volunteers', []):
            if isinstance(vol, VolunteerInput):
                volunteers.append(vol)
            elif isinstance(vol, dict):
                is_med = bool(vol.get("medical_certified", False))
                volunteers.append(VolunteerInput(
                    volunteer_id=str(vol.get("id", "VOL-1")),
                    name=str(vol.get("full_name", vol.get("name", "Volunteer"))),
                    latitude=float(vol.get("latitude", 13.082)),
                    longitude=float(vol.get("longitude", 80.272)),
                    skill_category="MEDICAL" if is_med else "GENERAL",
                    skills=["MEDICAL"] if is_med else ["GENERAL"],
                    medical_certified=is_med,
                    is_available=vol.get("status") == "AVAILABLE"
                ))
            else:
                is_med = bool(getattr(vol, 'medical_certified', False))
                volunteers.append(VolunteerInput(
                    volunteer_id=str(getattr(vol, 'id', 'VOL-1')),
                    name=str(getattr(vol, 'full_name', getattr(vol, 'name', 'Volunteer'))),
                    latitude=float(getattr(vol, 'latitude', 13.082)),
                    longitude=float(getattr(vol, 'longitude', 80.272)),
                    skill_category="MEDICAL" if is_med else "GENERAL",
                    skills=["MEDICAL"] if is_med else ["GENERAL"],
                    medical_certified=is_med,
                    is_available=bool(getattr(vol, 'is_available', True))
                ))

        graph_engine = getattr(operational_state, 'graph_engine')
        all_layers = cls.build_all_12_layers(
            incidents=incidents,
            shelters=shelters,
            depots=depots,
            vehicles=vehicles,
            volunteers=volunteers,
            graph_engine=graph_engine,
            response_result=response_result
        )

        selected_layer_names = active_layers or CANONICAL_GIS_LAYERS
        aggregated_features = []

        for l_name in selected_layer_names:
            if l_name in all_layers:
                layer_fc = all_layers[l_name]
                for feat in layer_fc.get("features", []):
                    f_copy = copy.deepcopy(feat)
                    if "properties" not in f_copy:
                        f_copy["properties"] = {}
                    f_copy["properties"]["layer_type"] = l_name
                    f_copy["properties"]["is_simulation"] = is_simulation
                    f_copy["properties"]["timestamp"] = datetime.now(timezone.utc).isoformat()
                    aggregated_features.append(f_copy)

        return {
            "type": "FeatureCollection",
            "crs": "EPSG:4326",
            "features_count": len(aggregated_features),
            "features": aggregated_features
        }

