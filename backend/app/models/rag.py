import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class KnowledgeDocument(Base):
    """
    Stores authoritative emergency management and disaster response documents.
    """
    __tablename__ = "knowledge_documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    source_organization = Column(String(255), nullable=False) # NDMA, FEMA, WHO, Red Cross, Govt
    source_url = Column(String(512), nullable=True)
    document_type = Column(String(100), nullable=False) # MANUAL, PROTOCOL, GUIDELINE, POLICY
    disaster_type = Column(String(50), nullable=False, default="GENERAL") # FLOOD, CYCLONE, FIRE, LANDSLIDE, EARTHQUAKE, GENERAL
    publication_date = Column(String(50), nullable=True)
    version_hash = Column(String(64), nullable=False)
    metadata_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    """
    Normalized and embedded text chunks from authoritative knowledge documents.
    """
    __tablename__ = "knowledge_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(String(255), nullable=True)
    text_content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    embedding_vector = Column(JSON, nullable=True) # Serialized float array for local/pgvector index
    metadata_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("KnowledgeDocument", back_populates="chunks")

class RAGQueryLog(Base):
    """
    Audit log of RAG Copilot queries, retrieved contexts, citations, and generated outputs.
    """
    __tablename__ = "rag_query_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True, index=True)
    query_text = Column(Text, nullable=False)
    query_mode = Column(String(50), default="GENERAL_COPILOT") # SUMMARY, RECOMMENDATIONS, RESOURCE_PLANNING, RISK_EXPLANATION, GENERAL_COPILOT
    response_summary = Column(Text, nullable=False)
    full_response_json = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False, default=85.0)
    is_grounded = Column(Boolean, nullable=False, default=True)
    latency_ms = Column(Float, nullable=False, default=120.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Recommendation(Base):
    """
    Structured AI decision recommendations generated for Government Officers.
    Requires explicit Government approval before execution.
    """
    __tablename__ = "ai_recommendations"

    id = Column(String, primary_key=True, default=generate_uuid)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False) # EVACUATION, SHELTER_ALLOCATION, RESOURCE_DISPATCH, MEDICAL_TRIAGE, ALERTS
    priority = Column(String(50), nullable=False, default="HIGH") # CRITICAL, HIGH, MEDIUM, LOW
    action_title = Column(String(255), nullable=False)
    action_description = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    evidence_citations = Column(JSON, nullable=False) # Retrieved chunks & DIRS system facts
    required_resources = Column(JSON, nullable=True)
    risk_if_delayed = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=90.0)
    requires_government_approval = Column(Boolean, nullable=False, default=True)
    status = Column(String(50), nullable=False, default="PENDING") # PENDING, ACCEPTED, REJECTED, MODIFIED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    decisions = relationship("RecommendationDecision", back_populates="recommendation", cascade="all, delete-orphan")

class RecommendationDecision(Base):
    """
    Immutable audit record of Government Officer approval, rejection, or modification of an AI recommendation.
    """
    __tablename__ = "recommendation_decisions"

    id = Column(String, primary_key=True, default=generate_uuid)
    recommendation_id = Column(String, ForeignKey("ai_recommendations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False) # ACCEPTED, REJECTED, MODIFIED
    original_recommendation_snapshot = Column(JSON, nullable=False)
    modified_values = Column(JSON, nullable=True)
    decision_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    recommendation = relationship("Recommendation", back_populates="decisions")
