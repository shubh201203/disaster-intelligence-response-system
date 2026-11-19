import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class RecoveryAssessment(Base):
    """
    Formal engineering and field damage/loss evaluations with monotonic
    versioning and duplicate candidate tracking.
    """
    __tablename__ = "recovery_assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_code = Column(String(50), unique=True, index=True, nullable=False)
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=False, index=True)
    inspector_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    sector = Column(String(50), nullable=False, index=True)  # HOUSING, HEALTH, EDUCATION, WASH, TRANSPORT, POWER, TELECOM
    facility_name = Column(String(255), nullable=False)
    damage_level = Column(String(30), nullable=False)  # NONE, MINOR, MODERATE, SEVERE, DESTROYED
    is_operational = Column(Boolean, default=False, nullable=False)
    estimated_reconstruction_cost = Column(Float, default=0.0, nullable=False)
    structural_notes = Column(Text, nullable=True)
    evidence_media_urls = Column(JSON, default=list)
    cv_assessment_id = Column(String(36), ForeignKey("cv_damage_assessments.id", ondelete="SET NULL"), nullable=True)

    # Location & Geometry (SRID 4326)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geom = Column(Geometry(geometry_type='POINT', srid=4326, spatial_index=False, use_typmod=True), nullable=True)

    # Versioning & Deduplication
    assessment_version = Column(Integer, default=1, nullable=False)
    superseded_by_id = Column(String(36), ForeignKey("recovery_assessments.id", ondelete="SET NULL"), nullable=True)
    is_current_version = Column(Boolean, default=True, nullable=False, index=True)
    deduplication_cluster_id = Column(String(36), nullable=True, index=True)
    reconciliation_status = Column(String(30), default="UNRECONCILED", nullable=False)  # UNRECONCILED, RECONCILED_MERGED, SUPERSEDED

    # Provenance & Freshness
    provenance_tier = Column(String(50), default="TIER_2_GOVT_OFFICIAL", nullable=False)
    data_confidence = Column(Float, default=100.0, nullable=False)
    freshness_status = Column(String(20), default="FRESH", nullable=False)  # FRESH, MODERATE, STALE_AMBER, EXPIRED_RED

    # Human Verification Gate
    verification_status = Column(String(30), default="PENDING_VERIFICATION", nullable=False)  # PENDING_VERIFICATION, VERIFIED, REJECTED
    verified_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    incident = relationship("Incident", foreign_keys=[incident_id])
    inspector = relationship("User", foreign_keys=[inspector_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])
    needs = relationship("RecoveryNeed", back_populates="assessment", cascade="all, delete-orphan")


class RecoveryNeed(Base):
    """
    Quantifies multi-sectoral human and community recovery requirements with
    double-count reconciliation against census baseline caps and salted PII hashing.
    """
    __tablename__ = "recovery_needs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("recovery_assessments.id", ondelete="CASCADE"), nullable=True, index=True)
    ward_code = Column(String(50), nullable=False, index=True)
    district = Column(String(100), nullable=False)
    sector = Column(String(50), nullable=False, index=True)

    # Demographics
    affected_households = Column(Integer, default=0, nullable=False)
    displaced_persons = Column(Integer, default=0, nullable=False)
    vulnerable_persons = Column(Integer, default=0, nullable=False)

    # Salted Pseudonymized Beneficiary Identification
    beneficiary_id_hash = Column(String(64), nullable=True, index=True)
    household_head_name_masked = Column(String(100), nullable=True)

    # Sectoral Demands
    potable_water_demand_liters_day = Column(Float, default=0.0)
    temporary_shelter_units_needed = Column(Integer, default=0)
    livelihood_support_households = Column(Integer, default=0)
    unmet_need_score = Column(Float, default=50.0)

    # Census Reconciliation Gate
    census_baseline_population = Column(Integer, nullable=False)
    is_reconciled = Column(Boolean, default=False)
    reconciliation_notes = Column(String(255), nullable=True)

    data_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    assessment = relationship("RecoveryAssessment", back_populates="needs")
    projects = relationship("RecoveryProject", back_populates="need")


