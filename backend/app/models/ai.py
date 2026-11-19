import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, JSON, Boolean
from app.database import Base

class AIPrediction(Base):
    __tablename__ = "ai_predictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(String(50), nullable=False)  # Incident, Evidence, Zone
    entity_id = Column(String(36), nullable=False, index=True)
    prediction_type = Column(String(50), nullable=False)  # SEVERITY, PRIORITY, DUPLICATE, COMPUTER_VISION, RISK_PREDICTION, RESOURCE_DEMAND
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    prediction = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    requires_human_review = Column(Boolean, default=False)
    explanation = Column(JSON, default=dict)
    input_snapshot = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class CVDamageAssessment(Base):
    __tablename__ = "cv_damage_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), nullable=False, index=True)
    evidence_id = Column(String(36), nullable=True, index=True)
    damage_class = Column(String(50), nullable=False)  # NO_DAMAGE, LOW_DAMAGE, MODERATE_DAMAGE, SEVERE_DAMAGE, DESTROYED
    confidence = Column(Float, nullable=False)
    class_probabilities = Column(JSON, default=dict)
    model_version = Column(String(50), nullable=False, default="1.0.0")
    requires_human_review = Column(Boolean, default=False)
    is_overridden = Column(Boolean, default=False)
    override_class = Column(String(50), nullable=True)
    override_notes = Column(String(255), nullable=True)
    reviewer_id = Column(String(36), nullable=True)
    explanation_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), nullable=True, index=True)
    geographic_scope = Column(String(100), nullable=False, default="District Central")
    disaster_type = Column(String(50), nullable=False, default="FLOOD")
    risk_score = Column(Float, nullable=False)  # 0.0 - 100.0
    risk_level = Column(String(50), nullable=False)  # LOW, MODERATE, HIGH, EXTREME
    confidence = Column(Float, nullable=False)
    requires_human_review = Column(Boolean, default=False)
    is_overridden = Column(Boolean, default=False)
    override_level = Column(String(50), nullable=True)
    override_notes = Column(String(255), nullable=True)
    reviewer_id = Column(String(36), nullable=True)
    input_snapshot = Column(JSON, default=dict)
    contributing_factors = Column(JSON, default=list)
    model_version = Column(String(50), nullable=False, default="1.0.0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class ResourceDemandPrediction(Base):
    __tablename__ = "resource_demand_predictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), nullable=False, index=True)
    predictions = Column(JSON, default=dict)  # resource_type -> {quantity, unit, confidence, bounds}
    overall_confidence = Column(Float, nullable=False)
    requires_human_review = Column(Boolean, default=False)
    is_overridden = Column(Boolean, default=False)
    override_demands = Column(JSON, nullable=True)
    override_notes = Column(String(255), nullable=True)
    reviewer_id = Column(String(36), nullable=True)
    contributing_features = Column(JSON, default=list)
    shortages_detected = Column(JSON, default=list)
    model_version = Column(String(50), nullable=False, default="1.0.0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

