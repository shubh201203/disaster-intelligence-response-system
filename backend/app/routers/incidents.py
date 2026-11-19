import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.incident import Incident, IncidentMedia
from app.schemas.incident import IncidentCreate, IncidentResponse, IncidentVerifyRequest, IncidentMergeRequest
from app.services.incident_service import IncidentService
from app.services.gis_service import GISService
from app.core.deps import get_current_user, require_role
from app.core.websocket_manager import ws_manager
from app.core.idempotency import idempotency_service, get_idempotency_key

router = APIRouter(prefix="/incidents", tags=["Incidents"])

@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident_in: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Depends(get_idempotency_key)
):
    if idempotency_key:
        fingerprint = idempotency_service.compute_fingerprint(incident_in)
        is_cached, cached_res = idempotency_service.check_or_lock(
            key=idempotency_key,
            user_id=str(current_user.id),
            endpoint="/api/v1/incidents",
            fingerprint=fingerprint
        )
        if is_cached:
            return cached_res

    try:
        incident = IncidentService.create_incident(db, incident_in, current_user)

        if idempotency_key:
            res_dict = IncidentResponse.model_validate(incident).model_dump(mode="json")
            idempotency_service.store_result(
                key=idempotency_key,
                user_id=str(current_user.id),
                endpoint="/api/v1/incidents",
                response_data=res_dict,
                status_code=status.HTTP_201_CREATED
            )
    except Exception:
        if idempotency_key:
            idempotency_service.release_lock(
                key=idempotency_key,
                user_id=str(current_user.id),
                endpoint="/api/v1/incidents"
            )
        raise

    # Standardized WebSocket Event (Isolated so broadcast failure does not corrupt idempotency)
    try:
        await ws_manager.broadcast_event(
            event_type="INCIDENT_CREATED",
            entity_type="Incident",
            entity_id=incident.id,
            data={
                "incident_code": incident.incident_code,
                "title": incident.title,
                "priority_level": incident.priority_level,
                "priority_score": incident.priority_score,
                "latitude": incident.latitude,
                "longitude": incident.longitude,
                "disaster_type": incident.disaster_type
            }
        )
    except Exception:
        pass

    return incident

