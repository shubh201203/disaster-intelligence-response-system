from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ResourceCreate(BaseModel):
    owner_type: str = "NGO" # NGO, GOVT
    category: str # FOOD, WATER, MEDICINE, CLOTHING, VEHICLE, GENERATOR
    resource_name: str
    total_quantity: int = Field(..., gt=0)
    unit: str = "units"
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None

class ResourceResponse(BaseModel):
    id: str
    owner_type: str
    owner_id: str
    category: str
    resource_name: str
    total_quantity: int
    available_quantity: int
    unit: str
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ResourceRequestCreate(BaseModel):
    incident_id: str
    category: str
    quantity_requested: int
    priority: str = "HIGH"
