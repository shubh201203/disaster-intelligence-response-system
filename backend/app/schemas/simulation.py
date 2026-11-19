"""
DIRS Phase 5G: Disaster Simulation & GIS Pydantic Schemas
Defines request/response contracts for scenarios, simulation execution, spatial queries, and multi-scenario comparisons.
Classification: SYNTHETIC CALIBRATED SIMULATION / DECISION SUPPORT
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ScenarioCreateRequest(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Coastal Breach & Route Cutoff"})
    description: Optional[str] = Field(None, json_schema_extra={"example": "Simulated 20% surge in affected population with key arterial road closure."})
    hazard_type: str = Field("FLOOD", json_schema_extra={"example": "FLOOD"})
    severity_multiplier: float = Field(1.0, ge=0.1, le=5.0)
    affected_area_multiplier: float = Field(1.0, ge=0.1, le=5.0)
    
    new_incidents: List[Dict[str, Any]] = Field(default_factory=list)
    additional_blockages: List[Dict[str, Any]] = Field(default_factory=list)
    shelter_capacity_changes: Dict[str, float] = Field(default_factory=dict)
    depot_supply_changes: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    vehicle_availability_changes: List[str] = Field(default_factory=list)
    volunteer_availability_changes: List[str] = Field(default_factory=list)
    seed: int = Field(42, json_schema_extra={"example": 42})


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    hazard_type: str
    severity_multiplier: float
    affected_area_multiplier: float
    scenario_parameters: Dict[str, Any]
    seed: int
    created_at: str


class SimulationRunRequest(BaseModel):
    scenario_id: Optional[str] = None
    inline_scenario: Optional[ScenarioCreateRequest] = None
    base_workload: str = Field("DIRS-GIS-10", json_schema_extra={"example": "DIRS-GIS-10"}) # DIRS-GIS-10, DIRS-GIS-25, DIRS-GIS-50, LIVE_DB
    seed: int = Field(42, json_schema_extra={"example": 42})


class SimulationAlert(BaseModel):
    condition: str
    metric: str
    base_value: float
    scenario_value: float
    absolute_change: float
    percentage_change: float
    threshold: float
    source: str
    explanation: str


class SimulationRunResponse(BaseModel):
    simulation_id: str
    scenario_id: Optional[str] = None
    scenario_name: str
    status: str = "PROPOSED" # Always PROPOSED / SIMULATION
    disclaimer: str = "SIMULATED IMPACT: This is a decision-support simulation. Live operational state is unmodified."
    base_state_hash: str
    result_hash: str
    graph_version: str
    seed: int
    delta: Dict[str, Any]
    intelligence_observations: List[str]
    critical_alerts: List[SimulationAlert]
    timing_breakdown: Dict[str, float]
    created_at: str


class MultiScenarioCompareRequest(BaseModel):
    scenario_ids: List[str] = Field(..., min_length=1)
    base_workload: str = Field("DIRS-GIS-10", json_schema_extra={"example": "DIRS-GIS-10"})
    seed: int = Field(42, json_schema_extra={"example": 42})


class ScenarioComparisonItem(BaseModel):
    scenario_id: str
    scenario_name: str
    delta_evacuees_sheltered: int
    delta_unmet_evacuation: int
    delta_resource_allocated: float
    delta_unmet_resources: float
    delta_vehicle_count: int
    delta_total_route_distance_km: float
    delta_total_response_time_min: float
    delta_unrouted_shipments: int
    delta_volunteers_deployed: int
    delta_unmet_volunteer_tasks: int
    delta_medical_unmet_tasks: int
    new_unreachable_locations_count: int
    new_isolated_shelters_count: int
    critical_alerts_count: int


class MultiScenarioCompareResponse(BaseModel):
    base_workload: str
    base_metrics: Dict[str, Any]
    comparisons: List[ScenarioComparisonItem]
    factual_observations: List[str]


class SpatialQueryRequest(BaseModel):
    query_type: str = Field(..., json_schema_extra={"example": "NEAREST_SHELTER"}) # NEAREST_SHELTER, NEAREST_DEPOT, NEAREST_VEHICLE, NEAREST_VOLUNTEER, INCIDENTS_IN_RADIUS, SHELTERS_IN_ZONE, POINT_IN_ZONE, BBOX
    latitude: Optional[float] = Field(None, json_schema_extra={"example": 13.0827})
    longitude: Optional[float] = Field(None, json_schema_extra={"example": 80.2707})
    radius_km: Optional[float] = Field(10.0, json_schema_extra={"example": 10.0})
    target_layer: Optional[str] = None
    k_nearest: Optional[int] = 3
    zone_polygon: Optional[List[List[float]]] = None # List of [lng, lat]
    bbox: Optional[List[float]] = None # [min_lng, min_lat, max_lng, max_lat]


class SpatialQueryResponse(BaseModel):
    query_type: str
    coordinate_reference_system: str = "WGS-84 / EPSG:4326"
    results_count: int
    features: List[Dict[str, Any]]
