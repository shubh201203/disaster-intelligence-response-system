from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session
from app.models.incident import Incident
from app.ai.duplicate_detection.clustering import find_duplicate_candidates
from app.ai.common.schemas import DuplicateDetectionResponse

class DuplicateDetectionService:
    @classmethod
    def detect_duplicates(cls, db: Session, incident: Incident) -> DuplicateDetectionResponse:
        """
        Queries active incidents within spatial radius and time window to detect duplicate reports.
        """
        recent_incidents = db.query(Incident).filter(
            Incident.id != incident.id,
            Incident.status != "CLOSED"
        ).order_by(Incident.created_at.desc()).limit(100).all()
        
        candidates = find_duplicate_candidates(incident, recent_incidents)
        
        return DuplicateDetectionResponse(
            incident_id=incident.id,
            duplicate_count=len(candidates),
            candidates=candidates,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
