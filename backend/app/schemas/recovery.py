from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


# ==============================================================================
# RECOVERY ASSESSMENT SCHEMAS
# ==============================================================================

class RecoveryAssessmentBase(BaseModel):
    sector: str = Field(..., description="HOUSING, HEALTH, EDUCATION, WASH, TRANSPORT, POWER, TELECOM")
    facility_name: str = Field(..., max_length=255)
    damage_level: str = Field(..., description="NONE, MINOR, MODERATE, SEVERE, DESTROYED")
    is_operational: bool = False
    estimated_reconstruction_cost: float = Field(0.0, ge=0.0)
    structural_notes: Optional[str] = None
    evidence_media_urls: List[str] = Field(default_factory=list)
    latitude: float
    longitude: float


class RecoveryAssessmentCreate(RecoveryAssessmentBase):
    incident_id: str = Field(..., description="Target incident UUID")
    cv_assessment_id: Optional[str] = None
    deduplication_cluster_id: Optional[str] = None


class RecoveryAssessmentUpdate(BaseModel):
    sector: Optional[str] = None
    facility_name: Optional[str] = None
    damage_level: Optional[str] = None
    is_operational: Optional[bool] = None
    estimated_reconstruction_cost: Optional[float] = Field(None, ge=0.0)
    structural_notes: Optional[str] = None
    evidence_media_urls: Optional[List[str]] = None


class RecoveryAssessmentVerify(BaseModel):
    action: str = Field(..., description="VERIFY or REJECT")
    verified_cost: Optional[float] = Field(None, ge=0.0)
    notes: Optional[str] = None


class RecoveryAssessmentSupersede(BaseModel):
    new_damage_level: str = Field(..., description="NONE, MINOR, MODERATE, SEVERE, DESTROYED")
    new_estimated_cost: float = Field(..., ge=0.0)
    is_operational: bool = False
    structural_notes: Optional[str] = None
    justification_reason: Optional[str] = Field(None, min_length=5)
    supersede_reason: Optional[str] = Field(None, min_length=5)

    @model_validator(mode="after")
    def reconcile_reason(self):
        if not self.justification_reason and not self.supersede_reason:
            raise ValueError("Either justification_reason or supersede_reason is required")
        if not self.justification_reason:
            self.justification_reason = self.supersede_reason
        if not self.supersede_reason:
            self.supersede_reason = self.justification_reason
        return self


class RecoveryAssessmentResponse(RecoveryAssessmentBase):
    id: str
    assessment_code: str
    incident_id: str
    inspector_id: str
    cv_assessment_id: Optional[str] = None
    assessment_version: int
    superseded_by_id: Optional[str] = None
    is_current_version: bool
    deduplication_cluster_id: Optional[str] = None
    reconciliation_status: str
    provenance_tier: str
    data_confidence: float
    freshness_status: str
    verification_status: str
    verified_by_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



# ==============================================================================
# RECOVERY NEED SCHEMAS
# ==============================================================================

class RecoveryNeedBase(BaseModel):
    ward_code: str
    district: str
    sector: str
    affected_households: int = Field(0, ge=0)
    displaced_persons: int = Field(0, ge=0)
    vulnerable_persons: int = Field(0, ge=0)
    potable_water_demand_liters_day: float = Field(0.0, ge=0.0)
    temporary_shelter_units_needed: int = Field(0, ge=0)
    livelihood_support_households: int = Field(0, ge=0)
    unmet_need_score: float = Field(50.0, ge=0.0, le=100.0)
    census_baseline_population: int = Field(..., ge=1)


class RecoveryNeedCreate(RecoveryNeedBase):
    assessment_id: Optional[str] = None
    raw_beneficiary_id: Optional[str] = Field(None, description="Sensitive ID will be salted and hashed")
    household_head_name: Optional[str] = Field(None, description="Will be masked for privacy")


class RecoveryNeedResponse(RecoveryNeedBase):
    """Internal / Government detailed schema with hashed identity"""
    id: str
    assessment_id: Optional[str] = None
    beneficiary_id_hash: Optional[str] = None
    household_head_name_masked: Optional[str] = None
    is_reconciled: bool
    reconciliation_notes: Optional[str] = None
    data_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)



