from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: str
    full_name: str
    role: str = "CITIZEN"
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class CitizenProfileResponse(BaseModel):
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class VolunteerProfileResponse(BaseModel):
    skills: List[str] = []
    skill_category: str = "GENERAL"
    assignment_status: str = "UNASSIGNED"
    experience_years: int = 0
    vehicle_type: Optional[str] = None
    medical_certified: bool = False
    verification_status: str = "PENDING"
    is_available: bool = True
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    max_shift_hours: Optional[float] = Field(default=8.0, gt=0.0)
    max_travel_time_mins: Optional[float] = Field(default=45.0, gt=0.0)
    shift_availability: Optional[List[str]] = []

    @field_validator("skill_category")
    @classmethod
    def validate_skill_category(cls, v):
        allowed = {"MEDICAL", "RESCUE", "LOGISTICS", "GENERAL"}
        if v not in allowed:
            raise ValueError(f"Invalid skill category '{v}'. Must be one of {allowed}")
        return v

class NGOProfileResponse(BaseModel):
    org_name: str
    registration_no: Optional[str] = None
    contact_person: Optional[str] = None
    verified: bool = False

class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    citizen_profile: Optional[CitizenProfileResponse] = None
    volunteer_profile: Optional[VolunteerProfileResponse] = None
    ngo_profile: Optional[NGOProfileResponse] = None

    class Config:
        from_attributes = True

Token.model_rebuild()
