from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field, field_validator

class OptimizationRunCreate(BaseModel):
    objective_config_json: Dict[str, Any] = Field(default_factory=dict)
    input_snapshot_json: Dict[str, Any] = Field(default_factory=dict)
    solver_metadata_json: Dict[str, Any] = Field(default_factory=dict)

class OptimizationRecommendationBase(BaseModel):
    recommendation_type: str = Field(..., description="RESOURCE_DISPATCH, VEHICLE_ROUTE, SHELTER_EVACUATION, VOLUNTEER_ASSIGNMENT")
    incident_id: Optional[str] = None
    depot_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    shelter_id: Optional[str] = None
    volunteer_id: Optional[str] = None
    commodity_category: Optional[str] = None
    allocated_quantity: float = 0.0
    proposed_route_json: Dict[str, Any] = Field(default_factory=dict)
    objective_contribution: float = 0.0
    explanation: Optional[str] = None
    demographic_group: Optional[str] = Field(default=None, description="GEN, ACC, MED, MED_ACC for SHELTER_EVACUATION")
    skill_category: Optional[str] = Field(default=None, description="MEDICAL, RESCUE, LOGISTICS, GENERAL for VOLUNTEER_ASSIGNMENT")
    shift_id: Optional[str] = Field(default=None, description="e.g. SHIFT_1")
    transit_time_minutes: Optional[float] = Field(default=None, ge=0.0)
    transit_distance_km: Optional[float] = Field(default=None, ge=0.0)
    status: str = Field(default="PROPOSED", description="PROPOSED, APPROVED, REJECTED, MODIFIED")

    @field_validator("demographic_group")
    @classmethod
    def validate_demographic_group(cls, v):
        if v is not None:
            allowed = {"GEN", "ACC", "MED", "MED_ACC"}
            if v not in allowed:
                raise ValueError(f"Invalid demographic group '{v}'. Must be one of {allowed}")
        return v

    @field_validator("skill_category")
    @classmethod
    def validate_skill_category(cls, v):
        if v is not None:
            allowed = {"MEDICAL", "RESCUE", "LOGISTICS", "GENERAL"}
            if v not in allowed:
                raise ValueError(f"Invalid skill category '{v}'. Must be one of {allowed}")
        return v

class OptimizationRecommendationResponse(OptimizationRecommendationBase):
    id: str
    run_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OptimizationRunResponse(BaseModel):
    id: str
    status: str
    run_timestamp: datetime
    requesting_user_id: str
    objective_config_json: Dict[str, Any]
    input_snapshot_json: Dict[str, Any]
    solver_metadata_json: Dict[str, Any]
    runtime_ms: Optional[float] = None
    optimality_gap: Optional[float] = None
    feasibility_status: str
    graph_version: Optional[str] = None
    created_at: datetime
    recommendations: List[OptimizationRecommendationResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class OptimizationOverrideCreate(BaseModel):
    action: str = Field(..., description="APPROVE, MODIFY, REJECT")
    original_value_json: Dict[str, Any] = Field(default_factory=dict)
    overridden_value_json: Dict[str, Any] = Field(default_factory=dict)
    justification_reason: str = Field(..., min_length=5, description="Mandatory government user operational justification reason")

class OptimizationOverrideResponse(BaseModel):
    id: str
    run_id: str
    user_id: str
    action: str
    original_value_json: Dict[str, Any]
    overridden_value_json: Dict[str, Any]
    justification_reason: str
    audit_log_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
