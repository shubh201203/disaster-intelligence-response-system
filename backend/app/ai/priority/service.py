from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.incident import Incident
from app.ai.priority.scoring import compute_priority_score_and_breakdown
from app.ai.common.schemas import PriorityScoreResponse

class PriorityService:
    @classmethod
    def calculate_incident_priority(cls, db: Session, incident: Incident) -> PriorityScoreResponse:
        data = {
            "severity_level": incident.severity_level,
            "disaster_type": incident.disaster_type,
            "people_affected": incident.people_affected,
            "injuries": incident.injuries,
            "vulnerable_count": incident.vulnerable_count,
            "infrastructure_damage": incident.infrastructure_damage,
            "corroboration_count": 1
        }
        
        score, classification, breakdown, factors = compute_priority_score_and_breakdown(data)
        
        # Persist priority updates to Incident entity
        incident.priority_score = score
        incident.priority_level = classification
        if incident.ai_breakdown is None:
            incident.ai_breakdown = {}
            
        incident.ai_breakdown.update({
            "priority_scoring_version": "1.0.0",
            "priority_breakdown": breakdown
        })
        
        db.commit()
        db.refresh(incident)
        
        return PriorityScoreResponse(
            incident_id=incident.id,
            priority_score=score,
            classification=classification,
            model_version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            breakdown=breakdown,
            factors=factors
        )
