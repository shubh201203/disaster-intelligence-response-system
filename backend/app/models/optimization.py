import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(50), default="PROPOSED", index=True) # PROPOSED, APPROVED, REJECTED, MODIFIED
    run_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    requesting_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Metadata & Snapshots
    objective_config_json = Column(JSON, default=dict)
    input_snapshot_json = Column(JSON, default=dict)
    solver_metadata_json = Column(JSON, default=dict)
    
    # Performance & Feasibility Metrics
    runtime_ms = Column(Float, nullable=True)
    optimality_gap = Column(Float, nullable=True)
    feasibility_status = Column(String(50), default="FEASIBLE") # FEASIBLE, RELAXED, INFEASIBLE
    graph_version = Column(String(64), nullable=True) # Phase 5C graph version hash
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    requesting_user = relationship("User", foreign_keys=[requesting_user_id])
    recommendations = relationship("OptimizationRecommendation", back_populates="run", cascade="all, delete-orphan")
    override_logs = relationship("OptimizationOverrideLog", back_populates="run", cascade="all, delete-orphan")

class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("optimization_runs.id"), nullable=False, index=True)
    recommendation_type = Column(String(50), nullable=False, index=True) # RESOURCE_DISPATCH, VEHICLE_ROUTE, SHELTER_EVACUATION, VOLUNTEER_ASSIGNMENT
    
    # Entity Foreign Keys
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=True)
    depot_id = Column(String(36), ForeignKey("resources.id"), nullable=True)
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=True)
    shelter_id = Column(String(36), ForeignKey("shelters.id"), nullable=True)
    volunteer_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Payload & Route Data
    commodity_category = Column(String(50), nullable=True)
    allocated_quantity = Column(Float, default=0.0)
    proposed_route_json = Column(JSON, default=dict)
    objective_contribution = Column(Float, default=0.0)
    explanation = Column(Text, nullable=True)
    
    # Phase 5F Data Foundation Extensions
    demographic_group = Column(String(50), nullable=True, index=True) # GEN, ACC, MED, MED_ACC (SHELTER_EVACUATION)
    skill_category = Column(String(50), nullable=True, index=True) # MEDICAL, RESCUE, LOGISTICS, GENERAL (VOLUNTEER_ASSIGNMENT)
    shift_id = Column(String(50), nullable=True) # e.g. SHIFT_1
    transit_time_minutes = Column(Float, nullable=True) # Network travel time in minutes
    transit_distance_km = Column(Float, nullable=True) # Network travel distance in km
    
    # Item Level State
    status = Column(String(50), default="PROPOSED", index=True) # PROPOSED, APPROVED, REJECTED, MODIFIED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    run = relationship("OptimizationRun", back_populates="recommendations")
    incident = relationship("Incident", foreign_keys=[incident_id])
    depot = relationship("Resource", foreign_keys=[depot_id])
    vehicle = relationship("Vehicle", foreign_keys=[vehicle_id])
    shelter = relationship("Shelter", foreign_keys=[shelter_id])
    volunteer = relationship("User", foreign_keys=[volunteer_id])

class OptimizationOverrideLog(Base):
    __tablename__ = "optimization_override_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("optimization_runs.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False) # Must be user with GOVT role
    action = Column(String(50), nullable=False) # APPROVE, MODIFY, REJECT
    
    original_value_json = Column(JSON, default=dict)
    overridden_value_json = Column(JSON, default=dict)
    justification_reason = Column(Text, nullable=False)
    audit_log_id = Column(String(36), ForeignKey("audit_logs.id"), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    run = relationship("OptimizationRun", back_populates="override_logs")
    user = relationship("User", foreign_keys=[user_id])
    audit_log = relationship("AuditLog", foreign_keys=[audit_log_id])
