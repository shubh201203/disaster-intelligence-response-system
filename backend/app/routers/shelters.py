from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.shelter import Shelter
from app.schemas.shelter import ShelterCreate, ShelterResponse
from app.services.shelter_service import ShelterService
from app.services.gis_service import GISService
from app.core.deps import require_role
from app.core.websocket_manager import ws_manager

router = APIRouter(prefix="/shelters", tags=["Shelters"])

@router.get("", response_model=List[ShelterResponse])
def list_shelters(db: Session = Depends(get_db)):
    shelters = ShelterService.get_shelters(db)
    return [ShelterResponse.model_validate(s) for s in shelters]

@router.post("", response_model=ShelterResponse, status_code=status.HTTP_201_CREATED)
async def create_shelter(
    shelter_in: ShelterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    shelter = ShelterService.create_shelter(db, shelter_in)

    await ws_manager.broadcast_event(
        event_type="SHELTER_UPDATED",
        entity_type="Shelter",
        entity_id=shelter.id,
        data={"name": shelter.name, "occupancy": shelter.current_occupancy, "capacity": shelter.total_capacity}
    )

    return ShelterResponse.model_validate(shelter)

@router.patch("/{shelter_id}", response_model=ShelterResponse)
async def update_shelter(
    shelter_id: str,
    occupancy: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("GOVT"))
):
    shelter = db.query(Shelter).filter(Shelter.id == shelter_id).first()
    if not shelter:
        raise HTTPException(status_code=404, detail="Shelter not found")

    if occupancy is not None:
        if occupancy > shelter.total_capacity:
            raise HTTPException(status_code=400, detail="Occupancy cannot exceed total capacity")
        shelter.current_occupancy = occupancy

    if status is not None:
        shelter.status = status.upper()

    db.commit()
    db.refresh(shelter)

    await ws_manager.broadcast_event(
        event_type="SHELTER_UPDATED",
        entity_type="Shelter",
        entity_id=shelter.id,
        data={"name": shelter.name, "occupancy": shelter.current_occupancy, "status": shelter.status}
    )

    return ShelterResponse.model_validate(shelter)

@router.get("/nearby", response_model=List[ShelterResponse])
def get_nearby_shelters(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(15.0),
    db: Session = Depends(get_db)
):
    nearby = GISService.get_nearby_shelters(db, lat, lng, radius_km)
    results = []
    for shelter, dist in nearby:
        s_resp = ShelterService.calculate_shelter_suitability(shelter, lat, lng)
        results.append(s_resp)
    results.sort(key=lambda x: x.suitability_score or 0, reverse=True)
    return results
