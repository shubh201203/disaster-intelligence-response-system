from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.incident import Incident
from app.models.rag import Recommendation
from app.core.deps import get_current_user, require_role
from app.core.websocket_manager import ws_manager
from app.ai.recommendations.engine import RecommendationEngine
from app.ai.recommendations.service import RecommendationService
from app.ai.rag.schemas import RecommendationResponse, RecommendationDecisionRequest

router = APIRouter(prefix="/ai", tags=["AI Recommendation Engine"])

@router.get("/incidents/{incident_id}/recommendations", response_model=List[RecommendationResponse])
async def get_incident_recommendations(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists AI decision recommendations for an incident, generating new recommendations if none exist.
    """
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    recs = RecommendationService.get_recommendations_for_incident(db, incident_id)
    if not recs:
        recs = RecommendationEngine.generate_incident_recommendations(db, inc)

    res = []
    for r in recs:
        res.append(RecommendationResponse(
            id=r.id,
            incident_id=r.incident_id,
            category=r.category,
            priority=r.priority,
            action_title=r.action_title,
            action_description=r.action_description,
            rationale=r.rationale,
            evidence_citations=r.evidence_citations,
            required_resources=r.required_resources,
            risk_if_delayed=r.risk_if_delayed,
            confidence=r.confidence,
            requires_government_approval=r.requires_government_approval,
            status=r.status,
            created_at=r.created_at.isoformat()
        ))
    return res

@router.post("/recommendations/{recommendation_id}/approve", response_model=RecommendationResponse)
async def approve_recommendation(
    recommendation_id: str,
    req: Optional[RecommendationDecisionRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Allows authorized Government Officer to approve an AI recommendation with audit tracking.
    """
    notes = req.notes if req else "Government Officer approved recommendation"
    updated = RecommendationService.process_government_decision(
        db=db,
        recommendation_id=recommendation_id,
        action="ACCEPTED",
        notes=notes,
        modified_values=None,
        reviewer=current_user
    )

    await ws_manager.broadcast_event(
        event_type="AI_RECOMMENDATION_APPROVED",
        entity_type="Recommendation",
        entity_id=updated.id,
        data={
            "recommendation_id": updated.id,
            "action_title": updated.action_title,
            "approved_by": current_user.full_name
        }
    )

    return RecommendationResponse(
        id=updated.id,
        incident_id=updated.incident_id,
        category=updated.category,
        priority=updated.priority,
        action_title=updated.action_title,
        action_description=updated.action_description,
        rationale=updated.rationale,
        evidence_citations=updated.evidence_citations,
        required_resources=updated.required_resources,
        risk_if_delayed=updated.risk_if_delayed,
        confidence=updated.confidence,
        requires_government_approval=updated.requires_government_approval,
        status=updated.status,
        created_at=updated.created_at.isoformat()
    )

@router.post("/recommendations/{recommendation_id}/reject", response_model=RecommendationResponse)
async def reject_recommendation(
    recommendation_id: str,
    req: Optional[RecommendationDecisionRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Allows authorized Government Officer to reject an AI recommendation.
    """
    notes = req.notes if req else "Government Officer rejected recommendation"
    updated = RecommendationService.process_government_decision(
        db=db,
        recommendation_id=recommendation_id,
        action="REJECTED",
        notes=notes,
        modified_values=None,
        reviewer=current_user
    )

    await ws_manager.broadcast_event(
        event_type="AI_RECOMMENDATION_REJECTED",
        entity_type="Recommendation",
        entity_id=updated.id,
        data={
            "recommendation_id": updated.id,
            "action_title": updated.action_title,
            "rejected_by": current_user.full_name
        }
    )

    return RecommendationResponse(
        id=updated.id,
        incident_id=updated.incident_id,
        category=updated.category,
        priority=updated.priority,
        action_title=updated.action_title,
        action_description=updated.action_description,
        rationale=updated.rationale,
        evidence_citations=updated.evidence_citations,
        required_resources=updated.required_resources,
        risk_if_delayed=updated.risk_if_delayed,
        confidence=updated.confidence,
        requires_government_approval=updated.requires_government_approval,
        status=updated.status,
        created_at=updated.created_at.isoformat()
    )

@router.post("/recommendations/{recommendation_id}/modify", response_model=RecommendationResponse)
async def modify_recommendation(
    recommendation_id: str,
    req: RecommendationDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Allows authorized Government Officer to modify parameters and approve an AI recommendation.
    """
    notes = req.notes or "Government Officer modified recommendation parameters"
    updated = RecommendationService.process_government_decision(
        db=db,
        recommendation_id=recommendation_id,
        action="MODIFIED",
        notes=notes,
        modified_values=req.modified_values,
        reviewer=current_user
    )

    await ws_manager.broadcast_event(
        event_type="AI_RECOMMENDATION_APPROVED",
        entity_type="Recommendation",
        entity_id=updated.id,
        data={
            "recommendation_id": updated.id,
            "action_title": updated.action_title,
            "modified_by": current_user.full_name
        }
    )

    return RecommendationResponse(
        id=updated.id,
        incident_id=updated.incident_id,
        category=updated.category,
        priority=updated.priority,
        action_title=updated.action_title,
        action_description=updated.action_description,
        rationale=updated.rationale,
        evidence_citations=updated.evidence_citations,
        required_resources=updated.required_resources,
        risk_if_delayed=updated.risk_if_delayed,
        confidence=updated.confidence,
        requires_government_approval=updated.requires_government_approval,
        status=updated.status,
        created_at=updated.created_at.isoformat()
    )
