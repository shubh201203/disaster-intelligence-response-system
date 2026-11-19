from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class FactorContribution(BaseModel):
    feature: str = Field(..., description="Feature or factor name")
    impact: float = Field(..., description="Point impact or contribution weight")
    direction: str = Field("increases", description="Impact direction: increases or decreases severity/priority")
    description: Optional[str] = Field(None, description="Human readable explanation")

class SeverityPredictionResponse(BaseModel):
    incident_id: str
    prediction: str = Field(..., description="Severity level: LOW, MEDIUM, HIGH, CRITICAL")
    confidence: float = Field(..., description="Confidence percentage 0-100%")
    requires_human_review: bool = Field(False, description="Flagged if confidence is below threshold")
    model_name: str
    model_version: str
    timestamp: str
    factors: List[FactorContribution] = Field(default_factory=list)

class PriorityScoreResponse(BaseModel):
    incident_id: str
    priority_score: float = Field(..., description="Priority score 0-100")
    classification: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    model_version: str
    timestamp: str
    breakdown: Dict[str, float] = Field(default_factory=dict)
    factors: List[FactorContribution] = Field(default_factory=list)

class DuplicateEvidence(BaseModel):
    distance_m: float = Field(..., description="Spatial distance in meters")
    time_difference_min: float = Field(..., description="Time difference in minutes")
    type_match: bool = Field(..., description="Whether disaster types match exactly")
    text_similarity: float = Field(..., description="Text cosine/keyword similarity score (0-1)")

class DuplicateCandidate(BaseModel):
    candidate_incident_id: str
    candidate_code: str
    candidate_title: str
    similarity_score: float = Field(..., description="Overall multi-criteria similarity score (0-1)")
    recommendation: str = Field(..., description="POSSIBLE_DUPLICATE or UNRELATED")
    evidence: DuplicateEvidence

class DuplicateDetectionResponse(BaseModel):
    incident_id: str
    duplicate_count: int
    candidates: List[DuplicateCandidate] = Field(default_factory=list)
    timestamp: str

class ModelRegistryItem(BaseModel):
    name: str
    version: str
    purpose: str
    framework: str
    dataset: str
    training_date: str
    status: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    limitations: str

# Phase 3B Computer Vision Schemas
class CVDamageResponse(BaseModel):
    id: str
    incident_id: str
    evidence_id: Optional[str] = None
    damage_class: str = Field(..., description="NO_DAMAGE, LOW_DAMAGE, MODERATE_DAMAGE, SEVERE_DAMAGE, DESTROYED")
    confidence: float = Field(..., description="Confidence percentage 0-100%")
    class_probabilities: Dict[str, float] = Field(default_factory=dict)
    model_version: str
    requires_human_review: bool
    is_overridden: bool = False
    override_class: Optional[str] = None
    override_notes: Optional[str] = None
    explanation_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str

class CVOverrideRequest(BaseModel):
    override_class: str = Field(..., description="NO_DAMAGE, LOW_DAMAGE, MODERATE_DAMAGE, SEVERE_DAMAGE, DESTROYED")
    notes: str = Field(..., description="Review notes explaining manual override rationale")

# Phase 3B Risk Prediction Schemas
class RiskPredictionResponse(BaseModel):
    id: str
    incident_id: Optional[str] = None
    geographic_scope: str
    disaster_type: str
    risk_score: float = Field(..., description="Risk score 0.0 - 100.0")
    risk_level: str = Field(..., description="LOW, MODERATE, HIGH, EXTREME")
    confidence: float
    requires_human_review: bool
    is_overridden: bool = False
    override_level: Optional[str] = None
    override_notes: Optional[str] = None
    contributing_factors: List[FactorContribution] = Field(default_factory=list)
    model_version: str
    created_at: str

class RiskOverrideRequest(BaseModel):
    override_level: str = Field(..., description="LOW, MODERATE, HIGH, EXTREME")
    notes: str = Field(..., description="Review notes explaining risk level override")

# Phase 3B Resource Demand Schemas
class ResourceDemandItem(BaseModel):
    quantity: float
    unit: str
    confidence: float
    lower_bound: float
    upper_bound: float

class ShortageItem(BaseModel):
    resource_type: str
    demanded: float
    available: float
    shortage_quantity: float
    severity: str

class ResourceDemandResponse(BaseModel):
    id: str
    incident_id: str
    predictions: Dict[str, ResourceDemandItem] = Field(default_factory=dict)
    overall_confidence: float
    requires_human_review: bool
    is_overridden: bool = False
    override_demands: Optional[Dict[str, float]] = None
    override_notes: Optional[str] = None
    contributing_features: List[str] = Field(default_factory=list)
    shortages_detected: List[ShortageItem] = Field(default_factory=list)
    model_version: str
    created_at: str

class ResourceDemandOverrideRequest(BaseModel):
    override_demands: Dict[str, float] = Field(..., description="Manual resource quantity overrides")
    notes: str = Field(..., description="Review notes explaining demand override")
