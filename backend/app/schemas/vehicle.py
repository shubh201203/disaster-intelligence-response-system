from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class VehicleBase(BaseModel):
    vehicle_code: str = Field(..., description="Unique vehicle code, e.g. VEH-TRK-001")
    vehicle_type: str = Field(..., description="Transport category: TRUCK, AMBULANCE, BOAT, VAN, HELICOPTER")
    owner_type: str = Field(default="GOVT", description="GOVT, NGO, VOLUNTEER")
    capacity_weight_kg: float = Field(default=0.0, ge=0.0, description="Max weight capacity in kg")
    capacity_volume_m3: float = Field(default=0.0, ge=0.0, description="Max volume capacity in m3")
    current_location_lat: Optional[float] = None
    current_location_lng: Optional[float] = None
    depot_id: Optional[str] = None
    status: str = Field(default="AVAILABLE", description="AVAILABLE, ASSIGNED, IN_TRANSIT, UNAVAILABLE, MAINTENANCE")
    is_active: bool = True
    operational_constraints: Dict[str, Any] = Field(default_factory=dict)

class VehicleCreate(VehicleBase):
    owner_id: Optional[str] = None

class VehicleUpdate(BaseModel):
    vehicle_type: Optional[str] = None
    capacity_weight_kg: Optional[float] = None
    capacity_volume_m3: Optional[float] = None
    current_location_lat: Optional[float] = None
    current_location_lng: Optional[float] = None
    depot_id: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    operational_constraints: Optional[Dict[str, Any]] = None

class VehicleResponse(VehicleBase):
    id: str
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