class RecoveryNeedPublicResponse(RecoveryNeedBase):
    """Public / Non-Govt schema strictly stripping all individual identifiers"""
    id: str
    is_reconciled: bool
    data_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)



# ==============================================================================
# RECOVERY PROJECT SCHEMAS
# ==============================================================================

class RecoveryProjectBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    sector: str
    priority_tier: str = Field("TIER_3", description="TIER_1, TIER_2, TIER_3, TIER_4")
    priority_score: float = Field(0.0, ge=0.0, le=100.0)
    estimated_cost: float = Field(0.0, ge=0.0)
    funding_source: Optional[str] = None
    time_indexed_cost_profile: List[float] = Field(default_factory=list)
    estimated_duration_days: int = Field(..., ge=1)
    lead_agency: str = Field(..., max_length=100)
    contractor_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RecoveryProjectCreate(RecoveryProjectBase):
    need_id: Optional[str] = None
    assigned_manager_id: Optional[str] = None
    earliest_start_date: Optional[datetime] = None
    planned_completion_date: Optional[datetime] = None


class RecoveryProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority_tier: Optional[str] = None
    estimated_cost: Optional[float] = Field(None, ge=0.0)
    time_indexed_cost_profile: Optional[List[float]] = None
    estimated_duration_days: Optional[int] = Field(None, ge=1)
    lead_agency: Optional[str] = None
    contractor_name: Optional[str] = None
    assigned_manager_id: Optional[str] = None


class RecoveryProjectApprove(BaseModel):
    approved_budget: float = Field(..., ge=0.0)
    funding_source: str = Field(..., max_length=100)
    sanction_order_number: str = Field(..., max_length=100)
    notes: Optional[str] = None


class RecoveryProjectStatusUpdate(BaseModel):
    status: str = Field(..., description="PROPOSED, APPROVED, IN_TENDER, IN_PROGRESS, INSPECTION, COMPLETED, SUSPENDED")
    actual_expenditure_increment: Optional[float] = Field(0.0, ge=0.0)
    notes: Optional[str] = None


class RecoveryProjectResponse(RecoveryProjectBase):
    id: str
    project_code: str
    need_id: Optional[str] = None
    status: str
    actual_expenditure: float
    actual_duration_days: Optional[int] = None
    earliest_start_date: Optional[datetime] = None
    planned_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    assigned_manager_id: Optional[str] = None
    approval_status: str
    approved_by_id: Optional[str] = None
    sanction_order_number: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



# ==============================================================================
# PROJECT DEPENDENCY SCHEMAS
# ==============================================================================

class ProjectDependencyCreate(BaseModel):
    predecessor_project_id: str
    successor_project_id: str
    dependency_type: str = Field("FINISH_TO_START", description="FINISH_TO_START, START_TO_START, FINISH_TO_FINISH")
    lag_days: int = Field(0, ge=0)
    rationale: Optional[str] = None


class ProjectDependencyResponse(BaseModel):
    id: str
    predecessor_project_id: str
    successor_project_id: str
    dependency_type: str
    lag_days: int
    is_critical_path: bool
    rationale: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class PrecedenceCPMInfo(BaseModel):
    duration_periods: int
    early_start: int
    early_finish: int
    late_start: int
    late_finish: int
    total_float: int
    free_float: int
    is_critical: bool


class PrecedenceGraphNode(BaseModel):
    id: str
    project_code: str
    title: str
    sector: str
    priority_tier: str
    status: str
    estimated_cost: float
    estimated_duration_days: int
    cpm: Optional[PrecedenceCPMInfo] = None


class PrecedenceGraphEdge(BaseModel):
    id: str
    predecessor_project_id: str
    successor_project_id: str
    dependency_type: str
    lag_days: int
    lag_periods: int
    is_critical_path: bool
    rationale: Optional[str] = None


class PrecedenceGraphResponse(BaseModel):
    is_acyclic: bool
    topological_order: List[str] = Field(default_factory=list)
    critical_path_project_ids: List[str] = Field(default_factory=list)
    project_makespan_periods: int = 0
    total_projects: int = 0
    total_dependencies: int = 0
    nodes: List[PrecedenceGraphNode] = Field(default_factory=list)
    edges: List[PrecedenceGraphEdge] = Field(default_factory=list)
    cycle_path: Optional[List[str]] = None


