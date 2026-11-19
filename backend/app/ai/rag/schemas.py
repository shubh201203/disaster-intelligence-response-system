from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CitationItem(BaseModel):
    citation_id: int
    doc_id: str
    title: str
    organization: str
    section: Optional[str] = "General Guidance"
    url: Optional[str] = None
    similarity_score: float = 0.90
    excerpt: str

class FactItem(BaseModel):
    statement: str
    source_type: str # DIRS_SYSTEM_DATA or RETRIEVED_KNOWLEDGE
    evidence_ref: str

class InferenceItem(BaseModel):
    conclusion: str
    basis: str

class RecommendationItem(BaseModel):
    recommendation_id: Optional[str] = None
    priority: str # CRITICAL, HIGH, MEDIUM, LOW
    action: str
    rationale: str
    evidence: str
    required_resources: Optional[Dict[str, Any]] = None
    risk_if_delayed: Optional[str] = None
    confidence: float = 90.0
    requires_government_approval: bool = True

class GroundedRAGResponse(BaseModel):
    query: str
    mode: str = "GENERAL_COPILOT" # SUMMARY, RECOMMENDATIONS, RESOURCE_PLANNING, RISK_EXPLANATION, GENERAL_COPILOT
    summary: str
    facts: List[FactItem] = []
    inferences: List[InferenceItem] = []
    recommendations: List[RecommendationItem] = []
    risks: List[str] = []
    resource_implications: List[str] = []
    confidence: float = 88.5
    citations: List[CitationItem] = []
    requires_human_review: bool = False
    is_grounded: bool = True
    provider: str = "DIRS_GROUNDED_FALLBACK"

class RAGQueryRequest(BaseModel):
    query: str
    incident_id: Optional[str] = None
    mode: Optional[str] = "GENERAL_COPILOT"

class RecommendationDecisionRequest(BaseModel):
    notes: Optional[str] = None
    modified_values: Optional[Dict[str, Any]] = None

class RecommendationResponse(BaseModel):
    id: str
    incident_id: str
    category: str
    priority: str
    action_title: str
    action_description: str
    rationale: str
    evidence_citations: Dict[str, Any]
    required_resources: Optional[Dict[str, Any]] = None
    risk_if_delayed: Optional[str] = None
    confidence: float
    requires_government_approval: bool
    status: str
    created_at: str

class KnowledgeSearchRequest(BaseModel):
    query: str
    disaster_type: Optional[str] = None
    top_k: int = 5