class RecoveryProject(Base):
    """
    Capital reconstruction, rehabilitation, or infrastructure restoration project.
    """
    __tablename__ = "recovery_projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_code = Column(String(50), unique=True, index=True, nullable=False)
    need_id = Column(String(36), ForeignKey("recovery_needs.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sector = Column(String(50), nullable=False, index=True)
    priority_tier = Column(String(20), default="TIER_3", nullable=False)  # TIER_1, TIER_2, TIER_3, TIER_4
    priority_score = Column(Float, default=0.0, index=True)
    status = Column(String(50), default="PROPOSED", nullable=False, index=True)  # PROPOSED, APPROVED, IN_TENDER, IN_PROGRESS, INSPECTION, COMPLETED, SUSPENDED

    # Capital Cost Tracking
    estimated_cost = Column(Float, default=0.0, nullable=False)
    actual_expenditure = Column(Float, default=0.0, nullable=False)
    funding_source = Column(String(100), nullable=True)  # STATE_SDRF, NATIONAL_NDRF, MULTILATERAL_WB, NGO_AID

    # Time-Indexed Expenditure & Schedule
    time_indexed_cost_profile = Column(JSON, default=list)
    estimated_duration_days = Column(Integer, nullable=False)
    actual_duration_days = Column(Integer, nullable=True)
    earliest_start_date = Column(DateTime, nullable=True)
    planned_completion_date = Column(DateTime, nullable=True)
    actual_completion_date = Column(DateTime, nullable=True)

    lead_agency = Column(String(100), nullable=False)
    contractor_name = Column(String(150), nullable=True)
    assigned_manager_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Location & Geometry (SRID 4326)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geom = Column(Geometry(geometry_type='GEOMETRY', srid=4326, spatial_index=False, use_typmod=True), nullable=True)

    # Human Approval Gate
    approval_status = Column(String(30), default="PENDING_APPROVAL", nullable=False)
    approved_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sanction_order_number = Column(String(100), nullable=True)
    approval_timestamp = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    need = relationship("RecoveryNeed", back_populates="projects")
    assigned_manager = relationship("User", foreign_keys=[assigned_manager_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    resources = relationship("RecoveryResource", back_populates="project", cascade="all, delete-orphan")
    predecessors = relationship(
        "ProjectDependency",
        foreign_keys="ProjectDependency.successor_project_id",
        back_populates="successor",
        cascade="all, delete-orphan"
    )
    successors = relationship(
        "ProjectDependency",
        foreign_keys="ProjectDependency.predecessor_project_id",
        back_populates="predecessor",
        cascade="all, delete-orphan"
    )
    override_logs = relationship("RecoveryOverrideLog", back_populates="project", cascade="all, delete-orphan")


class ProjectDependency(Base):
    """
    Encodes directed precedence relations between recovery projects for critical path and scheduling.
    """
    __tablename__ = "project_dependencies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    predecessor_project_id = Column(String(36), ForeignKey("recovery_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    successor_project_id = Column(String(36), ForeignKey("recovery_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    dependency_type = Column(String(30), default="FINISH_TO_START", nullable=False)
    lag_days = Column(Integer, default=0, nullable=False)
    is_critical_path = Column(Boolean, default=False, nullable=False)
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('predecessor_project_id', 'successor_project_id', name='uq_project_dependency'),
    )

    # Relationships
    predecessor = relationship("RecoveryProject", foreign_keys=[predecessor_project_id], back_populates="successors")
    successor = relationship("RecoveryProject", foreign_keys=[successor_project_id], back_populates="predecessors")


class RecoveryResource(Base):
    """
    Specialized durable reconstruction materials and heavy machinery allocated to projects.
    """
    __tablename__ = "recovery_resources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("recovery_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    material_category = Column(String(50), nullable=False, index=True)  # CEMENT, STRUCTURAL_STEEL, PIPING, ASPHALT, TIMBER, HEAVY_MACHINERY, WORKFORCE
    item_description = Column(String(255), nullable=False)
    quantity_required = Column(Float, nullable=False)
    quantity_delivered = Column(Float, default=0.0, nullable=False)
    unit_of_measure = Column(String(30), nullable=False)  # METRIC_TONS, CUBIC_METERS, METERS, MACHINE_DAYS, LABOR_HOURS
    unit_cost_estimate = Column(Float, nullable=False)
    actual_unit_cost = Column(Float, default=0.0, nullable=False)
    supplier_info = Column(String(255), nullable=True)
    delivery_status = Column(String(30), default="ORDERED", nullable=False)  # PENDING, ORDERED, IN_TRANSIT, DELIVERED, EXHAUSTED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    project = relationship("RecoveryProject", back_populates="resources")


class CommunityRecoveryMetric(Base):
    """
    Longitudinal ward-level recovery indicators tracked over time with confidence decay.
    """
    __tablename__ = "community_recovery_metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ward_code = Column(String(50), nullable=False, index=True)
    district = Column(String(100), nullable=False)
    metric_date = Column(DateTime, nullable=False, index=True)

    # Community Indicators
    active_shelter_count = Column(Integer, default=0)
    remaining_displaced_persons = Column(Integer, default=0)
    power_grid_restoration_pct = Column(Float, default=0.0)
    potable_water_access_pct = Column(Float, default=0.0)
    healthcare_facility_operational_pct = Column(Float, default=0.0)
    schools_open_pct = Column(Float, default=0.0)
    livelihoods_resumed_pct = Column(Float, default=0.0)
    overall_recovery_score = Column(Float, default=0.0)

    # Confidence and Freshness
    data_confidence = Column(Float, default=100.0)
    freshness_status = Column(String(20), default="FRESH")  # FRESH, MODERATE, STALE_AMBER, EXPIRED_RED
    last_verified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    verified_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint('ward_code', 'metric_date', name='uq_ward_metric_date'),
    )

    # Relationships
    verified_by = relationship("User", foreign_keys=[verified_by_id])


class RecoveryOverrideLog(Base):
    """
    Audit log of human-in-the-loop recovery decisions, budget overrides, and project approvals.
    """
    __tablename__ = "recovery_override_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("recovery_projects.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # PROJECT_APPROVE, BUDGET_OVERRIDE, WEIGHT_ADJUSTMENT, DEPENDENCY_BYPASS, ASSESSMENT_SUPERSEDE
    original_value = Column(JSON, default=dict)
    new_value = Column(JSON, default=dict)
    justification_reason = Column(Text, nullable=False)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    project = relationship("RecoveryProject", back_populates="override_logs")
    user = relationship("User", foreign_keys=[user_id])
