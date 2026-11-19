from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.incident import Incident
from app.ai.severity.predictor import SeverityPredictor
from app.ai.common.schemas import SeverityPredictionResponse

class SeverityService:
    _predictor: Optional[SeverityPredictor] = None

    @classmethod
    def get_predictor(cls) -> SeverityPredictor:
        if cls._predictor is None:
            cls._predictor = SeverityPredictor()
        return cls._predictor

    @classmethod
    def analyze_incident_severity(cls, db: Session, incident: Incident) -> SeverityPredictionResponse:
        predictor = cls.get_predictor()
        incident_data = {
            "title": incident.title,
            "description": incident.description,
            "disaster_type": incident.disaster_type,
            "people_affected": incident.people_affected,
            "injuries": incident.injuries,
            "vulnerable_count": incident.vulnerable_count,
            "infrastructure_damage": incident.infrastructure_damage
        }
        
        response = predictor.predict(incident.id, incident_data)
        
        # Persist prediction result on incident entity
        incident.severity_level = response.prediction
        incident.confidence_score = response.confidence
        incident.ai_breakdown = {
            "model_name": response.model_name,
            "model_version": response.model_version,
            "requires_human_review": response.requires_human_review,
            "factors": [f.model_dump() for f in response.factors]
        }
        
        # Transition status to AI_ANALYZED if in REPORTED state
        if incident.status == "REPORTED":
            incident.status = "AI_ANALYZED"
            
        db.commit()
        db.refresh(incident)
        
        return response
