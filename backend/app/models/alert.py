import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from app.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    alert_type = Column(String(50), default="WARNING") # EVACUATION, WARNING, SHELTER, GENERAL
    target_zone_lat = Column(Float, nullable=True)
    target_zone_lng = Column(Float, nullable=True)
    radius_km = Column(Float, default=10.0)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Donation(Base):
    __tablename__ = "donations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    donor_name = Column(String(255), nullable=False)
    donor_email = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    target_disaster = Column(String(100), default="GENERAL_RELIEF")
    transaction_id = Column(String(100), unique=True, nullable=False)
    status = Column(String(50), default="COMPLETED")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
