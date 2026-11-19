from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.incident import Incident
from app.models.rescue import RescueTask
from app.schemas.user import UserResponse
from app.services.rescue_service import RescueService
from app.core.deps import get_current_user, require_role
from app.core.websocket_manager import ws_manager

router = APIRouter(prefix="/volunteers", tags=["Volunteers"])

@router.get("", response_model=List[UserResponse])
def list_volunteers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    volunteers = db.query(User).filter(User.role == "VOLUNTEER").all()
    return volunteers

@router.get("/me", response_model=UserResponse)
def get_volunteer_me(current_user: User = Depends(get_current_user)):
    if current_user.role != "VOLUNTEER" and current_user.role != "GOVT":
        raise HTTPException(status_code=403, detail="Only volunteers can access this endpoint")
    return current_user

@router.get("/recommended/{incident_id}")
def get_recommended_volunteers(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    ranked = RescueService.rank_candidate_volunteers(db, incident)
    return [
        {
            "user_id": vol.id,
            "full_name": vol.full_name,
            "suitability_score": score,
            "distance_km": dist,
            "skills": vol.volunteer_profile.skills if vol.volunteer_profile else [],
            "vehicle": vol.volunteer_profile.vehicle_type if vol.volunteer_profile else None
        }
        for vol, score, dist in ranked
    ]

@router.post("/assign", status_code=status.HTTP_201_CREATED)
async def assign_rescue_task(
    incident_id: str = Query(...),
    volunteer_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    try:
        task = RescueService.assign_rescue_task(db, incident_id, "VOLUNTEER", volunteer_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await ws_manager.broadcast_event(
        event_type="TASK_ASSIGNED",
        entity_type="RescueTask",
        entity_id=task.id,
        data={"incident_id": incident_id, "volunteer_id": volunteer_id, "status": task.status}
    )

    return {"message": "Rescue task assigned successfully", "task_id": task.id}

@router.post("/claim", status_code=status.HTTP_201_CREATED)
@router.post("/incidents/{incident_id}/claim", status_code=status.HTTP_201_CREATED)
@router.post("/incidents/{incident_id}/accept", status_code=status.HTTP_201_CREATED)
async def claim_incident_task(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allows an eligible volunteer or government coordinator to claim and accept
    an unassigned verified incident. Enforces concurrency protection so multiple
    responders cannot claim the same task.
    """
    if current_user.role not in ["VOLUNTEER", "GOVT"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only registered volunteers or government officers can claim emergency response tasks."
        )

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident record not found.")

    # Concurrency guard: Check if an active non-completed task already exists
    active_statuses = ["ASSIGNED", "ACCEPTED", "EN_ROUTE", "ARRIVED", "RESCUE_STARTED"]
    existing_task = db.query(RescueTask).filter(
        RescueTask.incident_id == incident_id,
        RescueTask.status.in_(active_statuses)
    ).first()

    if existing_task:
        if existing_task.assigned_id == current_user.id:
            return {
                "message": "Task already assigned to you.",
                "task_id": existing_task.id,
                "status": existing_task.status
            }
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident is already claimed by another tactical responder."
        )

    # Create new task directly in ACCEPTED state
    task = RescueTask(
        incident_id=incident.id,
        assigned_type="VOLUNTEER",
        assigned_id=current_user.id,
        status="ACCEPTED"
    )
    db.add(task)

    if incident.status in ["VERIFIED", "REPORTED", "PRIORITIZED"]:
        incident.status = "ASSIGNED"

    db.commit()
    db.refresh(task)

    from app.services.audit_service import AuditService
    AuditService.log_action(
        db, current_user.id, "TASK_CLAIMED_BY_VOLUNTEER", "RescueTask",
        {"task_id": task.id, "incident_id": incident.id, "volunteer_id": current_user.id}
    )

    await ws_manager.broadcast_event(
        event_type="TASK_ASSIGNED",
        entity_type="RescueTask",
        entity_id=task.id,
        data={"incident_id": incident.id, "volunteer_id": current_user.id, "status": task.status}
    )

    return {
        "message": "Incident successfully claimed and task accepted.",
        "task_id": task.id,
        "status": task.status
    }

@router.get("/my-tasks")
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns rescue tasks assigned to the current volunteer.
    Enforces that volunteers can only retrieve their own assigned tasks.
    """
    tasks = db.query(RescueTask).filter(
        RescueTask.assigned_id == current_user.id
    ).order_by(RescueTask.assigned_at.desc()).all()

    result = []
    for t in tasks:
        inc = db.query(Incident).filter(Incident.id == t.incident_id).first()
        result.append({
            "id": t.id,
            "incident_id": t.incident_id,
            "incident_code": inc.incident_code if inc else "INC-UNKNOWN",
            "incident_title": inc.title if inc else "Assigned Emergency Task",
            "incident_description": inc.description if inc else "",
            "location_address": inc.location_address if inc else "Sector Operational Zone",
            "latitude": inc.latitude if inc else 0.0,
            "longitude": inc.longitude if inc else 0.0,
            "priority_level": inc.priority_level if inc else "HIGH",
            "people_affected": inc.people_affected if inc else 0,
            "injuries": inc.injuries if inc else 0,
            "vulnerable_count": inc.vulnerable_count if inc else 0,
            "status": t.status,
            "assigned_at": t.assigned_at.isoformat() if t.assigned_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None
        })
    return result

@router.get("/tasks")
def list_all_rescue_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    """
    Returns all rescue tasks across the emergency operations system for Government Command review.
    """
    tasks = db.query(RescueTask).order_by(RescueTask.assigned_at.desc()).all()
    result = []
    for t in tasks:
        inc = db.query(Incident).filter(Incident.id == t.incident_id).first()
        assignee = db.query(User).filter(User.id == t.assigned_id).first()
        result.append({
            "id": t.id,
            "incident_id": t.incident_id,
            "incident_code": inc.incident_code if inc else "INC-UNKNOWN",
            "incident_title": inc.title if inc else "Assigned Task",
            "assigned_id": t.assigned_id,
            "assigned_name": assignee.full_name if assignee else "Unknown",
            "status": t.status,
            "assigned_at": t.assigned_at.isoformat() if t.assigned_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None
        })
    return result

@router.post("/tasks/{task_id}/status")
@router.patch("/tasks/{task_id}/status")
async def update_task_status(
    task_id: str,
    target_status: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(RescueTask).filter(RescueTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Rescue task not found")

    try:
        updated_task = RescueService.transition_task_status(db, task, target_status, current_user)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    await ws_manager.broadcast_event(
        event_type="TASK_STATUS_UPDATED",
        entity_type="RescueTask",
        entity_id=updated_task.id,
        data={"status": updated_task.status, "updated_by": current_user.full_name}
    )

    return {"message": "Task status updated", "task_id": updated_task.id, "status": updated_task.status}