class PrecedenceEdgeValidateRequest(BaseModel):
    predecessor_project_id: str
    successor_project_id: str
    lag_days: int = Field(0, ge=0)
    dependency_type: str = Field("FINISH_TO_START", description="FINISH_TO_START, START_TO_START, FINISH_TO_FINISH")


class PrecedenceEdgeValidateResponse(BaseModel):
    is_valid: bool
    reason: Optional[str] = None
    message: str
    cycle_path: Optional[List[str]] = None


# ==============================================================================
# RECOVERY RESOURCE SCHEMAS
# ==============================================================================

class RecoveryResourceCreate(BaseModel):
    project_id: str
    material_category: str = Field(..., description="CEMENT, STRUCTURAL_STEEL, PIPING, ASPHALT, TIMBER, HEAVY_MACHINERY, WORKFORCE")
    item_description: str = Field(..., max_length=255)
    quantity_required: float = Field(..., gt=0.0)
    unit_of_measure: str = Field(..., max_length=30)
    unit_cost_estimate: float = Field(..., ge=0.0)
    supplier_info: Optional[str] = None


class RecoveryResourceUpdate(BaseModel):
    quantity_delivered: Optional[float] = Field(None, ge=0.0)
    actual_unit_cost: Optional[float] = Field(None, ge=0.0)
    delivery_status: Optional[str] = None


class RecoveryResourceResponse(BaseModel):
    id: str
    project_id: str
    material_category: str
    item_description: str
    quantity_required: float
    quantity_delivered: float
    unit_of_measure: str
    unit_cost_estimate: float
    actual_unit_cost: float
    supplier_info: Optional[str] = None
    delivery_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



# ==============================================================================
# COMMUNITY RECOVERY METRIC SCHEMAS
# ==============================================================================

class CommunityRecoveryMetricCreate(BaseModel):
    ward_code: str
    district: str
    metric_date: datetime
    active_shelter_count: int = Field(0, ge=0)
    remaining_displaced_persons: int = Field(0, ge=0)
    power_grid_restoration_pct: float = Field(0.0, ge=0.0, le=100.0)
    potable_water_access_pct: float = Field(0.0, ge=0.0, le=100.0)
    healthcare_facility_operational_pct: float = Field(0.0, ge=0.0, le=100.0)
    schools_open_pct: float = Field(0.0, ge=0.0, le=100.0)
    livelihoods_resumed_pct: float = Field(0.0, ge=0.0, le=100.0)
    overall_recovery_score: float = Field(0.0, ge=0.0, le=100.0)
    data_confidence: float = Field(100.0, ge=0.0, le=100.0)
    freshness_status: str = Field("FRESH", description="FRESH, MODERATE, STALE_AMBER, EXPIRED_RED")


class CommunityRecoveryMetricResponse(CommunityRecoveryMetricCreate):
    id: str
    last_verified_at: datetime
    verified_by_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



# ==============================================================================
# RECOVERY OVERRIDE LOG SCHEMAS
# ==============================================================================

class RecoveryOverrideLogResponse(BaseModel):
    id: str
    project_id: Optional[str] = None
    user_id: str
    action: str
    original_value: Dict[str, Any]
    new_value: Dict[str, Any]
    justification_reason: str
    ip_address: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)



# ==============================================================================
# PHASE 6C: DAMAGE ASSESSMENT INTELLIGENCE & CV SCREENING SCHEMAS
# ==============================================================================

class DamageScreeningRequest(BaseModel):
    image_path: Optional[str] = Field(None, description="Path to image evidence file")
    image_base64: Optional[str] = Field(None, description="Optional Base64 encoded image string")
    incident_id: Optional[str] = None


class DamageScreeningResponse(BaseModel):
    cv_assessment_id: str
    predicted_damage_class: str
    mapped_recovery_damage_level: str
    confidence_score: float
    class_probabilities: Dict[str, float]
    model_name: str
    model_version: str
    requires_human_review: bool
    is_uncertain: bool
    image_sha256: str
    screening_disclaimer: str
    feature_summary: Dict[str, float]

    model_config = ConfigDict(from_attributes=True)



