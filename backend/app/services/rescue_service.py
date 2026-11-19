from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.rescue import RescueTask
from app.models.incident import Incident
from app.models.user import User, VolunteerProfile
from app.services.gis_service import haversine_distance_km
from app.services.audit_service import AuditService

ALLOWED_TASK_TRANSITIONS = {
    "ASSIGNED": ["ACCEPTED", "REJECTED"],
    "ACCEPTED": ["EN_ROUTE"],
    "EN_ROUTE": ["ARRIVED"],
    "ARRIVED": ["RESCUE_STARTED"],
    "RESCUE_STARTED": ["COMPLETED"],
    "COMPLETED": [],
    "REJECTED": []
}

class RescueService:
    @staticmethod
    def assign_rescue_task(db: Session, incident_id: str, assigned_type: str, assigned_id: str, admin: User) -> RescueTask:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            raise ValueError("Incident not found")

        task = RescueTask(
            incident_id=incident.id,
            assigned_type=assigned_type.upper(),
            assigned_id=assigned_id,
            status="ASSIGNED"
        )
        db.add(task)
        
        # Advance incident status to ASSIGNED
        if incident.status in ["VERIFIED", "PRIORITIZED"]:
            incident.status = "ASSIGNED"

        db.commit()
        db.refresh(task)

        AuditService.log_action(
            db, admin.id, "TASK_ASSIGNED", "RescueTask",
            {"task_id": task.id, "incident_id": incident.id, "assigned_to": assigned_id}
        )

        return task

    @staticmethod
    def transition_task_status(db: Session, task: RescueTask, target_status: str, actor: User) -> RescueTask:
        current = task.status
        target = target_status.upper()

        # Authorization: Only assigned volunteer or GOVT can update task
        if actor.role == "VOLUNTEER" and task.assigned_id != actor.id:
            raise PermissionError("Volunteers can only update their own assigned rescue tasks")

        if target not in ALLOWED_TASK_TRANSITIONS.get(current, []):
            raise ValueError(f"Invalid rescue task transition from '{current}' to '{target}'. Allowed: {ALLOWED_TASK_TRANSITIONS.get(current, [])}")

        task.status = target
        if target == "COMPLETED":
            task.completed_at = datetime.now(timezone.utc)
            # Update associated incident status to RESOLVED
            incident = db.query(Incident).filter(Incident.id == task.incident_id).first()
            if incident:
                incident.status = "RESOLVED"
                incident.resolved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(task)

        AuditService.log_action(
            db, actor.id, "TASK_STATUS_CHANGED", "RescueTask",
            {"task_id": task.id, "from_status": current, "to_status": target}
        )

        return task

    @staticmethod
    def rank_candidate_volunteers(db: Session, incident: Incident) -> List[Tuple[User, float, float]]:
        volunteers = db.query(User).filter(User.role == "VOLUNTEER", User.is_active == True).all()
        ranked = []

        for vol in volunteers:
            prof = vol.volunteer_profile
            if not prof or not prof.is_available or prof.verification_status != "VERIFIED":
                continue

            dist_km = 5.0
            if prof.current_lat and prof.current_lng:
                dist_km = haversine_distance_km(incident.latitude, incident.longitude, prof.current_lat, prof.current_lng)

            # Candidate suitability score out of 100
            score = 50.0
            # Distance bonus (max 30 pts)
            score += max(0.0, 30.0 * (1.0 - (dist_km / 25.0)))
            # Medical certification bonus
            if prof.medical_certified:
                score += 10.0
            # Vehicle capability bonus
            if prof.vehicle_type:
                score += 10.0

            score = round(min(100.0, score), 1)
            ranked.append((vol, score, round(dist_km, 2)))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
