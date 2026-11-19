from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.incident import Incident
from app.models.ai import AIPrediction
from app.core.deps import get_current_user, require_role
from app.core.websocket_manager import ws_manager
from app.ai.severity.service import SeverityService
from app.ai.priority.service import PriorityService
from app.ai.duplicate_detection.service import DuplicateDetectionService
from app.ai.common.model_registry import ModelRegistry
from app.ai.common.schemas import (
    SeverityPredictionResponse,
    PriorityScoreResponse,
    DuplicateDetectionResponse,
    ModelRegistryItem
)

router = APIRouter(prefix="/ai", tags=["AI Intelligence"])

@router.get("/models", response_model=List[ModelRegistryItem])
def list_registered_models():
    """
    Returns metadata for all registered DIRS AI intelligence models.
    """
    return ModelRegistry.list_models()

@router.post("/incidents/{incident_id}/severity", response_model=SeverityPredictionResponse)
async def predict_incident_severity(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Predicts disaster incident severity using trained classifier and returns explainability breakdown.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    try:
        res = SeverityService.analyze_incident_severity(db, incident)

        # Log AI Prediction to AIPrediction table
        pred_record = AIPrediction(
            entity_type="Incident",
            entity_id=incident.id,
            prediction_type="SEVERITY",
            model_name=res.model_name,
            model_version=res.model_version,
            prediction=res.prediction,
            confidence=res.confidence,
            requires_human_review=res.requires_human_review,
            explanation={"factors": [f.model_dump() for f in res.factors]},
            input_snapshot={"title": incident.title, "people_affected": incident.people_affected}
        )
        db.add(pred_record)
        db.commit()

        # WebSocket Event
        await ws_manager.broadcast_event(
            event_type="AI_SEVERITY_UPDATED",
            entity_type="Incident",
            entity_id=incident.id,
            data={
                "incident_code": incident.incident_code,
                "severity_level": res.prediction,
                "confidence": res.confidence,
                "requires_human_review": res.requires_human_review
            }
        )

        return res
    except Exception as e:
        # Fallback grace handling
        raise HTTPException(
            status_code=500,
            detail=f"AI Severity Prediction fallback triggered: {str(e)}"
        )

@router.post("/incidents/{incident_id}/priority", response_model=PriorityScoreResponse)
async def calculate_incident_priority(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Calculates 0-100 priority score using centralized PRIORITY_WEIGHTS configuration.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    try:
        res = PriorityService.calculate_incident_priority(db, incident)

        pred_record = AIPrediction(
            entity_type="Incident",
            entity_id=incident.id,
            prediction_type="PRIORITY",
            model_name="priority-scoring-engine",
            model_version=res.model_version,
            prediction=str(res.priority_score),
            confidence=100.0,
            requires_human_review=False,
            explanation={"breakdown": res.breakdown, "factors": [f.model_dump() for f in res.factors]},
            input_snapshot={"title": incident.title}
        )
        db.add(pred_record)
        db.commit()

        await ws_manager.broadcast_event(
            event_type="AI_PRIORITY_UPDATED",
            entity_type="Incident",
            entity_id=incident.id,
            data={
                "incident_code": incident.incident_code,
                "priority_score": res.priority_score,
                "classification": res.classification
            }
        )

        return res
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI Priority Engine fallback triggered: {str(e)}"
        )

@router.post("/incidents/{incident_id}/duplicates", response_model=DuplicateDetectionResponse)
async def detect_incident_duplicates(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Detects candidate duplicate reports using spatial distance, time delta, and text similarity.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    try:
        res = DuplicateDetectionService.detect_duplicates(db, incident)

        if res.duplicate_count > 0:
            await ws_manager.broadcast_event(
                event_type="DUPLICATE_DETECTED",
                entity_type="Incident",
                entity_id=incident.id,
                data={
                    "incident_code": incident.incident_code,
                    "duplicate_count": res.duplicate_count,
                    "top_candidate": res.candidates[0].candidate_code if res.candidates else None
                }
            )

        return res
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI Duplicate Detection fallback triggered: {str(e)}"
        )

@router.post("/incidents/{incident_id}/analyze")
async def run_full_ai_analysis(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Runs complete AI Pipeline (Severity + Priority + Duplicate Detection) for an incident.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    sev = SeverityService.analyze_incident_severity(db, incident)
    prio = PriorityService.calculate_incident_priority(db, incident)
    dups = DuplicateDetectionService.detect_duplicates(db, incident)

    return {
        "incident_id": incident.id,
        "severity": sev,
        "priority": prio,
        "duplicates": dups
    }


# ============================================================================
# PHASE 3B API ENDPOINTS: Computer Vision, Risk Prediction, Resource Demand
# ============================================================================

from app.models.incident import IncidentMedia
from app.models.ai import CVDamageAssessment, RiskAssessment, ResourceDemandPrediction
from app.ai.computer_vision.service import ComputerVisionService
from app.ai.risk_prediction.service import RiskPredictionService
from app.ai.resource_demand.service import ResourceDemandService
from app.ai.common.schemas import (
    CVDamageResponse,
    CVOverrideRequest,
    RiskPredictionResponse,
    RiskOverrideRequest,
    ResourceDemandResponse,
    ResourceDemandOverrideRequest
)

@router.post("/incidents/{incident_id}/vision", response_model=CVDamageResponse)
async def analyze_incident_computer_vision(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Runs Computer Vision damage assessment on incident media images.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    media = db.query(IncidentMedia).filter(IncidentMedia.incident_id == incident_id).first()

    assessment = ComputerVisionService.analyze_incident_image(db, incident, media)

    await ws_manager.broadcast_event(
        event_type="AI_CV_ANALYSIS_COMPLETED",
        entity_type="Incident",
        entity_id=incident.id,
        data={
            "incident_code": incident.incident_code,
            "damage_class": assessment.damage_class,
            "confidence": assessment.confidence,
            "requires_human_review": assessment.requires_human_review
        }
    )

    return CVDamageResponse(
        id=assessment.id,
        incident_id=assessment.incident_id,
        evidence_id=assessment.evidence_id,
        damage_class=assessment.damage_class,
        confidence=assessment.confidence,
        class_probabilities=assessment.class_probabilities,
        model_version=assessment.model_version,
        requires_human_review=assessment.requires_human_review,
        is_overridden=assessment.is_overridden,
        override_class=assessment.override_class,
        override_notes=assessment.override_notes,
        explanation_metadata=assessment.explanation_metadata,
        created_at=assessment.created_at.isoformat()
    )


@router.post("/incidents/{incident_id}/vision/override", response_model=CVDamageResponse)
async def override_cv_damage_assessment(
    incident_id: str,
    override_in: CVOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Allows Government Officers to review and override AI Computer Vision damage predictions.
    """
    assessment = db.query(CVDamageAssessment).filter(CVDamageAssessment.incident_id == incident_id).order_by(CVDamageAssessment.created_at.desc()).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="No CV damage assessment found for incident")

    updated = ComputerVisionService.override_damage_assessment(
        db, assessment.id, override_in.override_class, override_in.notes, current_user
    )

    return CVDamageResponse(
        id=updated.id,
        incident_id=updated.incident_id,
        evidence_id=updated.evidence_id,
        damage_class=updated.damage_class,
        confidence=updated.confidence,
        class_probabilities=updated.class_probabilities,
        model_version=updated.model_version,
        requires_human_review=updated.requires_human_review,
        is_overridden=updated.is_overridden,
        override_class=updated.override_class,
        override_notes=updated.override_notes,
        explanation_metadata=updated.explanation_metadata,
        created_at=updated.created_at.isoformat()
    )


@router.post("/incidents/{incident_id}/risk", response_model=RiskPredictionResponse)
async def predict_incident_disaster_risk(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Predicts geographic and meteorological disaster risk score (0-100) and risk level.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    assessment = RiskPredictionService.calculate_risk(db, incident=incident)

    await ws_manager.broadcast_event(
        event_type="AI_RISK_UPDATED",
        entity_type="Incident",
        entity_id=incident.id,
        data={
            "incident_code": incident.incident_code,
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "confidence": assessment.confidence
        }
    )

    return RiskPredictionResponse(
        id=assessment.id,
        incident_id=assessment.incident_id,
        geographic_scope=assessment.geographic_scope,
        disaster_type=assessment.disaster_type,
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        confidence=assessment.confidence,
        requires_human_review=assessment.requires_human_review,
        is_overridden=assessment.is_overridden,
        override_level=assessment.override_level,
        override_notes=assessment.override_notes,
        contributing_factors=assessment.contributing_factors,
        model_version=assessment.model_version,
        created_at=assessment.created_at.isoformat()
    )


@router.post("/incidents/{incident_id}/risk/override", response_model=RiskPredictionResponse)
async def override_disaster_risk(
    incident_id: str,
    override_in: RiskOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Allows Government Officers to review and override AI risk prediction levels.
    """
    assessment = db.query(RiskAssessment).filter(RiskAssessment.incident_id == incident_id).order_by(RiskAssessment.created_at.desc()).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="No risk assessment found for incident")

    updated = RiskPredictionService.override_risk_assessment(
        db, assessment.id, override_in.override_level, override_in.notes, current_user
    )

    return RiskPredictionResponse(
        id=updated.id,
        incident_id=updated.incident_id,
        geographic_scope=updated.geographic_scope,
        disaster_type=updated.disaster_type,
        risk_score=updated.risk_score,
        risk_level=updated.risk_level,
        confidence=updated.confidence,
        requires_human_review=updated.requires_human_review,
        is_overridden=updated.is_overridden,
        override_level=updated.override_level,
        override_notes=updated.override_notes,
        contributing_factors=updated.contributing_factors,
        model_version=updated.model_version,
        created_at=updated.created_at.isoformat()
    )


@router.post("/incidents/{incident_id}/resource-demand", response_model=ResourceDemandResponse)
async def predict_incident_resource_demand(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Predicts required resource quantities (water, food, medical, beds, personnel) and flags stock shortages.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    prediction = ResourceDemandService.predict_incident_demand(db, incident)

    await ws_manager.broadcast_event(
        event_type="AI_RESOURCE_DEMAND_UPDATED",
        entity_type="Incident",
        entity_id=incident.id,
        data={
            "incident_code": incident.incident_code,
            "shortage_count": len(prediction.shortages_detected),
            "overall_confidence": prediction.overall_confidence
        }
    )

    return ResourceDemandResponse(
        id=prediction.id,
        incident_id=prediction.incident_id,
        predictions=prediction.predictions,
        overall_confidence=prediction.overall_confidence,
        requires_human_review=prediction.requires_human_review,
        is_overridden=prediction.is_overridden,
        override_demands=prediction.override_demands,
        override_notes=prediction.override_notes,
        contributing_features=prediction.contributing_features,
        shortages_detected=prediction.shortages_detected,
        model_version=prediction.model_version,
        created_at=prediction.created_at.isoformat()
    )


@router.post("/incidents/{incident_id}/resource-demand/override", response_model=ResourceDemandResponse)
async def override_resource_demand_prediction(
    incident_id: str,
    override_in: ResourceDemandOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Allows Government Officers to review and override predicted resource demand quantities.
    """
    prediction = db.query(ResourceDemandPrediction).filter(ResourceDemandPrediction.incident_id == incident_id).order_by(ResourceDemandPrediction.created_at.desc()).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="No resource demand prediction found for incident")

    updated = ResourceDemandService.override_demand_prediction(
        db, prediction.id, override_in.override_demands, override_in.notes, current_user
    )

    return ResourceDemandResponse(
        id=updated.id,
        incident_id=updated.incident_id,
        predictions=updated.predictions,
        overall_confidence=updated.overall_confidence,
        requires_human_review=updated.requires_human_review,
        is_overridden=updated.is_overridden,
        override_demands=updated.override_demands,
        override_notes=updated.override_notes,
        contributing_features=updated.contributing_features,
        shortages_detected=updated.shortages_detected,
        model_version=updated.model_version,
        created_at=updated.created_at.isoformat()
    )
