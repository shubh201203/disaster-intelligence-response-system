from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class ShelterCreate(BaseModel):
    name: str
    address: str
    total_capacity: int = Field(default=100, gt=0)
    current_occupancy: int = Field(default=0, ge=0)
    latitude: float
    longitude: float
    has_medical: bool = True
    has_food: bool = True
    has_water: bool = True
    disaster_risk_level: str = "LOW"
    status: str = "OPEN"
    accessibility_features: Optional[bool] = False
    power_available: Optional[bool] = True
    sanitation_available: Optional[bool] = True
    disaster_compatibility: Optional[list[str]] = Field(default_factory=list)
    last_verified_at: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"OPEN", "FULL", "CLOSED"}
        if v not in allowed:
            raise ValueError(f"Invalid shelter status '{v}'. Must be one of {allowed}")
        return v

    @field_validator("disaster_compatibility")
    @classmethod
    def validate_disaster_compatibility(cls, v):
        if not v:
            return v
        allowed = {"FLOOD", "CYCLONE", "FIRE", "LANDSLIDE", "EARTHQUAKE"}
        for d in v:
            if d not in allowed:
                raise ValueError(f"Invalid disaster type '{d}' in compatibility list. Must be one of {allowed}")
        return v

class ShelterResponse(BaseModel):
    id: str
    name: str
    address: str
    total_capacity: int
    current_occupancy: int
    latitude: float
    longitude: float
    has_medical: bool
    has_food: bool
    has_water: bool
    disaster_risk_level: str
    status: str
    accessibility_features: Optional[bool] = False
    power_available: Optional[bool] = True
    sanitation_available: Optional[bool] = True
    disaster_compatibility: Optional[list[str]] = Field(default_factory=list)
    last_verified_at: Optional[datetime] = None
    remaining_capacity: Optional[int] = None
    suitability_score: Optional[float] = None
    distance_km: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True
