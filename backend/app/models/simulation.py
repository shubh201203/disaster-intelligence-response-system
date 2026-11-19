"""
DIRS Phase 5G: Simulation Models
Database models for disaster what-if scenarios and simulation audit records.
Classification: SYNTHETIC CALIBRATED SIMULATION / DECISION SUPPORT
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class SimulationScenario(Base):
    """Represents a defined disaster what-if scenario."""
    __tablename__ = "simulation_scenarios"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    hazard_type = Column(String(50), default="FLOOD", nullable=False)
    severity_multiplier = Column(Float, default=1.0, nullable=False)
    affected_area_multiplier = Column(Float, default=1.0, nullable=False)
    
    # Serialized scenario parameters
    scenario_parameters_json = Column(JSON, default=dict)
    seed = Column(Integer, default=42, nullable=False)
    
    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    created_by = relationship("User", foreign_keys=[created_by_user_id])
    simulation_runs = relationship("SimulationRun", back_populates="scenario", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if "scenario_parameters" in kwargs:
            kwargs["scenario_parameters_json"] = kwargs.pop("scenario_parameters")
        super().__init__(**kwargs)

    @property
    def scenario_parameters(self):
        return self.scenario_parameters_json

    @scenario_parameters.setter
    def scenario_parameters(self, val):
        self.scenario_parameters_json = val


class SimulationRun(Base):
    """Represents an executed simulation run with reproducibility audit trail."""
    __tablename__ = "simulation_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scenario_id = Column(String(36), ForeignKey("simulation_scenarios.id"), nullable=True, index=True)
    scenario_name = Column(String(100), nullable=True)
    status = Column(String(50), default="PROPOSED", nullable=False, index=True) # Always PROPOSED / SIMULATION
    disclaimer = Column(String(255), default="SIMULATED IMPACT: This is a decision-support simulation. Live operational state is unmodified.")
    
    # Audit & Reproducibility Hashes
    base_state_hash = Column(String(64), nullable=False)
    result_hash = Column(String(64), nullable=False)
    graph_version = Column(String(64), nullable=False)
    seed = Column(Integer, default=42, nullable=False)
    
    # Simulation Outputs
    delta_metrics_json = Column(JSON, default=dict)
    intelligence_observations_json = Column(JSON, default=list)
    critical_alerts_json = Column(JSON, default=list)
    audit_trail_json = Column(JSON, default=dict)
    
    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    scenario = relationship("SimulationScenario", back_populates="simulation_runs")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __init__(self, **kwargs):
        if "delta_summary" in kwargs:
            kwargs["delta_metrics_json"] = kwargs.pop("delta_summary")
        if "timing_breakdown" in kwargs:
            timing = kwargs.pop("timing_breakdown")
            if "audit_trail_json" not in kwargs:
                kwargs["audit_trail_json"] = {}
            kwargs["audit_trail_json"]["timing_ms"] = timing
        super().__init__(**kwargs)

    @property
    def delta_summary(self):
        return self.delta_metrics_json

    @delta_summary.setter
    def delta_summary(self, val):
        self.delta_metrics_json = val

    @property
    def timing_breakdown(self):
        return self.audit_trail_json.get("timing_ms", {}) if self.audit_trail_json else {}

    @timing_breakdown.setter
    def timing_breakdown(self, val):
        if not self.audit_trail_json:
            self.audit_trail_json = {}
        self.audit_trail_json["timing_ms"] = val
