from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.resource import Resource, ResourceRequest
from app.models.incident import Incident
from app.models.user import User
from app.services.gis_service import haversine_distance_km
from app.services.audit_service import AuditService

class ResourceService:
    @staticmethod
    def create_resource_inventory(
        db: Session,
        owner_type: str,
        owner: User,
        category: str,
        resource_name: str,
        quantity: int,
        unit: str = "units",
        lat: float = None,
        lng: float = None
    ) -> Resource:
        res = Resource(
            owner_type=owner_type.upper(),
            owner_id=owner.id,
            category=category.upper(),
            resource_name=resource_name,
            total_quantity=quantity,
            available_quantity=quantity,
            unit=unit,
            location_lat=lat,
            location_lng=lng
        )
        db.add(res)
        db.commit()
        db.refresh(res)

        AuditService.log_action(db, owner.id, "RESOURCE_CREATED", "Resource", {"resource_id": res.id, "category": category, "quantity": quantity})
        return res

    @staticmethod
    def reserve_and_dispatch_resource(db: Session, resource_id: str, quantity_to_dispatch: int, actor: User) -> Resource:
        resource = db.query(Resource).filter(Resource.id == resource_id).with_for_update().first()
        if not resource:
            raise ValueError("Resource stock record not found")

        if resource.available_quantity < quantity_to_dispatch:
            raise ValueError(f"Insufficient stock available. Requested: {quantity_to_dispatch}, Available: {resource.available_quantity}")

        # Transactional stock update
        resource.available_quantity -= quantity_to_dispatch
        db.commit()
        db.refresh(resource)

        AuditService.log_action(
            db, actor.id, "RESOURCE_DISPATCHED", "Resource",
            {"resource_id": resource.id, "dispatched_quantity": quantity_to_dispatch, "remaining_available": resource.available_quantity}
        )

        return resource

    @staticmethod
    def rank_resource_sources_for_incident(db: Session, incident: Incident, category: str) -> List[Tuple[Resource, float, float]]:
        resources = db.query(Resource).filter(
            Resource.category == category.upper(),
            Resource.available_quantity > 0
        ).all()

        ranked = []
        for res in resources:
            dist_km = 5.0
            if res.location_lat and res.location_lng:
                dist_km = haversine_distance_km(incident.latitude, incident.longitude, res.location_lat, res.location_lng)

            # Allocation score out of 100
            score = 40.0
            # Distance score (max 30 pts)
            score += max(0.0, 30.0 * (1.0 - (dist_km / 30.0)))
            # Quantity availability score (max 30 pts)
            score += min(30.0, (res.available_quantity / 100.0) * 10.0)

            score = round(min(100.0, score), 1)
            ranked.append((res, score, round(dist_km, 2)))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
