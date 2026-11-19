from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AlertCreate(BaseModel):
    title: str
    message: str
    alert_type: str = "WARNING" # EVACUATION, WARNING, SHELTER, GENERAL
    target_zone_lat: Optional[float] = None
    target_zone_lng: Optional[float] = None
    radius_km: float = 10.0

class AlertResponse(BaseModel):
    id: str
    title: str
    message: str
    alert_type: str
    target_zone_lat: Optional[float] = None
    target_zone_lng: Optional[float] = None
    radius_km: float
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True
