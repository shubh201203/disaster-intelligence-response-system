import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON
from geoalchemy2 import Geometry
from app.database import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_code = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    disaster_type = Column(String(100), nullable=False, index=True) # FLOOD, CYCLONE, FIRE, LANDSLIDE, EARTHQUAKE
    description = Column(Text, nullable=False)
    
    # Status & Priority Lifecycle
    # Status: REPORTED -> AI_ANALYZED -> PENDING_VERIFICATION -> VERIFIED -> PRIORITIZED -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CLOSED
    status = Column(String(50), default="REPORTED", index=True)
    priority_level = Column(String(20), default="MEDIUM", index=True) # CRITICAL, HIGH, MEDIUM, LOW
    priority_score = Column(Float, default=50.0) # 0 to 100
    severity_level = Column(String(20), default="MEDIUM") # CRITICAL, HIGH, MEDIUM, LOW
    confidence_score = Column(Float, default=75.0) # 0 to 100
    
    # Location & PostGIS Spatial Geometry
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geom = Column(Geometry(geometry_type='POINT', srid=4326, spatial_index=False, use_typmod=True), nullable=True)
    location_address = Column(String(500), nullable=True)
    
    # Demographics & Impact
    people_affected = Column(Integer, default=1)
    injuries = Column(Integer, default=0)
    vulnerable_count = Column(Integer, default=0) # children, elderly
    infrastructure_damage = Column(Text, nullable=True)
    
    # Phase 5F Data Foundation Extensions
    required_skills = Column(JSON, default=dict, nullable=True) # e.g. {"MEDICAL": 2, "RESCUE": 4} (d_ikt)
    evacuation_demographics = Column(JSON, default=dict, nullable=True) # e.g. {"GEN": 80, "ACC": 15, "MED": 5, "MED_ACC": 2} (p_ig)
    
    # Cluster & Duplicates
    cluster_id = Column(String(36), ForeignKey("incident_clusters.id"), nullable=True)
    is_duplicate = Column(Float, default=0.0) # 0 to 1
    
    # AI Explainability Details
    ai_breakdown = Column(JSON, default=dict)
    cv_evidence_tags = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

    @property
    def media_urls(self):
        urls = []
        from sqlalchemy.orm import object_session
        sess = object_session(self)
        if sess is not None:
            records = (
                sess.query(IncidentMedia.file_path)
                .filter(IncidentMedia.incident_id == self.id)
                .order_by(IncidentMedia.created_at.asc())
                .all()
            )
            for r in records:
                if r[0] and r[0] not in urls:
                    urls.append(r[0])
            reports = (
                sess.query(IncidentReport.media_urls)
                .filter(IncidentReport.incident_id == self.id)
                .all()
            )
            for rep in reports:
                if rep[0] and isinstance(rep[0], list):
                    for u in rep[0]:
                        if u and not str(u).startswith("data:") and u not in urls:
                            urls.append(u)
        return urls

class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    reporter_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    report_text = Column(Text, nullable=False)
    media_urls = Column(JSON, default=list)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class IncidentMedia(Base):
    __tablename__ = "incident_media"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    uploader_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    media_type = Column(String(50), default="IMAGE") # IMAGE, VIDEO
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class IncidentCluster(Base):
    __tablename__ = "incident_clusters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cluster_code = Column(String(50), unique=True, nullable=False)
    primary_incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    duplicate_count = Column(Integer, default=1)
    spatial_radius_m = Column(Float, default=500.0)
    temporal_span_min = Column(Integer, default=60)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
