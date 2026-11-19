from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.incident import Incident
from app.core.deps import get_current_user, require_role
from app.core.websocket_manager import ws_manager
from app.ai.rag.service import RAGService
from app.ai.rag.schemas import (
    RAGQueryRequest,
    GroundedRAGResponse,
    KnowledgeSearchRequest
)

router = APIRouter(prefix="/ai", tags=["AI Copilot & RAG Grounding"])

@router.post("/rag/query", response_model=GroundedRAGResponse)
async def query_ai_disaster_copilot(
    req: RAGQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes Grounded RAG Copilot query combining verified DIRS incident facts, Phase 3A/3B AI predictions,
    and authoritative disaster management knowledge.
    """
    if req.incident_id:
        inc = db.query(Incident).filter(Incident.id == req.incident_id).first()
        if not inc:
            raise HTTPException(status_code=404, detail="Incident not found")

    response = RAGService.query_copilot(
        db=db,
        query=req.query,
        incident_id=req.incident_id,
        mode=req.mode or "GENERAL_COPILOT",
        user=current_user
    )

    if req.incident_id:
        await ws_manager.broadcast_event(
            event_type="AI_RAG_RESPONSE_READY",
            entity_type="Incident",
            entity_id=req.incident_id,
            data={
                "incident_id": req.incident_id,
                "summary": response.summary[:120],
                "confidence": response.confidence
            }
        )

    return response

@router.post("/rag/incidents/{incident_id}/summary", response_model=GroundedRAGResponse)
async def get_grounded_incident_summary(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generates a structured, grounded situation report summary for a specific disaster incident.
    """
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    return RAGService.query_copilot(
        db=db,
        query=f"Provide a comprehensive situation report summary and facts for incident {inc.incident_code}",
        incident_id=incident_id,
        mode="SUMMARY",
        user=current_user
    )

@router.post("/knowledge/search")
async def search_knowledge_base(
    req: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Searches authoritative disaster management guidelines & emergency operating procedures.
    """
    RAGService.seed_authoritative_knowledge_base(db)
    from app.ai.rag.retrieval.hybrid_search import HybridSearchRetriever
    chunks = HybridSearchRetriever.retrieve(db, req.query, req.disaster_type, req.top_k)
    return {"query": req.query, "count": len(chunks), "results": chunks}
