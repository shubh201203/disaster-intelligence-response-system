import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database import Base

class RescueTask(Base):
    __tablename__ = "rescue_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    assigned_type = Column(String(50), nullable=False) # VOLUNTEER, NGO, GOVT_TEAM
    assigned_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="ASSIGNED") # ASSIGNED, ACCEPTED, EN_ROUTE, ARRIVED, RESCUE_STARTED, COMPLETED
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

class RoadBlockage(Base):
    __tablename__ = "road_blockages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    hazard_type = Column(String(100), nullable=False) # FLOOD, DEBRIS, COLLAPSED_BRIDGE, TREE_FALL
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    severity = Column(String(50), default="HIGH")
    
    # Phase 5B Dynamic Network Accessibility Fields
    blockage_status = Column(String(50), default="IMPASSABLE", index=True) # IMPASSABLE, DELAYED, CLEARING, RESOLVED
    effective_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expiry_at = Column(DateTime, nullable=True)
    delay_penalty_mins = Column(Float, default=0.0) # Penalty travel time in minutes for DELAYED state
    source = Column(String(100), default="FIELD_REPORT") # FIELD_REPORT, SATELLITE, GOVT
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    created_by = relationship("User", foreign_keys=[created_by_id])
