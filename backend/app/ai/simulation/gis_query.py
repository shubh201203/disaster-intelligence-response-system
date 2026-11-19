"""
DIRS Phase 5G: Reusable Spatial Query Service
Implements deterministic WGS-84 geometric queries (nearest-neighbor, point-in-zone,
radius containment, bounding box, road-zone intersection, and route-blockage intersection).
Classification: SYNTHETIC CALIBRATED BENCHMARK / SPATIAL INTELLIGENCE
"""
import math
from typing import List, Dict, Any, Optional, Tuple

from app.ai.optimization.orchestrator import IncidentIntakeInput
from app.ai.optimization.shelter import ShelterInput
from app.ai.optimization.allocation import DepotSupplyInput
from app.ai.optimization.routing import VehicleInput
from app.ai.optimization.volunteer import VolunteerInput
from app.ai.optimization.graph import RoadGraphEngine
from app.ai.simulation.gis_situation import haversine_distance


# ------------------------------------------------------------------------------
# 1. Core Geometric Operators (Point in Polygon & Line Intersection)
# ------------------------------------------------------------------------------

def point_in_polygon(px: float, py: float, polygon: List[List[float]]) -> bool:
    """
    Determines if point (px=lng, py=lat) is inside polygon using Ray Casting Algorithm.
    polygon is list of [lng, lat] vertices.
    """
    if len(polygon) < 3:
        return False

    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0]

    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if py > min(p1y, p2y):
            if py <= max(p1y, p2y):
                if px <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or px <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def line_intersects_bbox(
    x1: float, y1: float, x2: float, y2: float,
    min_x: float, min_y: float, max_x: float, max_y: float
) -> bool:
    """Fast bounding box test for line segment."""
    if max(x1, x2) < min_x or min(x1, x2) > max_x:
        return False
    if max(y1, y2) < min_y or min(y1, y2) > max_y:
        return False
    return True


def line_segment_intersects_polygon(
    x1: float, y1: float, x2: float, y2: float, polygon: List[List[float]]
) -> bool:
    """Checks if line segment (x1, y1)-(x2, y2) intersects polygon or has endpoints inside."""
    if point_in_polygon(x1, y1, polygon) or point_in_polygon(x2, y2, polygon):
        return True

    # Check intersection with any polygon edge
    n = len(polygon)
    for i in range(n - 1):
        x3, y3 = polygon[i]
        x4, y4 = polygon[i + 1]
        if line_segments_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
            return True
    return False


def line_segments_intersect(
    x1: float, y1: float, x2: float, y2: float,
    x3: float, y3: float, x4: float, y4: float
) -> bool:
    """Tests if segment 1-2 intersects segment 3-4 using vector cross product."""
    def ccw(ax, ay, bx, by, cx, cy):
        return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)

    return (ccw(x1, y1, x3, y3, x4, y4) != ccw(x2, y2, x3, y3, x4, y4) and
            ccw(x1, y1, x2, y2, x3, y3) != ccw(x1, y1, x2, y2, x4, y4))


# ------------------------------------------------------------------------------
# 2. Reusable Spatial Query Service
# ------------------------------------------------------------------------------

