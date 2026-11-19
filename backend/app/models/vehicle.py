import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_code = Column(String(50), unique=True, index=True, nullable=False)
    vehicle_type = Column(String(50), index=True, nullable=False) # TRUCK, AMBULANCE, BOAT, VAN, HELICOPTER
    owner_type = Column(String(50), default="GOVT") # GOVT, NGO, VOLUNTEER
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Payload Physical Capacities
    capacity_weight_kg = Column(Float, default=0.0)
    capacity_volume_m3 = Column(Float, default=0.0)
    
    # Location & Depot Base
    current_location_lat = Column(Float, nullable=True)
    current_location_lng = Column(Float, nullable=True)
    depot_id = Column(String(36), ForeignKey("resources.id"), nullable=True)
    
    # State & Availability Lifecycle
    # States: AVAILABLE, ASSIGNED, IN_TRANSIT, UNAVAILABLE, MAINTENANCE
    status = Column(String(50), default="AVAILABLE", index=True)
    is_active = Column(Boolean, default=True)
    
    # Operational bounds (e.g. {"flood_capable": true, "max_speed_kmh": 60})
    operational_constraints = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    owner = relationship("User", foreign_keys=[owner_id])
    depot = relationship("Resource", foreign_keys=[depot_id])
