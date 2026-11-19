import os
import base64
import random
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
from app.config import settings
from app.models.incident import Incident, IncidentReport, IncidentCluster, IncidentMedia
from app.models.user import User
from app.schemas.incident import IncidentCreate
from app.services.audit_service import AuditService

ALLOWED_STATUS_TRANSITIONS = {
    "REPORTED": ["AI_ANALYZED", "PENDING_VERIFICATION", "VERIFIED", "CLOSED"],
    "AI_ANALYZED": ["PENDING_VERIFICATION", "VERIFIED", "CLOSED"],
    "PENDING_VERIFICATION": ["VERIFIED", "CLOSED"],
    "VERIFIED": ["PRIORITIZED", "ASSIGNED", "CLOSED"],
    "PRIORITIZED": ["ASSIGNED", "CLOSED"],
    "ASSIGNED": ["IN_PROGRESS", "CLOSED"],
    "IN_PROGRESS": ["RESOLVED", "CLOSED"],
    "RESOLVED": ["CLOSED"],
    "CLOSED": []
}

def generate_incident_code() -> str:
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"INC-{datetime.now().year}-{unique_suffix}"

def calculate_initial_severity_and_priority(data: IncidentCreate) -> Tuple[float, str, str, dict]:
    base_score = 40.0
    breakdown = {}

    if data.people_affected > 50:
        base_score += 25
        breakdown["people_affected_bonus"] = 25
    elif data.people_affected > 10:
        base_score += 15
        breakdown["people_affected_bonus"] = 15
    else:
        breakdown["people_affected_bonus"] = 5

    if data.injuries > 10:
        base_score += 20
        breakdown["injuries_bonus"] = 20
    elif data.injuries > 0:
        base_score += 10
        breakdown["injuries_bonus"] = 10

    if data.vulnerable_count > 5:
        base_score += 15
        breakdown["vulnerable_bonus"] = 15

    type_weights = {
        "FLOOD": 10,
        "CYCLONE": 15,
        "FIRE": 15,
        "LANDSLIDE": 10,
        "EARTHQUAKE": 20
    }
    disaster_bonus = type_weights.get(data.disaster_type.upper(), 5)
    base_score += disaster_bonus
    breakdown["disaster_type_bonus"] = disaster_bonus

    priority_score = min(100.0, max(10.0, base_score))

    if priority_score >= 80:
        priority_level = "CRITICAL"
        severity_level = "CRITICAL"
    elif priority_score >= 60:
        priority_level = "HIGH"
        severity_level = "HIGH"
    elif priority_score >= 40:
        priority_level = "MEDIUM"
        severity_level = "MEDIUM"
    else:
        priority_level = "LOW"
        severity_level = "LOW"

    return priority_score, priority_level, severity_level, breakdown

