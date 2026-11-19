from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class IncidentCreate(BaseModel):
    title: str = Field(..., example="Severe Flooding near Riverfront Road")
    disaster_type: str = Field(..., example="FLOOD") # FLOOD, CYCLONE, FIRE, LANDSLIDE, EARTHQUAKE
    description: str
    latitude: float
    longitude: float
    location_address: Optional[str] = None
    people_affected: int = Field(default=1, ge=0)
    injuries: int = Field(default=0, ge=0)
    vulnerable_count: int = Field(default=0, ge=0)
    infrastructure_damage: Optional[str] = None
    media_urls: List[str] = []
    required_skills: Optional[Dict[str, int]] = Field(default_factory=dict)
    evacuation_demographics: Optional[Dict[str, int]] = Field(default_factory=dict)

    @field_validator("evacuation_demographics")
    @classmethod
    def validate_demographics(cls, v):
        if not v:
            return v
        allowed_groups = {"GEN", "ACC", "MED", "MED_ACC"}
        for group, count in v.items():
            if group not in allowed_groups:
                raise ValueError(f"Unknown demographic group '{group}'. Must be one of {allowed_groups}")
            if count < 0:
                raise ValueError(f"Demographic population count for '{group}' must be non-negative (got {count})")
        return v

    @field_validator("required_skills")
    @classmethod
    def validate_required_skills(cls, v):
        if not v:
            return v
        allowed_skills = {"MEDICAL", "RESCUE", "LOGISTICS", "GENERAL"}
        for skill, count in v.items():
            if skill not in allowed_skills:
                raise ValueError(f"Unknown skill category '{skill}'. Must be one of {allowed_skills}")
            if count < 0:
                raise ValueError(f"Required volunteer count for skill '{skill}' must be non-negative (got {count})")
        return v

    @model_validator(mode="after")
    def validate_demographic_conservation(self):
        if self.evacuation_demographics:
            total_evacuees = sum(self.evacuation_demographics.values())
            if total_evacuees > self.people_affected:
                raise ValueError(
                    f"Inconsistent demographic totals: sum of evacuation demographics ({total_evacuees}) "
                    f"exceeds total people_affected ({self.people_affected})."
                )
        return self

class IncidentVerifyRequest(BaseModel):
    action: str = Field(..., example="VERIFY") # VERIFY or REJECT
    status: str = Field(default="VERIFIED")
    notes: Optional[str] = None

class IncidentMergeRequest(BaseModel):
    duplicate_incident_ids: List[str]

class IncidentResponse(BaseModel):
    id: str
    incident_code: str
    title: str
    disaster_type: str
    description: str
    status: str
    priority_level: str
    priority_score: float
    severity_level: str
    confidence_score: float
    latitude: float
    longitude: float
    location_address: Optional[str] = None
    people_affected: int
    injuries: int
    vulnerable_count: int
    infrastructure_damage: Optional[str] = None
    media_urls: List[str] = []
    required_skills: Optional[Dict[str, int]] = Field(default_factory=dict)
    evacuation_demographics: Optional[Dict[str, int]] = Field(default_factory=dict)
    ai_breakdown: Dict[str, Any] = {}
    cv_evidence_tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True
