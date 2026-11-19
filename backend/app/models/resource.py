import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime
from app.database import Base

class Resource(Base):
    __tablename__ = "resources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_type = Column(String(50), nullable=False, default="NGO") # NGO, GOVT
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    category = Column(String(100), nullable=False) # FOOD, WATER, MEDICINE, CLOTHING, VEHICLE, GENERATOR
    resource_name = Column(String(255), nullable=False)
    total_quantity = Column(Integer, nullable=False, default=0)
    available_quantity = Column(Integer, nullable=False, default=0)
    unit = Column(String(50), default="units") # packets, liters, boxes, units
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ResourceRequest(Base):
    __tablename__ = "resource_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    requester_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    category = Column(String(100), nullable=False)
    quantity_requested = Column(Integer, nullable=False)
    priority = Column(String(50), default="HIGH")
    status = Column(String(50), default="PENDING") # PENDING, APPROVED, DISPATCHED, FULFILLED, REJECTED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
