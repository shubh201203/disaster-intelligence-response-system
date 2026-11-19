from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.incident import Incident
from app.models.resource import Resource, ResourceRequest
from app.schemas.resource import ResourceCreate, ResourceResponse, ResourceRequestCreate
from app.services.resource_service import ResourceService
from app.core.deps import get_current_user, require_any_role
from app.core.websocket_manager import ws_manager

router = APIRouter(prefix="/resources", tags=["Resources"])

@router.get("", response_model=List[ResourceResponse])
def list_resources(db: Session = Depends(get_db)):
    resources = db.query(Resource).all()
    return resources

@router.get("/recommended/{incident_id}")
def get_recommended_resources(
    incident_id: str,
    category: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    ranked = ResourceService.rank_resource_sources_for_incident(db, incident, category)
    return [
        {
            "resource_id": res.id,
            "resource_name": res.resource_name,
            "category": res.category,
            "available_quantity": res.available_quantity,
            "unit": res.unit,
            "allocation_score": score,
            "distance_km": dist
        }
        for res, score, dist in ranked
    ]

@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource_in: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(["NGO", "GOVT"]))
):
    resource = ResourceService.create_resource_inventory(
        db,
        owner_type=resource_in.owner_type,
        owner=current_user,
        category=resource_in.category,
        resource_name=resource_in.resource_name,
        quantity=resource_in.total_quantity,
        unit=resource_in.unit,
        lat=resource_in.location_lat,
        lng=resource_in.location_lng
    )

    await ws_manager.broadcast_event(
        event_type="RESOURCE_CREATED",
        entity_type="Resource",
        entity_id=resource.id,
        data={"resource_name": resource.resource_name, "quantity": resource.total_quantity}
    )

    return resource

@router.post("/{resource_id}/dispatch", response_model=ResourceResponse)
async def dispatch_resource(
    resource_id: str,
    quantity: Optional[int] = Query(None, gt=0),
    dispatch_quantity: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(["NGO", "GOVT"]))
):
    qty = quantity if quantity is not None else dispatch_quantity
    if qty is None or qty <= 0:
        raise HTTPException(status_code=400, detail="A positive quantity is required for dispatch")

    try:
        updated_resource = ResourceService.reserve_and_dispatch_resource(db, resource_id, qty, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await ws_manager.broadcast_event(
        event_type="RESOURCE_DISPATCHED",
        entity_type="Resource",
        entity_id=updated_resource.id,
        data={"dispatched_quantity": quantity, "remaining": updated_resource.available_quantity}
    )

    return updated_resource

@router.post("/request", status_code=status.HTTP_201_CREATED)
def request_resource(
    req_in: ResourceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = ResourceRequest(
        incident_id=req_in.incident_id,
        requester_id=current_user.id,
        category=req_in.category.upper(),
        quantity_requested=req_in.quantity_requested,
        priority=req_in.priority,
        status="PENDING"
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"message": "Resource request submitted successfully", "request_id": req.id}

@router.get("/requests")
def list_resource_requests(
    incident_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ResourceRequest)
    if incident_id:
        query = query.filter(ResourceRequest.incident_id == incident_id)
    if status:
        query = query.filter(ResourceRequest.status == status.upper())
    requests = query.order_by(ResourceRequest.created_at.desc()).all()
    result = []
    for r in requests:
        inc = db.query(Incident).filter(Incident.id == r.incident_id).first()
        result.append({
            "id": r.id,
            "incident_id": r.incident_id,
            "incident_code": inc.incident_code if inc else "INC-UNKNOWN",
            "incident_title": inc.title if inc else "Emergency Request",
            "category": r.category,
            "quantity_requested": r.quantity_requested,
            "priority": r.priority,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return result

