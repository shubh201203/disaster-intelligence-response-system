"""
DIRS Phase 5G: GIS API Router
Exposes the 12 canonical GIS layers as GeoJSON FeatureCollections and provides spatial query endpoints.
Classification: SYNTHETIC CALIBRATED BENCHMARK / DECISION SUPPORT
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.ai.simulation.gis_situation import GISSituationLayerBuilder, CANONICAL_GIS_LAYERS
from app.ai.simulation.gis_query import SpatialQueryEngine
from app.ai.simulation.scenario_engine import OperationalStateSnapshot
from app.ai.optimization.integrated_benchmark_dataset import (
    generate_dirs_integrated_10,
    generate_dirs_integrated_25,
    generate_dirs_integrated_50
)
from app.ai.optimization.benchmark_graph import create_chennai_benchmark_graph
from app.schemas.simulation import SpatialQueryRequest, SpatialQueryResponse

router = APIRouter(prefix="/gis", tags=["GIS Situation & Spatial Operations"])


def _load_workload_state(workload: str) -> OperationalStateSnapshot:
    """Loads base operational state for benchmark tier."""
    if workload == "DIRS-GIS-25":
        incidents, shelters, depots, vehicles, volunteers = generate_dirs_integrated_25()
        graph = create_chennai_benchmark_graph(num_nodes=50, seed=42)
    elif workload == "DIRS-GIS-50":
        incidents, shelters, depots, vehicles, volunteers = generate_dirs_integrated_50()
        graph = create_chennai_benchmark_graph(num_nodes=100, seed=42)
    else: # Default DIRS-GIS-10
        incidents, shelters, depots, vehicles, volunteers = generate_dirs_integrated_10()
        graph = create_chennai_benchmark_graph(num_nodes=50, seed=42)

    return OperationalStateSnapshot(
        incidents=incidents,
        shelters=shelters,
        depots=depots,
        vehicles=vehicles,
        volunteers=volunteers,
        graph_engine=graph
    )


@router.get("/layers")
async def get_all_gis_layers(
    layers: Optional[str] = Query(None, description="Comma-separated list of layers to include"),
    workload: str = Query("DIRS-GIS-10", description="Benchmark workload tier"),
    multiplier: float = Query(1.0, ge=0.5, le=3.0, description="Spatial hazard zone multiplier")
) -> Dict[str, Any]:
    """
    Returns the canonical GIS situation layers formatted as a GeoJSON FeatureCollection:
    INCIDENTS, SHELTERS, DEPOTS, VEHICLES, VOLUNTEERS, ROAD_NETWORK,
    ROAD_BLOCKAGES, EVACUATION_ZONES, RISK_ZONES, RESOURCE_ROUTES,
    VOLUNTEER_ASSIGNMENTS, and RESPONSE_COVERAGE (30-min envelope).
    """
    state = _load_workload_state(workload)
    active_layers_list = [l.strip() for l in layers.split(",")] if layers else None
    fc = GISSituationLayerBuilder.build_situation_layers(state, active_layers=active_layers_list)
    return fc


@router.post("/spatial-query", response_model=SpatialQueryResponse)
async def execute_spatial_query(
    query_req: SpatialQueryRequest,
    workload: str = Query("DIRS-GIS-10")
) -> SpatialQueryResponse:
    """
    Executes a deterministic spatial query (nearest neighbor, radius, or zone containment).
    """
    state = _load_workload_state(workload)
    q_type = query_req.query_type.upper()
    features = []

    # Map generic KNN / NEAREST / RADIUS with target_layer to canonical query type
    if q_type in ["KNN", "NEAREST", "RADIUS", "RADIUS_QUERY", "WITHIN_RADIUS"]:
        target = (query_req.target_layer or ("incident" if "RADIUS" in q_type else "shelter")).lower()
        if "depot" in target:
            q_type = "NEAREST_DEPOT"
        elif "vehicle" in target:
            q_type = "NEAREST_VEHICLE"
        elif "volunteer" in target:
            q_type = "NEAREST_VOLUNTEER"
        elif "shelter" in target and "RADIUS" not in q_type:
            q_type = "NEAREST_SHELTER"
        else:
            q_type = "INCIDENTS_IN_RADIUS"

    if q_type == "NEAREST_SHELTER":
        if query_req.latitude is None or query_req.longitude is None:
            raise HTTPException(status_code=400, detail="latitude and longitude required for NEAREST_SHELTER")
        res = SpatialQueryEngine.nearest_shelter(query_req.latitude, query_req.longitude, state.shelters)
        if res:
            s, dist = res
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s.longitude, s.latitude]},
                "properties": {"shelter_id": s.shelter_id, "name": s.name, "distance_km": dist}
            })

    elif q_type == "NEAREST_DEPOT":
        if query_req.latitude is None or query_req.longitude is None:
            raise HTTPException(status_code=400, detail="latitude and longitude required for NEAREST_DEPOT")
        res = SpatialQueryEngine.nearest_depot(query_req.latitude, query_req.longitude, state.depots)
        if res:
            d, dist = res
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [d.longitude, d.latitude]},
                "properties": {"depot_id": d.depot_id, "name": d.name, "distance_km": dist}
            })

    elif q_type == "NEAREST_VEHICLE":
        if query_req.latitude is None or query_req.longitude is None:
            raise HTTPException(status_code=400, detail="latitude and longitude required for NEAREST_VEHICLE")
        res = SpatialQueryEngine.nearest_vehicle(query_req.latitude, query_req.longitude, state.vehicles)
        if res:
            v, dist = res
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [v.depot_lng, v.depot_lat]},
                "properties": {"vehicle_id": v.vehicle_id, "name": f"Vehicle {v.vehicle_id} ({v.vehicle_type})", "distance_km": dist}
            })

    elif q_type == "NEAREST_VOLUNTEER":
        if query_req.latitude is None or query_req.longitude is None:
            raise HTTPException(status_code=400, detail="latitude and longitude required for NEAREST_VOLUNTEER")
        res = SpatialQueryEngine.nearest_volunteer(query_req.latitude, query_req.longitude, state.volunteers)
        if res:
            vol, dist = res
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [vol.longitude, vol.latitude]},
                "properties": {"volunteer_id": vol.volunteer_id, "name": f"Volunteer {vol.volunteer_id}", "distance_km": dist}
            })

    elif q_type == "INCIDENTS_IN_RADIUS":
        if query_req.latitude is None or query_req.longitude is None:
            raise HTTPException(status_code=400, detail="latitude and longitude required for INCIDENTS_IN_RADIUS")
        matches = SpatialQueryEngine.incidents_within_radius(
            query_req.latitude, query_req.longitude, query_req.radius_km or 10.0, state.incidents
        )
        for inc, dist in matches:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [inc.longitude, inc.latitude]},
                "properties": {
                    "incident_id": inc.incident_id,
                    "title": inc.title,
                    "distance_km": dist,
                    "severity": inc.severity_level
                }
            })

    elif q_type == "SHELTERS_IN_ZONE":
        if not query_req.zone_polygon:
            raise HTTPException(status_code=400, detail="zone_polygon required for SHELTERS_IN_ZONE")
        matched_shelters = SpatialQueryEngine.shelters_inside_zone(query_req.zone_polygon, state.shelters)
        for s in matched_shelters:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s.longitude, s.latitude]},
                "properties": {"shelter_id": s.shelter_id, "name": s.name, "capacity": s.total_capacity}
            })

    elif q_type == "BBOX":
        if not query_req.bbox or len(query_req.bbox) != 4:
            raise HTTPException(status_code=400, detail="bbox [min_lng, min_lat, max_lng, max_lat] required")
        min_lng, min_lat, max_lng, max_lat = query_req.bbox
        builder_fc = GISSituationLayerBuilder.build_situation_layers(state)
        features = SpatialQueryEngine.bounding_box_filter(min_lng, min_lat, max_lng, max_lat, builder_fc.get("features", []))

    return SpatialQueryResponse(
        query_type=q_type,
        coordinate_reference_system="WGS-84 / EPSG:4326",
        results_count=len(features),
        features=features
    )