class SpatialQueryEngine:
    """
    Deterministic spatial query service for disaster management entities.
    Operates consistently over WGS-84 coordinates.
    """

    @staticmethod
    def nearest_shelter(
        lat: float, lng: float, shelters: List[ShelterInput]
    ) -> Optional[Tuple[ShelterInput, float]]:
        """Returns the nearest shelter and its great-circle distance in km."""
        if not shelters:
            return None
        best_s = None
        best_dist = float("inf")
        for s in shelters:
            d = haversine_distance(lat, lng, s.latitude, s.longitude)
            if d < best_dist:
                best_dist = d
                best_s = s
        return (best_s, round(best_dist, 3)) if best_s else None

    @staticmethod
    def nearest_depot(
        lat: float, lng: float, depots: List[DepotSupplyInput]
    ) -> Optional[Tuple[DepotSupplyInput, float]]:
        """Returns the nearest depot and its great-circle distance in km."""
        if not depots:
            return None
        best_d = None
        best_dist = float("inf")
        for d in depots:
            dist = haversine_distance(lat, lng, d.latitude, d.longitude)
            if dist < best_dist:
                best_dist = dist
                best_d = d
        return (best_d, round(best_dist, 3)) if best_d else None

    @staticmethod
    def nearest_vehicle(
        lat: float, lng: float, vehicles: List[VehicleInput]
    ) -> Optional[Tuple[VehicleInput, float]]:
        """Returns the nearest available vehicle and distance in km."""
        avail = [v for v in vehicles if v.status == "AVAILABLE"]
        if not avail:
            return None
        best_v = None
        best_dist = float("inf")
        for v in avail:
            dist = haversine_distance(lat, lng, v.depot_lat, v.depot_lng)
            if dist < best_dist:
                best_dist = dist
                best_v = v
        return (best_v, round(best_dist, 3)) if best_v else None

    @staticmethod
    def nearest_volunteer(
        lat: float, lng: float, volunteers: List[VolunteerInput]
    ) -> Optional[Tuple[VolunteerInput, float]]:
        """Returns the nearest volunteer and distance in km."""
        avail = [vol for vol in volunteers if vol.is_available]
        if not avail:
            return None
        best_vol = None
        best_dist = float("inf")
        for vol in volunteers:
            dist = haversine_distance(lat, lng, vol.latitude, vol.longitude)
            if dist < best_dist:
                best_dist = dist
                best_vol = vol
        return (best_vol, round(best_dist, 3)) if best_vol else None

    @staticmethod
    def incidents_within_radius(
        lat: float, lng: float, radius_km: float, incidents: List[IncidentIntakeInput]
    ) -> List[Tuple[IncidentIntakeInput, float]]:
        """Returns incidents within radius_km sorted by ascending distance."""
        matches = []
        for inc in incidents:
            d = haversine_distance(lat, lng, inc.latitude, inc.longitude)
            if d <= radius_km:
                matches.append((inc, round(d, 3)))
        matches.sort(key=lambda x: x[1])
        return matches

    @staticmethod
    def shelters_inside_zone(
        zone_polygon: List[List[float]], shelters: List[ShelterInput]
    ) -> List[ShelterInput]:
        """Returns shelters located inside the given polygon [lng, lat]."""
        return [s for s in shelters if point_in_polygon(s.longitude, s.latitude, zone_polygon)]

    @staticmethod
    def depots_inside_zone(
        zone_polygon: List[List[float]], depots: List[DepotSupplyInput]
    ) -> List[DepotSupplyInput]:
        """Returns depots located inside the given polygon [lng, lat]."""
        return [d for d in depots if point_in_polygon(d.longitude, d.latitude, zone_polygon)]

    @staticmethod
    def roads_intersecting_zone(
        zone_polygon: List[List[float]], graph_engine: RoadGraphEngine
    ) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Returns road edges (u, v, data) that intersect or lie inside the given polygon."""
        intersecting = []
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

            if line_segment_intersects_polygon(u_lng, u_lat, v_lng, v_lat, zone_polygon):
                intersecting.append((u, v, data))

        return intersecting

    @staticmethod
    def bounding_box_filter(
        min_lng: float, min_lat: float, max_lng: float, max_lat: float,
        features: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filters GeoJSON features that intersect with the bounding box [min_lng, min_lat, max_lng, max_lat]."""
        results = []
        for feat in features:
            geom = feat.get("geometry", {})
            g_type = geom.get("type")
            coords = geom.get("coordinates", [])

            if g_type == "Point":
                lng, lat = coords[0], coords[1]
                if min_lng <= lng <= max_lng and min_lat <= lat <= max_lat:
                    results.append(feat)
            elif g_type == "LineString":
                # Check if any coordinate is inside or intersects bbox
                if any(min_lng <= pt[0] <= max_lng and min_lat <= pt[1] <= max_lat for pt in coords):
                    results.append(feat)
            elif g_type == "Polygon":
                # Check ring coordinates
                ring = coords[0] if coords else []
                if any(min_lng <= pt[0] <= max_lng and min_lat <= pt[1] <= max_lat for pt in ring):
                    results.append(feat)
        return results

    @staticmethod
    def routes_intersecting_blocked_areas(
        routes: List[Dict[str, Any]],
        graph_engine: RoadGraphEngine
    ) -> List[Dict[str, Any]]:
        """Identifies routes that intersect newly impassable or delayed edges."""
        blockage_dict = getattr(graph_engine, 'active_blockages', getattr(graph_engine, 'blockages', {}))
        impassable_edges = set()
        for b in blockage_dict.values():
            if isinstance(b, dict):
                u = b.get("source_id", b.get("u"))
                v = b.get("target_id", b.get("v"))
                st = b.get("blockage_status", b.get("status", "IMPASSABLE"))
            else:
                u = getattr(b, "u", getattr(b, "source_id", None))
                v = getattr(b, "v", getattr(b, "target_id", None))
                st = getattr(b, "status", getattr(b, "blockage_status", "IMPASSABLE"))
            if st == "IMPASSABLE" and u and v:
                impassable_edges.add((u, v))
                impassable_edges.add((v, u))

        for r in routes:
            disrupted = []
            stops = r.get("stops", [])
            for i in range(len(stops) - 1):
                s1 = stops[i].get("incident_id")
                s2 = stops[i + 1].get("incident_id")
                if (s1, s2) in impassable_edges:
                    disrupted.append(r)
                    break
        return disrupted


    # Convenience method aliases for spatial operations
    @staticmethod
    def point_in_polygon(point: Any, polygon: List[Any]) -> bool:
        px = point[0] if isinstance(point, (list, tuple)) else point.x
        py = point[1] if isinstance(point, (list, tuple)) else point.y
        poly_clean = []
        for p in polygon:
            if isinstance(p, (list, tuple)):
                poly_clean.append([float(p[0]), float(p[1])])
        return point_in_polygon(px, py, poly_clean)

    @staticmethod
    def line_segments_intersect(p1: Any, p2: Any, p3: Any, p4: Any) -> bool:
        return line_segments_intersect(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], p4[0], p4[1])

    @staticmethod
    def find_nearest_shelters(state: Any, query_lat: float, query_lng: float, k: int = 3) -> List[Dict[str, Any]]:
        results = []
        for s in getattr(state, 'shelters', []):
            s_id = str(getattr(s, 'id', getattr(s, 'shelter_id', 'SH-1')))
            s_lat = float(getattr(s, 'latitude', 13.08))
            s_lng = float(getattr(s, 'longitude', 80.27))
            d = haversine_distance(query_lat, query_lng, s_lat, s_lng)
            results.append({"id": s_id, "name": getattr(s, 'name', 'Shelter'), "distance_km": round(d, 3), "lat": s_lat, "lng": s_lng})
        results.sort(key=lambda x: x["distance_km"])
        return results[:k]

    @staticmethod
    def find_nearest_depots(state: Any, query_lat: float, query_lng: float, k: int = 3) -> List[Dict[str, Any]]:
        results = []
        for d in getattr(state, 'depots', []):
            d_id = str(d.get("id") if isinstance(d, dict) else getattr(d, 'depot_id', getattr(d, 'id', 'D-1')))
            d_lat = float(d.get("latitude") if isinstance(d, dict) else getattr(d, 'latitude', 13.085))
            d_lng = float(d.get("longitude") if isinstance(d, dict) else getattr(d, 'longitude', 80.27))
            dist = haversine_distance(query_lat, query_lng, d_lat, d_lng)
            results.append({"id": d_id, "distance_km": round(dist, 3), "lat": d_lat, "lng": d_lng})
        results.sort(key=lambda x: x["distance_km"])
        return results[:k]

    @staticmethod
    def find_nearest_vehicles(state: Any, query_lat: float, query_lng: float, k: int = 3) -> List[Dict[str, Any]]:
        results = []
        for v in getattr(state, 'vehicles', []):
            v_id = str(v.get("id") if isinstance(v, dict) else getattr(v, 'vehicle_id', getattr(v, 'id', 'V-1')))
            v_lat = float(v.get("latitude") if isinstance(v, dict) else getattr(v, 'latitude', getattr(v, 'depot_lat', 13.085)))
            v_lng = float(v.get("longitude") if isinstance(v, dict) else getattr(v, 'longitude', getattr(v, 'depot_lng', 80.27)))
            dist = haversine_distance(query_lat, query_lng, v_lat, v_lng)
            results.append({"id": v_id, "distance_km": round(dist, 3), "lat": v_lat, "lng": v_lng})
        results.sort(key=lambda x: x["distance_km"])
        return results[:k]

    @staticmethod
    def find_nearest_volunteers(state: Any, query_lat: float, query_lng: float, k: int = 3, medical_only: bool = False) -> List[Dict[str, Any]]:
        results = []
        for vol in getattr(state, 'volunteers', []):
            is_med = vol.get("medical_certified") if isinstance(vol, dict) else ("MEDICAL" in getattr(vol, 'skills', []))
            if medical_only and not is_med:
                continue
            vol_id = str(vol.get("id") if isinstance(vol, dict) else getattr(vol, 'volunteer_id', getattr(vol, 'id', 'VOL-1')))
            vol_lat = float(vol.get("latitude") if isinstance(vol, dict) else getattr(vol, 'latitude', 13.082))
            vol_lng = float(vol.get("longitude") if isinstance(vol, dict) else getattr(vol, 'longitude', 80.272))
            dist = haversine_distance(query_lat, query_lng, vol_lat, vol_lng)
            results.append({"id": vol_id, "distance_km": round(dist, 3), "medical": is_med, "lat": vol_lat, "lng": vol_lng})
        results.sort(key=lambda x: x["distance_km"])
        return results[:k]

    @classmethod
    def filter_features_by_radius(cls, features: List[Dict[str, Any]], center_lat: float, center_lng: float, radius_km: float) -> List[Dict[str, Any]]:
        results = []
        for feat in features:
            geom = feat.get("geometry", {})
            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
                    dist = haversine_distance(center_lat, center_lng, lat, lng)
                    if dist <= radius_km:
                        results.append(feat)
        return results

    @classmethod
    def filter_features_by_bbox(cls, features: List[Dict[str, Any]], min_lng: float, min_lat: float, max_lng: float, max_lat: float) -> List[Dict[str, Any]]:
        return cls.bounding_box_filter(min_lng, min_lat, max_lng, max_lat, features)

    @classmethod
    def route_intersects_blockage(cls, route_coords: List[Any], blockage_poly: List[Any]) -> bool:
        poly_clean = [[float(p[0]), float(p[1])] for p in blockage_poly]
        for i in range(len(route_coords) - 1):
            p1 = route_coords[i]
            p2 = route_coords[i + 1]
            if line_segment_intersects_polygon(p1[0], p1[1], p2[0], p2[1], poly_clean):
                return True
        return False