class IncidentService:
    @staticmethod
    def create_incident(db: Session, data: IncidentCreate, reporter: User) -> Incident:
        code = generate_incident_code()
        score, p_level, s_level, breakdown = calculate_initial_severity_and_priority(data)

        incident_kwargs = {
            "incident_code": code,
            "title": data.title,
            "disaster_type": data.disaster_type,
            "description": data.description,
            "latitude": data.latitude,
            "longitude": data.longitude,
            "location_address": data.location_address,
            "people_affected": data.people_affected,
            "injuries": data.injuries,
            "vulnerable_count": data.vulnerable_count,
            "infrastructure_damage": data.infrastructure_damage,
            "status": "REPORTED",
            "priority_level": p_level,
            "priority_score": score,
            "severity_level": s_level,
            "confidence_score": 85.0,
            "ai_breakdown": breakdown,
            "cv_evidence_tags": ["FLOODED_ROADS"] if data.disaster_type.upper() == "FLOOD" else []
        }

        if db.bind and db.bind.dialect.name == "postgresql":
            incident_kwargs["geom"] = ST_SetSRID(ST_MakePoint(data.longitude, data.latitude), 4326)

        incident = Incident(**incident_kwargs)
        db.add(incident)
        db.commit()
        db.refresh(incident)

        # Persist media attachments if provided (supports raw static paths, external URLs, and base64 offline data)
        cleaned_media_urls: List[str] = []
        if data.media_urls:
            os.makedirs(settings.MEDIA_UPLOAD_DIR, exist_ok=True)
            for item in data.media_urls:
                if not item or not isinstance(item, str):
                    continue
                clean_item = item.strip()
                if clean_item.startswith("data:image/"):
                    try:
                        header, b64_data = clean_item.split(",", 1)
                        mime = header.split(";")[0].replace("data:", "").strip().lower()
                        raw_ext = mime.split("/")[-1].lower()
                        ext = f".{raw_ext}" if raw_ext in ["jpg", "jpeg", "png", "webp"] else ".png"
                        img_bytes = base64.b64decode(b64_data)
                        if len(img_bytes) <= 10 * 1024 * 1024:
                            unique_name = f"{uuid.uuid4().hex}{ext}"
                            disk_path = os.path.join(settings.MEDIA_UPLOAD_DIR, unique_name)
                            with open(disk_path, "wb") as f:
                                f.write(img_bytes)
                            web_path = f"/static/uploads/{unique_name}"
                            med = IncidentMedia(
                                incident_id=incident.id,
                                uploader_id=reporter.id,
                                file_name=unique_name,
                                file_path=web_path,
                                file_size=len(img_bytes),
                                mime_type=mime,
                                media_type="IMAGE"
                            )
                            db.add(med)
                            cleaned_media_urls.append(web_path)
                    except Exception as b64_err:
                        print("Failed to decode base64 incident media:", b64_err)
                elif clean_item.startswith("/static/uploads/") or clean_item.startswith("http"):
                    med = IncidentMedia(
                        incident_id=incident.id,
                        uploader_id=reporter.id,
                        file_name=os.path.basename(clean_item),
                        file_path=clean_item,
                        file_size=0,
                        mime_type="image/jpeg",
                        media_type="IMAGE"
                    )
                    db.add(med)
                    cleaned_media_urls.append(clean_item)

        # Create report record
        report = IncidentReport(
            incident_id=incident.id,
            reporter_id=reporter.id,
            report_text=data.description,
            media_urls=cleaned_media_urls,
            latitude=data.latitude,
            longitude=data.longitude
        )
        db.add(report)
        db.commit()

        # Audit log
        AuditService.log_action(db, reporter.id, "INCIDENT_CREATED", "Incident", {"incident_code": code, "disaster_type": data.disaster_type})

        return incident

    @staticmethod
    def transition_incident_status(db: Session, incident: Incident, target_status: str, actor: User, notes: Optional[str] = None) -> Incident:
        current = incident.status
        target = target_status.upper()

        if target not in ALLOWED_STATUS_TRANSITIONS.get(current, []):
            raise ValueError(f"Invalid incident state transition from '{current}' to '{target}'. Allowed transitions: {ALLOWED_STATUS_TRANSITIONS.get(current, [])}")

        incident.status = target
        if target == "RESOLVED" or target == "CLOSED":
            incident.resolved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(incident)

        AuditService.log_action(
            db, actor.id, "INCIDENT_STATUS_TRANSITION", "Incident",
            {"incident_id": incident.id, "from_status": current, "to_status": target, "notes": notes}
        )

        return incident

    @staticmethod
    def merge_duplicate_reports(db: Session, primary_incident_id: str, duplicate_incident_ids: List[str], admin: User) -> IncidentCluster:
        primary = db.query(Incident).filter(Incident.id == primary_incident_id).first()
        if not primary:
            raise ValueError("Primary incident not found")

        cluster_code = f"CLUSTER-{random.randint(1000, 9999)}"
        cluster = IncidentCluster(
            cluster_code=cluster_code,
            primary_incident_id=primary.id,
            duplicate_count=len(duplicate_incident_ids) + 1,
            spatial_radius_m=500.0,
            temporal_span_min=60
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)

        primary.cluster_id = cluster.id

        # Update duplicates
        for dup_id in duplicate_incident_ids:
            dup = db.query(Incident).filter(Incident.id == dup_id).first()
            if dup and dup.id != primary.id:
                dup.cluster_id = cluster.id
                dup.is_duplicate = 1.0
                dup.status = "CLOSED"
                # Combine affected demographics into primary
                primary.people_affected += dup.people_affected
                primary.injuries += dup.injuries

        db.commit()

        AuditService.log_action(
            db, admin.id, "INCIDENT_MERGED", "IncidentCluster",
            {"cluster_code": cluster_code, "primary_id": primary.id, "duplicate_ids": duplicate_incident_ids}
        )

        return cluster

    @staticmethod
    def get_incidents(
        db: Session,
        status: Optional[str] = None,
        disaster_type: Optional[str] = None,
        priority_level: Optional[str] = None,
        limit: int = 100
    ) -> List[Incident]:
        query = db.query(Incident)
        if status:
            query = query.filter(Incident.status == status)
        if disaster_type:
            query = query.filter(Incident.disaster_type == disaster_type)
        if priority_level:
            query = query.filter(Incident.priority_level == priority_level)
        return query.order_by(Incident.priority_score.desc()).limit(limit).all()
