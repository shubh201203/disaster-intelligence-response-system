import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class UserRole(str, SQLEnum):
    CITIZEN = "CITIZEN"
    VOLUNTEER = "VOLUNTEER"
    NGO = "NGO"
    GOVT = "GOVT"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.CITIZEN)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    citizen_profile = relationship("CitizenProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    volunteer_profile = relationship("VolunteerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    ngo_profile = relationship("NGOProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

class CitizenProfile(Base):
    __tablename__ = "citizen_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    user = relationship("User", back_populates="citizen_profile")

class VolunteerProfile(Base):
    __tablename__ = "volunteer_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    skills = Column(JSON, default=list) # e.g. ["First Aid", "Water Rescue"]
    
    # Phase 5B Structured Optimization Fields
    skill_category = Column(String(50), default="GENERAL", index=True) # MEDICAL, RESCUE, LOGISTICS, GENERAL
    assignment_status = Column(String(50), default="UNASSIGNED", index=True) # UNASSIGNED, ASSIGNED, ON_MISSION
    
    experience_years = Column(Integer, default=0)
    vehicle_type = Column(String(100), nullable=True)
    medical_certified = Column(Boolean, default=False)
    verification_status = Column(String(50), default="PENDING") # PENDING, VERIFIED, REJECTED
    is_available = Column(Boolean, default=True)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)

    # Phase 5F Data Foundation Extensions
    max_shift_hours = Column(Float, default=8.0, nullable=True) # Maximum shift workload in hours (W_v^max)
    max_travel_time_mins = Column(Float, default=45.0, nullable=True) # Maximum transit time in minutes (tau_v^max)
    shift_availability = Column(JSON, default=list, nullable=True) # e.g. ["SHIFT_1", "SHIFT_2"] (A_vt)

    user = relationship("User", back_populates="volunteer_profile")

class NGOProfile(Base):
    __tablename__ = "ngo_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    org_name = Column(String(255), nullable=False)
    registration_no = Column(String(100), nullable=True)
    contact_person = Column(String(255), nullable=True)
    address = Column(String(500), nullable=True)
    verified = Column(Boolean, default=False)

    user = relationship("User", back_populates="ngo_profile")