class DamageAssessmentFieldCreate(BaseModel):
    incident_id: str = Field(..., description="Target incident UUID")
    sector: str = Field(..., description="HOUSING, HEALTH, EDUCATION, WASH, TRANSPORT, POWER, TELECOM")
    facility_name: str = Field(..., max_length=255)
    damage_level: str = Field(..., description="NONE, MINOR, MODERATE, SEVERE, DESTROYED")
    is_operational: bool = False
    estimated_reconstruction_cost: float = Field(0.0, ge=0.0)
    structural_notes: Optional[str] = None
    evidence_media_urls: List[str] = Field(default_factory=list)
    cv_assessment_id: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    assessor_confidence: Optional[float] = Field(100.0, ge=0.0, le=100.0)


class DamageAssessmentVerifyRequest(BaseModel):
    action: str = Field(..., description="VERIFY, REJECT, DISPUTE")
    verified_damage_level: Optional[str] = Field(None, description="NONE, MINOR, MODERATE, SEVERE, DESTROYED")
    engineering_notes: str = Field(..., min_length=5, description="Mandatory engineering rationale")


class DamageAssessmentHistoryResponse(BaseModel):
    facility_name: str
    cluster_id: str
    current_version: int
    total_versions: int
    version_lineage: List[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)



# ==============================================================================
# PHASE 6C: STRUCTURED RECOVERY NEEDS & DEMOGRAPHICS SCHEMAS
# ==============================================================================

class StructuredRecoveryNeedCreate(BaseModel):
    ward_code: str
    district: str
    sector: str = Field(..., description="HOUSING, WASH, HEALTH, EDUCATION, LIVELIHOODS, ESSENTIAL_SERVICES, POWER, TRANSPORT")
    assessment_id: Optional[str] = None
    affected_households: int = Field(..., ge=0)
    displaced_persons: int = Field(0, ge=0)
    # Mutually Exclusive Demographics (Demographic Conservation Rule)
    affected_population_gen: int = Field(0, ge=0, description="General population")
    affected_population_acc: int = Field(0, ge=0, description="Accessibility needs population")
    affected_population_med: int = Field(0, ge=0, description="Medical needs population")
    affected_population_med_acc: int = Field(0, ge=0, description="Combined medical + accessibility population")
    # PII fields (will be hashed / masked)
    raw_beneficiary_id: Optional[str] = None
    raw_household_head_name: Optional[str] = None
    # Sectoral Demands
    potable_water_demand_liters_day: float = Field(0.0, ge=0.0)
    temporary_shelter_units_needed: int = Field(0, ge=0)
    livelihood_support_households: int = Field(0, ge=0)
    unmet_need_score: float = Field(50.0, ge=0.0, le=100.0)
    census_baseline_population: int = Field(..., ge=1, description="Official census baseline cap for ward")
    urgency_tier: str = Field("MEDIUM_TIER3", description="CRITICAL_TIER1, HIGH_TIER2, MEDIUM_TIER3, LOW_TIER4")
    time_horizon_days: int = Field(30, ge=1)
    is_verified_demand: bool = False
    source_confidence: float = Field(100.0, ge=0.0, le=100.0)
    notes: Optional[str] = None


class StructuredRecoveryNeedResponse(BaseModel):
    id: str
    assessment_id: Optional[str] = None
    ward_code: str
    district: str
    sector: str
    affected_households: int
    displaced_persons: int
    vulnerable_persons: int
    affected_population_gen: int
    affected_population_acc: int
    affected_population_med: int
    affected_population_med_acc: int
    total_affected_population: int
    beneficiary_id_hash: Optional[str] = None
    household_head_name_masked: Optional[str] = None
    potable_water_demand_liters_day: float
    temporary_shelter_units_needed: int
    livelihood_support_households: int
    unmet_need_score: float
    census_baseline_population: int
    exceeds_census_cap: bool
    urgency_tier: str
    time_horizon_days: int
    is_verified_demand: bool
    source_confidence: float
    is_reconciled: bool
    data_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)



