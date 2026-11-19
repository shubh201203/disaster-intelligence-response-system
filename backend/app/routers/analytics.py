from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.incident import Incident
from app.models.shelter import Shelter
from app.models.user import User
from app.models.resource import Resource

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary")
def get_analytics_summary(db: Session = Depends(get_db)):
    active_incidents = db.query(func.count(Incident.id)).filter(Incident.status.in_(["REPORTED", "VERIFIED", "IN_PROGRESS"])).scalar() or 0
    critical_incidents = db.query(func.count(Incident.id)).filter(Incident.priority_level == "CRITICAL", Incident.status != "CLOSED").scalar() or 0
    total_affected = db.query(func.sum(Incident.people_affected)).scalar() or 0
    total_injured = db.query(func.sum(Incident.injuries)).scalar() or 0
    
    total_capacity = db.query(func.sum(Shelter.total_capacity)).scalar() or 0
    total_occupancy = db.query(func.sum(Shelter.current_occupancy)).scalar() or 0
    
    active_volunteers = db.query(func.count(User.id)).filter(User.role == "VOLUNTEER", User.is_active == True).scalar() or 0
    total_resources = db.query(func.sum(Resource.available_quantity)).scalar() or 0

    return {
        "active_disasters": 1,
        "active_incidents": active_incidents,
        "critical_incidents": critical_incidents,
        "people_affected": total_affected,
        "people_injured": total_injured,
        "active_volunteers": active_volunteers,
        "total_resources_available": total_resources,
        "shelter_total_capacity": total_capacity,
        "shelter_current_occupancy": total_occupancy,
        "shelter_occupancy_rate": round((total_occupancy / float(max(1, total_capacity))) * 100, 1)
    }
