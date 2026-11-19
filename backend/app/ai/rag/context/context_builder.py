from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.incident import Incident, IncidentCluster
from app.models.shelter import Shelter
from app.models.resource import Resource
from app.models.rescue import RescueTask
from app.models.ai import CVDamageAssessment, RiskAssessment, ResourceDemandPrediction
from app.ai.severity.service import SeverityService
from app.ai.priority.service import PriorityService
from app.ai.duplicate_detection.service import DuplicateDetectionService

class IncidentContextBuilder:
    @classmethod
    def build_structured_context(
        cls,
        db: Session,
        incident_id: str
    ) -> Dict[str, Any]:
        """
        Retrieves and constructs structured, token-efficient live DIRS system context for RAG reasoning.
        Includes live incident state, Phase 3A & Phase 3B AI outputs, inventory, shelters, and tasks.
        """
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return {}

        # Phase 3A AI Intelligence Outputs
        try:
            sev_res = SeverityService.analyze_incident_severity(db, incident)
            severity_data = {
                "level": sev_res.prediction,
                "confidence": sev_res.confidence,
                "factors": [f.model_dump() for f in sev_res.factors[:3]]
            }
        except Exception:
            severity_data = {"level": incident.severity_level or "MEDIUM", "confidence": 85.0}

        try:
            prio_res = PriorityService.calculate_incident_priority(db, incident)
            priority_data = {
                "score": prio_res.priority_score,
                "level": prio_res.classification,
                "breakdown": prio_res.breakdown
            }
        except Exception:
            priority_data = {"score": incident.priority_score or 50.0, "level": incident.priority_level or "MEDIUM"}

        try:
            dup_res = DuplicateDetectionService.detect_duplicates(db, incident)
            dup_data = {
                "count": dup_res.duplicate_count,
                "candidates": [{"code": c.candidate_code, "similarity": round(c.similarity_score * 100, 1)} for c in dup_res.candidates[:2]]
            }
        except Exception:
            dup_data = {"count": 0, "candidates": []}

        # Phase 3B AI Intelligence Outputs
        cv = db.query(CVDamageAssessment).filter(CVDamageAssessment.incident_id == incident_id).order_by(CVDamageAssessment.created_at.desc()).first()
        cv_data = {
            "damage_class": cv.override_class if (cv and cv.is_overridden) else (cv.damage_class if cv else "MODERATE_DAMAGE"),
            "confidence": cv.confidence if cv else 80.0,
            "saliency": cv.explanation_metadata.get("saliency_heatmap_4x4") if (cv and cv.explanation_metadata) else None
        }

        risk = db.query(RiskAssessment).filter(RiskAssessment.incident_id == incident_id).order_by(RiskAssessment.created_at.desc()).first()
        risk_data = {
            "risk_score": risk.risk_score if risk else 65.0,
            "risk_level": risk.override_level if (risk and risk.is_overridden) else (risk.risk_level if risk else "HIGH"),
            "factors": risk.contributing_factors[:3] if (risk and risk.contributing_factors) else []
        }

        rd = db.query(ResourceDemandPrediction).filter(ResourceDemandPrediction.incident_id == incident_id).order_by(ResourceDemandPrediction.created_at.desc()).first()
        resource_demand_data = {
            "predictions": rd.predictions if rd else {},
            "shortages": rd.shortages_detected if rd else []
        }

        # Current System Resource & Shelter State
        open_shelters = db.query(Shelter).filter(Shelter.status == "OPEN").all()
        shelter_summary = [{
            "name": s.name,
            "available_beds": max(0, s.total_capacity - s.current_occupancy),
            "disaster_risk": s.disaster_risk_level
        } for s in open_shelters[:3]]

        ngo_resources = db.query(Resource).all()
        resource_stock = {r.category: sum(res.available_quantity for res in ngo_resources if res.category == r.category) for r in ngo_resources}

        active_tasks = db.query(RescueTask).filter(RescueTask.incident_id == incident_id).all()
        task_summary = [{"id": t.id, "status": t.status} for t in active_tasks]

        return {
            "incident": {
                "id": incident.id,
                "incident_code": incident.incident_code,
                "title": incident.title,
                "disaster_type": incident.disaster_type,
                "status": incident.status,
                "location_address": incident.location_address,
                "latitude": incident.latitude,
                "longitude": incident.longitude,
                "people_affected": incident.people_affected,
                "injuries": incident.injuries,
                "vulnerable_count": incident.vulnerable_count,
                "created_at": incident.created_at.isoformat()
            },
            "severity": severity_data,
            "priority": priority_data,
            "duplicates": dup_data,
            "computer_vision": cv_data,
            "risk_prediction": risk_data,
            "resource_demand": resource_demand_data,
            "shelters": shelter_summary,
            "inventory_stock": resource_stock,
            "rescue_tasks": task_summary
        }