# ==============================================================================
# PHASE 6C: POPULATION RECONCILIATION SCHEMAS
# ==============================================================================

class DuplicateCandidateGroup(BaseModel):
    beneficiary_hash: str
    matched_need_ids: List[str]
    household_head_name_masked: str
    record_count: int
    match_reason: str


class UnresolvedConflictItem(BaseModel):
    cluster_id: str
    conflicting_need_ids: List[str]
    reason: str
    requires_human_review: bool


class PopulationReconciliationRequest(BaseModel):
    ward_code: Optional[str] = None
    district: Optional[str] = None
    need_ids: Optional[List[str]] = None


class PopulationReconciliationResponse(BaseModel):
    ward_code: str
    district: str
    source_record_count: int
    unique_beneficiary_count: int
    reconciled_affected_households: int
    reconciled_displaced_persons: int
    reconciled_demographics: Dict[str, int]
    census_baseline_population: int
    census_utilization_pct: float
    duplicate_candidates: List[DuplicateCandidateGroup]
    unresolved_conflicts: List[UnresolvedConflictItem]
    reconciliation_status: str
    confidence_score: float
    provenance_summary: str

    model_config = ConfigDict(from_attributes=True)



# ==============================================================================
# PHASE 6C: SPATIAL RECOVERY & ANALYTICS SCHEMAS
# ==============================================================================

class RecoverySpatialSummaryResponse(BaseModel):
    ward_code: str
    total_assessments: int
    verified_assessments: int
    damage_level_distribution: Dict[str, int]
    total_estimated_reconstruction_cost: float
    total_affected_households: int
    total_displaced_persons: int
    total_potable_water_demand_liters: float
    total_shelter_units_needed: int
    spatial_boundary_geojson: Dict[str, Any]
    is_synthetic_boundary: bool

    model_config = ConfigDict(from_attributes=True)



class RecoveryAnalyticsSummaryResponse(BaseModel):
    total_facilities_assessed: int = Field(..., description="Total verified facilities assessed by certified engineers")
    verified_facilities_count: int = Field(0, description="Explicit count of verified engineering assessments")
    preliminary_screening_count: int = Field(0, description="Separate count of unverified preliminary AI screenings")
    rejected_assessments_count: int = Field(0, description="Count of rejected assessments excluded from official totals")
    operational_facilities_percentage: float
    damage_distribution: Dict[str, int] = Field(default_factory=dict, description="Damage distribution strictly across VERIFIED assessments")
    preliminary_damage_distribution: Dict[str, int] = Field(default_factory=dict, description="Damage distribution across preliminary unverified screenings")
    sectoral_distribution: Dict[str, int] = Field(default_factory=dict, description="Sectoral distribution strictly across VERIFIED assessments")
    average_power_restoration_pct: float
    average_water_access_pct: float
    average_community_recovery_score: float
    aggregated_affected_households: int
    aggregated_displaced_persons: int
    last_updated: Any

    model_config = ConfigDict(from_attributes=True)




# ==============================================================================
# PHASE 6F / WP2: COMMUNITY RECOVERY MONITORING, RESCORING & SIMULATION SCHEMAS
# ==============================================================================

class WardRecoveryIndicatorDTO(BaseModel):
    ward_code: str
    district: str
    metric_date: datetime
    active_shelter_count: int
    remaining_displaced_persons: int
    power_grid_restoration_pct: float
    potable_water_access_pct: float
    healthcare_facility_operational_pct: float
    schools_open_pct: float
    livelihoods_resumed_pct: float
    overall_recovery_score: float
    initial_confidence: float
    current_confidence: float
    freshness_status: str
    days_since_verification: float
    last_verified_at: datetime
    verified_by_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CommunityMetricSummaryResponse(BaseModel):
    total_wards_monitored: int
    reporting_date_range: Dict[str, Optional[datetime]]
    average_recovery_score: float
    average_confidence: float
    sector_restoration_averages: Dict[str, float]
    total_active_shelters: int
    total_remaining_displaced: int
    freshness_distribution: Dict[str, int]
    wards: List[WardRecoveryIndicatorDTO]

    model_config = ConfigDict(from_attributes=True)