@router.post("/sos", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def trigger_sos_distress(
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    location_address: Optional[str] = Query(None),
    description: Optional[str] = Query("EMERGENCY SOS PANIC SIGNAL TRIGGERED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    has_gps = lat is not None and lng is not None
    lat_val = lat if has_gps else 0.0
    lng_val = lng if has_gps else 0.0

    loc_desc = location_address or ("Exact GPS unavailable / denied by citizen" if not has_gps else "Citizen GPS Coordinates")
    full_description = f"HIGH PRIORITY SOS: {description}"
    if not has_gps:
        full_description = f"[LOCATION_UNAVAILABLE] {full_description} • Location notes: {loc_desc}"

    sos_data = IncidentCreate(
        title="EMERGENCY SOS DISTRESS SIGNAL",
        disaster_type="FLOOD",
        description=full_description,
        latitude=lat_val,
        longitude=lng_val,
        location_address=loc_desc,
        people_affected=1,
        injuries=0,
        vulnerable_count=0
    )
    incident = IncidentService.create_incident(db, sos_data, current_user)
    incident.priority_level = "CRITICAL"
    incident.priority_score = 99.0

    if not has_gps:
        # Clear spatial geom if coordinates were unavailable
        incident.geom = None

    db.commit()

    # Broadcast SOS payload
    await ws_manager.broadcast_event(
        event_type="SOS_TRIGGERED",
        entity_type="Incident",
        entity_id=incident.id,
        data={
            "incident_code": incident.incident_code,
            "user_name": current_user.full_name,
            "latitude": lat,
            "longitude": lng,
            "has_gps": has_gps,
            "location_address": loc_desc,
            "priority_score": 99.0
        }
    )

    return incident

@router.get("", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[str] = Query(None),
    disaster_type: Optional[str] = Query(None),
    priority_level: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    return IncidentService.get_incidents(db, status, disaster_type, priority_level, limit)

@router.get("/nearby", response_model=List[IncidentResponse])
def get_nearby_incidents(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(10.0, le=100.0),
    db: Session = Depends(get_db)
):
    results = GISService.get_nearby_incidents(db, lat, lng, radius_km)
    return [inc for inc, dist in results]

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@router.patch("/{incident_id}/status", response_model=IncidentResponse)
async def update_incident_status(
    incident_id: str,
    target_status: str = Query(...),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    try:
        updated = IncidentService.transition_incident_status(db, incident, target_status, current_user, notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await ws_manager.broadcast_event(
        event_type="INCIDENT_STATUS_UPDATED",
        entity_type="Incident",
        entity_id=updated.id,
        data={"status": updated.status, "updated_by": current_user.full_name}
    )

    return updated

@router.put("/{incident_id}/verify", response_model=IncidentResponse)
async def verify_incident(
    incident_id: str,
    verify_in: IncidentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    target_status = "VERIFIED" if verify_in.action.upper() == "VERIFY" else "CLOSED"
    try:
        updated = IncidentService.transition_incident_status(db, incident, target_status, current_user, verify_in.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await ws_manager.broadcast_event(
        event_type="INCIDENT_VERIFIED",
        entity_type="Incident",
        entity_id=updated.id,
        data={"status": updated.status, "verified_by": current_user.full_name}
    )

    return updated

@router.post("/{incident_id}/merge")
async def merge_incidents(
    incident_id: str,
    merge_in: IncidentMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    try:
        cluster = IncidentService.merge_duplicate_reports(db, incident_id, merge_in.duplicate_incident_ids, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await ws_manager.broadcast_event(
        event_type="INCIDENTS_MERGED",
        entity_type="IncidentCluster",
        entity_id=cluster.id,
        data={"cluster_code": cluster.cluster_code, "primary_id": primary_id if 'primary_id' in locals() else incident_id}
    )

    return {"message": "Incidents merged successfully", "cluster_code": cluster.cluster_code}

@router.post("/{incident_id}/media")
async def upload_incident_media(
    incident_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    ALLOWED_MIME_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp", "video/mp4"]
    clean_mime = (file.content_type or "").split(";")[0].strip().lower()
    if clean_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}. Allowed: {ALLOWED_MIME_TYPES}")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds maximum 10MB limit")

    os.makedirs(settings.MEDIA_UPLOAD_DIR, exist_ok=True)
    raw_ext = os.path.splitext(file.filename or "")[1].lower()
    ext = raw_ext if raw_ext in [".jpg", ".jpeg", ".png", ".webp", ".mp4"] else ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    disk_path = os.path.join(settings.MEDIA_UPLOAD_DIR, unique_name)

    with open(disk_path, "wb") as f:
        f.write(content)

    web_path = f"/static/uploads/{unique_name}"
    media = IncidentMedia(
        incident_id=incident_id,
        uploader_id=current_user.id,
        file_name=file.filename or unique_name,
        file_path=web_path,
        file_size=len(content),
        mime_type=clean_mime,
        media_type="VIDEO" if "video" in clean_mime else "IMAGE"
    )
    db.add(media)
    incident.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(media)

    return {
        "message": "Media uploaded successfully",
        "media_id": media.id,
        "file_path": media.file_path,
        "file_name": media.file_name
    }

@router.get("/{incident_id}/media")
def list_incident_media(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves all uploaded media attachments associated with an incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    media_records = db.query(IncidentMedia).filter(IncidentMedia.incident_id == incident_id).all()
    return [
        {
            "id": m.id,
            "incident_id": m.incident_id,
            "file_name": m.file_name,
            "file_path": m.file_path,
            "file_size": m.file_size,
            "mime_type": m.mime_type,
            "media_type": m.media_type,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in media_records
    ]
