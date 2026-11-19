from typing import List
from sqlalchemy.orm import Session
from app.models.shelter import Shelter
from app.schemas.shelter import ShelterCreate, ShelterResponse
from app.services.gis_service import GISService, haversine_distance_km

class ShelterService:
    @staticmethod
    def create_shelter(db: Session, data: ShelterCreate) -> Shelter:
        shelter = Shelter(
            name=data.name,
            address=data.address,
            total_capacity=data.total_capacity,
            current_occupancy=data.current_occupancy,
            latitude=data.latitude,
            longitude=data.longitude,
            has_medical=data.has_medical,
            has_food=data.has_food,
            has_water=data.has_water,
            disaster_risk_level=data.disaster_risk_level,
            status=data.status
        )
        db.add(shelter)
        db.commit()
        db.refresh(shelter)
        return shelter

    @staticmethod
    def get_shelters(db: Session) -> List[Shelter]:
        return db.query(Shelter).all()

    @staticmethod
    def calculate_shelter_suitability(shelter: Shelter, user_lat: float, user_lng: float) -> ShelterResponse:
        dist_km = haversine_distance_km(user_lat, user_lng, shelter.latitude, shelter.longitude)

        # Multi-criteria Decision Analysis (MCDA) Scoring (0-100)
        # Distance score (max 40 pts): 0km = 40, >20km = 0
        dist_score = max(0.0, 40.0 * (1.0 - (dist_km / 20.0)))

        # Capacity score (max 30 pts): Occupancy < 80% is good
        capacity_remaining = shelter.total_capacity - shelter.current_occupancy
        occupancy_ratio = shelter.current_occupancy / float(max(1, shelter.total_capacity))
        capacity_score = max(0.0, 30.0 * (1.0 - occupancy_ratio))

        # Facility bonuses (max 30 pts)
        facility_score = 0.0
        if shelter.has_medical:
            facility_score += 10.0
        if shelter.has_food:
            facility_score += 10.0
        if shelter.has_water:
            facility_score += 10.0

        suitability = round(min(100.0, dist_score + capacity_score + facility_score), 1)

        resp = ShelterResponse.model_validate(shelter)
        resp.suitability_score = suitability
        resp.distance_km = round(dist_km, 2)
        return resp