class VulnerabilityRescoreRequest(BaseModel):
    ward_code: str
    district: str
    total_affected_population: int = Field(..., ge=0)
    n_accessible_needs: int = Field(0, ge=0)
    n_chronic_medical: int = Field(0, ge=0)
    n_intersectional: int = Field(0, ge=0)
    n_general: Optional[int] = Field(None, ge=0)
    census_baseline_population: Optional[int] = Field(None, ge=0)
    power_grid_restoration_pct: float = Field(0.0, ge=0.0, le=100.0)
    potable_water_access_pct: float = Field(0.0, ge=0.0, le=100.0)
    healthcare_facility_operational_pct: float = Field(0.0, ge=0.0, le=100.0)
    schools_open_pct: float = Field(0.0, ge=0.0, le=100.0)
    livelihoods_resumed_pct: float = Field(0.0, ge=0.0, le=100.0)
    remaining_displaced_persons: int = Field(0, ge=0)
    last_verified_at: Optional[datetime] = None


class VulnerabilityRescoreResponse(BaseModel):
    ward_code: str
    district: str
    base_demographic_vulnerability: float
    rescored_vulnerability: float
    vulnerability_delta: float
    raw_headcount_index_psi: float
    baseline_status: str
    effective_denominator: float
    infrastructure_deficit_score: float
    displacement_pressure_score: float
    data_confidence: float
    freshness_status: str
    days_elapsed: float
    uncertainty_flag: bool
    audit_trail: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class SimulationPerturbationParams(BaseModel):
    budget_multiplier: float = Field(1.0, ge=0.2, le=3.0, description="Capital budget scaling factor (e.g. 1.2 = +20%)")
    material_supply_factor: float = Field(1.0, ge=0.1, le=2.0, description="Material availability factor (e.g. 0.7 = 30% supply bottleneck)")
    disaster_recurrence_shock: bool = Field(False, description="Simulate secondary disaster event during planning horizon")
    shock_period: int = Field(3, ge=1, description="Period at which recurrence shock occurs")
    shock_damage_factor: float = Field(0.25, ge=0.0, le=0.75, description="Fractional setback to active in-flight projects")
    sector_priorities: Dict[str, float] = Field(default_factory=dict, description="Sector priority multipliers (e.g. {'WASH': 1.5, 'HEALTH': 1.3})")


class RecoveryWhatIfSimulationRequest(BaseModel):
    scenario_name: str = Field(..., min_length=3, max_length=150)
    planning_horizon_periods: int = Field(12, ge=4, le=36)
    period_length_days: float = Field(30.0, ge=7.0, le=90.0)
    initial_budget: float = Field(..., ge=0.0)
    periodic_budget_inflow: float = Field(0.0, ge=0.0)
    target_ward_codes: Optional[List[str]] = None
    perturbation: SimulationPerturbationParams = Field(default_factory=SimulationPerturbationParams)
    candidate_project_ids: Optional[List[str]] = Field(None, description="Optional subset of projects to simulate; if omitted, all active projects used")


class SimulationPeriodSnapshot(BaseModel):
    period: int
    calendar_day: float
    capital_spent_period: float
    cumulative_capital_spent: float
    remaining_cash_balance: float
    projects_in_progress: int
    projects_completed_cumulative: int
    displaced_persons_remaining: int
    projected_recovery_score: float
    unmet_needs_score: float
    shock_occurred: bool


class BottleneckResourceItem(BaseModel):
    material_category: str
    demand_quantity: float
    available_supply: float
    deficit_quantity: float
    impact_level: str


class RecoveryWhatIfSimulationResponse(BaseModel):
    scenario_name: str
    planning_horizon_periods: int
    period_length_days: float
    is_non_mutating: bool = True
    baseline_completion_period: Optional[int]
    simulated_completion_period: Optional[int]
    baseline_final_recovery_score: float
    simulated_final_recovery_score: float
    recovery_score_delta: float
    periods_to_target_80pct: Optional[int]
    total_budget_allocated: float
    total_budget_utilized: float
    unmet_budget_deficit: float
    bottleneck_resources: List[BottleneckResourceItem]
    trajectory: List[SimulationPeriodSnapshot]
    simulation_provenance: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
