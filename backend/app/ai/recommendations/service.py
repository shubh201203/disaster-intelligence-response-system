from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.rag import Recommendation, RecommendationDecision
from app.models.user import User
from app.services.audit_service import AuditService

class RecommendationService:
    @classmethod
    def get_recommendations_for_incident(cls, db: Session, incident_id: str) -> List[Recommendation]:
        return db.query(Recommendation).filter(Recommendation.incident_id == incident_id).order_by(Recommendation.created_at.desc()).all()

    @classmethod
    def process_government_decision(
        cls,
        db: Session,
        recommendation_id: str,
        action: str, # ACCEPTED, REJECTED, MODIFIED
        notes: Optional[str],
        modified_values: Optional[Dict[str, Any]],
        reviewer: User
    ) -> Recommendation:
        """
        Processes Government Officer decision on an AI recommendation.
        Updates recommendation status and records an immutable RecommendationDecision audit log without destroying original AI recommendation.
        """
        rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
        if not rec:
            raise ValueError("Recommendation not found")

        clean_action = action.upper()
        if clean_action not in ["ACCEPTED", "REJECTED", "MODIFIED"]:
            raise ValueError("Invalid decision action. Allowed: ACCEPTED, REJECTED, MODIFIED")

        original_snapshot = {
            "id": rec.id,
            "category": rec.category,
            "priority": rec.priority,
            "action_title": rec.action_title,
            "action_description": rec.action_description,
            "rationale": rec.rationale,
            "required_resources": rec.required_resources,
            "confidence": rec.confidence,
            "status": rec.status
        }

        rec.status = clean_action
        if clean_action == "MODIFIED" and modified_values:
            if "action_title" in modified_values:
                rec.action_title = modified_values["action_title"]
            if "action_description" in modified_values:
                rec.action_description = modified_values["action_description"]
            if "required_resources" in modified_values:
                rec.required_resources = modified_values["required_resources"]

        decision_record = RecommendationDecision(
            recommendation_id=rec.id,
            user_id=reviewer.id,
            action=clean_action,
            original_recommendation_snapshot=original_snapshot,
            modified_values=modified_values,
            decision_notes=notes
        )
        db.add(decision_record)

        # Record system audit trail
        AuditService.log_action(
            db=db,
            user_id=reviewer.id,
            action=f"RECOMMENDATION_{clean_action}",
            target_entity="Recommendation",
            details={"action": clean_action, "notes": notes, "category": rec.category, "recommendation_id": rec.id}
        )

        db.commit()
        db.refresh(rec)
        return rec
