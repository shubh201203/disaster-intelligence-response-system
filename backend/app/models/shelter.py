import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON
from geoalchemy2 import Geometry
from app.database import Base

class Shelter(Base):
    __tablename__ = "shelters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    total_capacity = Column(Integer, nullable=False, default=100)
    current_occupancy = Column(Integer, nullable=False, default=0)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geom = Column(Geometry(geometry_type='POINT', srid=4326, spatial_index=False, use_typmod=True), nullable=True)
    
    has_medical = Column(Boolean, default=True)
    has_food = Column(Boolean, default=True)
    has_water = Column(Boolean, default=True)
    disaster_risk_level = Column(String(50), default="LOW") # LOW, MEDIUM, HIGH
    status = Column(String(50), default="OPEN") # OPEN, FULL, CLOSED
    
    # Phase 5F Data Foundation Extensions
    accessibility_features = Column(Boolean, default=False, nullable=True) # Wheelchair / mobility access (A_s)
    power_available = Column(Boolean, default=True, nullable=True) # Generator / continuous power
    sanitation_available = Column(Boolean, default=True, nullable=True) # Functional sanitation facilities
    disaster_compatibility = Column(JSON, default=list, nullable=True) # e.g. ["FLOOD", "CYCLONE"]
    last_verified_at = Column(DateTime, nullable=True) # Timestamp of physical inspection
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
