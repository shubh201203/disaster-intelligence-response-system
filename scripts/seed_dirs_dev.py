import os
import sys

# Explicitly set DATABASE_URL for Playwright dirs_dev.db BEFORE importing app.database
dirs_dev_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dirs_dev.db"))
os.environ["DATABASE_URL"] = f"sqlite:///{dirs_dev_path}"

# Suppress GeoAlchemy DDL for SQLite
import geoalchemy2.admin
import geoalchemy2.admin.dialects.sqlite
from geoalchemy2.types import _GISType
from geoalchemy2 import Geometry
from sqlalchemy.ext.compiler import compiles

geoalchemy2.admin.dialects.sqlite.after_create = lambda *a, **k: None
geoalchemy2.admin.dialects.sqlite.before_drop = lambda *a, **k: None
geoalchemy2.admin.after_create = lambda *a, **k: None
geoalchemy2.admin.before_drop = lambda *a, **k: None
_GISType.bind_expression = lambda self, b: b
_GISType.column_expression = lambda self, c: c

@compiles(Geometry, 'sqlite')
def compile_geom(el, comp, **kw): return "TEXT"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, Incident, RescueTask, Resource, Shelter, Alert, AuditLog
from app.core.security import get_password_hash
from app.ai.rag.service import RAGService

def seed_dirs_dev():
    print(f"Seeding Playwright Database at: {dirs_dev_path}")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # Clear old tables
        db.query(AuditLog).delete()
        db.query(RescueTask).delete()
        db.query(Alert).delete()
        db.query(Resource).delete()
        db.query(Shelter).delete()
        db.query(Incident).delete()
        db.query(User).delete()
        db.commit()

        # Seed users required by Playwright E2E specs
        admin_user = User(email="admin@dirs.gov", hashed_password=get_password_hash("Admin123!"), full_name="Disaster Commissioner", role="GOVT", phone="+91-11-20000000")
        citizen_user = User(email="citizen@dirs.org", hashed_password=get_password_hash("Citizen123!"), full_name="Rahul Sharma", role="CITIZEN", phone="+91-9876543210")
        volunteer_user = User(email="volunteer@dirs.org", hashed_password=get_password_hash("Volunteer123!"), full_name="Priya Patel", role="VOLUNTEER", phone="+91-9876543211")
        ngo_user = User(email="ngo@dirs.org", hashed_password=get_password_hash("Ngo123!"), full_name="NGO Manager", role="NGO", phone="+91-9876543212")
        
        db.add_all([admin_user, citizen_user, volunteer_user, ngo_user])
        db.commit()

        # Seed initial incident for AI inspect
        inc = Incident(
            incident_code="INC-2026-E2ETEST",
            title="Category 4 Cyclone Vardah Evacuation",
            disaster_type="CYCLONE",
            description="Severe storm surge and wind damage near coastal sector",
            latitude=13.0827,
            longitude=80.2707,
            people_affected=350,
            injuries=25,
            vulnerable_count=45,
            status="VERIFIED"
        )
        db.add(inc)
        db.commit()

        # Seed Knowledge Base
        RAGService.seed_authoritative_knowledge_base(db)
        print("dirs_dev.db successfully seeded for Playwright E2E tests!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_dirs_dev()
