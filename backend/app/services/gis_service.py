import math
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint, ST_SetSRID
from app.models.incident import Incident
from app.models.shelter import Shelter
from app.ai.simulation.gis_query import (
    SpatialQueryEngine,
    point_in_polygon,
    line_segment_intersects_polygon
)

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Fallback Haversine calculation for non-PostGIS memory operations
    R = 6371.0 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class GISService:
    @staticmethod
    def get_nearby_incidents(db: Session, lat: float, lng: float, radius_km: float = 10.0) -> List[Tuple[Incident, float]]:
        radius_meters = radius_km * 1000.0
        point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)

        try:
            # PostGIS spatial query
            results = (
                db.query(Incident, ST_Distance(Incident.geom, point))
                .filter(ST_DWithin(Incident.geom, point, radius_meters))
                .all()
            )
            return [(inc, dist / 1000.0) for inc, dist in results]
        except Exception:
            # Fallback memory query
            all_incidents = db.query(Incident).all()
            nearby = []
            for inc in all_incidents:
                dist = haversine_distance_km(lat, lng, inc.latitude, inc.longitude)
                if dist <= radius_km:
                    nearby.append((inc, dist))
            return nearby

    @staticmethod
    def get_nearby_shelters(db: Session, lat: float, lng: float, radius_km: float = 15.0) -> List[Tuple[Shelter, float]]:
        radius_meters = radius_km * 1000.0
        point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)

        try:
            results = (
                db.query(Shelter, ST_Distance(Shelter.geom, point))
                .filter(ST_DWithin(Shelter.geom, point, radius_meters))
                .all()
            )
            return [(s, dist / 1000.0) for s, dist in results]
        except Exception:
            all_shelters = db.query(Shelter).filter(Shelter.status == "OPEN").all()
            nearby = []
            for s in all_shelters:
                dist = haversine_distance_km(lat, lng, s.latitude, s.longitude)
                if dist <= radius_km:
                    nearby.append((s, dist))
            return nearby

    # Phase 5G Extensions (Delegates to SpatialQueryEngine)
    @staticmethod
    def nearest_shelter(lat: float, lng: float, shelters: list):
        return SpatialQueryEngine.nearest_shelter(lat, lng, shelters)

    @staticmethod
    def nearest_depot(lat: float, lng: float, depots: list):
        return SpatialQueryEngine.nearest_depot(lat, lng, depots)

    @staticmethod
    def nearest_vehicle(lat: float, lng: float, vehicles: list):
        return SpatialQueryEngine.nearest_vehicle(lat, lng, vehicles)

    @staticmethod
    def nearest_volunteer(lat: float, lng: float, volunteers: list):
        return SpatialQueryEngine.nearest_volunteer(lat, lng, volunteers)

    @staticmethod
    def incidents_within_radius(lat: float, lng: float, radius_km: float, incidents: list):
        return SpatialQueryEngine.incidents_within_radius(lat, lng, radius_km, incidents)

    @staticmethod
    def shelters_inside_zone(zone_polygon: list, shelters: list):
        return SpatialQueryEngine.shelters_inside_zone(zone_polygon, shelters)

    @staticmethod
    def depots_inside_zone(zone_polygon: list, depots: list):
        return SpatialQueryEngine.depots_inside_zone(zone_polygon, depots)

    @staticmethod
    def roads_intersecting_zone(zone_polygon: list, graph_engine):
        return SpatialQueryEngine.roads_intersecting_zone(zone_polygon, graph_engine)

    @staticmethod
    def bounding_box_filter(min_lng: float, min_lat: float, max_lng: float, max_lat: float, features: list):
        return SpatialQueryEngine.bounding_box_filter(min_lng, min_lat, max_lng, max_lat, features)

    @staticmethod
    def routes_intersecting_blocked_areas(routes: list, graph_engine):
        return SpatialQueryEngine.routes_intersecting_blocked_areas(routes, graph_engine)
