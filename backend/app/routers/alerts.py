from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertResponse
from app.core.deps import get_current_user, require_role
from app.core.websocket_manager import ws_manager

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=List[AlertResponse])
def list_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
    return alerts

@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_in: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    alert = Alert(
        title=alert_in.title,
        message=alert_in.message,
        alert_type=alert_in.alert_type.upper(),
        target_zone_lat=alert_in.target_zone_lat,
        target_zone_lng=alert_in.target_zone_lng,
        radius_km=alert_in.radius_km,
        created_by=current_user.id
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Broadcast emergency alert live
    await ws_manager.broadcast({
        "type": "EMERGENCY_ALERT",
        "alert_id": alert.id,
        "title": alert.title,
        "message": alert.message,
        "alert_type": alert.alert_type,
        "radius_km": alert.radius_km
    })

    return alert
