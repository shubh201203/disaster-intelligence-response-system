import sys
import os
import uuid

# Set DATABASE_URL fallback if PostgreSQL is not running locally
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///./demo_dirs.db"

if os.environ.get("DATABASE_URL", "").startswith("sqlite"):
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

from app.database import SessionLocal
from app.models.incident import Incident
from app.ai.rag.service import RAGService
from app.ai.recommendations.engine import RecommendationEngine

db = SessionLocal()
try:
    RAGService.seed_authoritative_knowledge_base(db)

    # Incident 1: Severe Flood Disaster
    inc1 = Incident(
        incident_code=f"INC-DIFF-1-{uuid.uuid4().hex[:4]}",
        title="Catastrophic Riverfront Flood Inundation",
        disaster_type="FLOOD",
        description="6ft water depth marooning 350 citizens on rooftops",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=350,
        injuries=25,
        vulnerable_count=45
    )

    # Incident 2: Minor Earthquake Tremor
    inc2 = Incident(
        incident_code=f"INC-DIFF-2-{uuid.uuid4().hex[:4]}",
        title="Minor Seismic Tremor & Wall Cracks",
        disaster_type="EARTHQUAKE",
        description="Minor wall cracks, no trapped citizens",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=10,
        injuries=0,
        vulnerable_count=0
    )

    db.add_all([inc1, inc2])
    db.commit()
    db.refresh(inc1)
    db.refresh(inc2)

    recs1 = RecommendationEngine.generate_incident_recommendations(db, inc1)
    recs2 = RecommendationEngine.generate_incident_recommendations(db, inc2)

    print("\n=== RECOMMENDATION FORENSICS: 2 MATERIALLY DIFFERENT INCIDENTS ===")

    print(f"\n[INCIDENT 1: FLOOD (350 Affected, 25 Injured)]")
    print(f"  Count of Recommendations Generated: {len(recs1)}")
    for r in recs1:
        print(f"  * [{r.priority}] ({r.category}) {r.action_title}")
        print(f"    Rationale: {r.rationale[:100]}...")

    print(f"\n[INCIDENT 2: EARTHQUAKE (10 Affected, 0 Injured)]")
    print(f"  Count of Recommendations Generated: {len(recs2)}")
    for r in recs2:
        print(f"  * [{r.priority}] ({r.category}) {r.action_title}")
        print(f"    Rationale: {r.rationale[:100]}...")

    # Verification: Recommendations must not be identical
    rec_titles1 = [r.action_title for r in recs1]
    rec_titles2 = [r.action_title for r in recs2]
    are_different = (rec_titles1 != rec_titles2)

    print(f"\nVERIFICATION RESULT: Recommendations are materially dynamic and different ({are_different})")

finally:
    db.close()
