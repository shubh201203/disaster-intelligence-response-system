import sys
import os
import json
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
from app.models.rag import KnowledgeDocument, KnowledgeChunk
from app.ai.rag.service import RAGService
from app.ai.rag.retrieval.hybrid_search import HybridSearchRetriever

db = SessionLocal()
try:
    RAGService.seed_authoritative_knowledge_base(db)

    # Seed test incident
    inc_cyc = Incident(
        incident_code=f"INC-CY-{uuid.uuid4().hex[:4]}",
        title="Category 4 Cyclone Vardah",
        disaster_type="CYCLONE",
        description="Storm surge and rooftop flooding",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=150,
        injuries=5,
        vulnerable_count=10
    )
    inc_fld = Incident(
        incident_code=f"INC-FL-{uuid.uuid4().hex[:4]}",
        title="Flash Flood Inundation",
        disaster_type="FLOOD",
        description="Inundation overflowing houses",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=200,
        injuries=12,
        vulnerable_count=20
    )
    db.add_all([inc_cyc, inc_fld])
    db.commit()
    db.refresh(inc_cyc)
    db.refresh(inc_fld)

    test_cases = [
        ("NDMA Cyclone Pre-Evacuation Alert Protocol", inc_cyc.id, "CYCLONE"),
        ("Cyclone Shelter Water Volume Rations NDMA", inc_cyc.id, "CYCLONE"),
        ("FEMA SOP Flood Inundation Motorboat Rescue", inc_fld.id, "FLOOD"),
        ("FEMA Water Purification Tablets Flood Shelter", inc_fld.id, "FLOOD"),
        ("WHO Emergency Medical Field Triage Guidelines", inc_cyc.id, "GENERAL"),
        ("WHO Mobile Field Clinic Trauma Dressing Supplies", inc_fld.id, "GENERAL"),
        ("Cyclone Wind Velocity Speed Limit Suspend Movement", inc_cyc.id, "CYCLONE"),
        ("Flood Water Level Gauges Hourly Monitoring", inc_fld.id, "FLOOD"),
        ("NDMA Cyclone Emergency Shelter Reinforced Roofing Power", inc_cyc.id, "CYCLONE"),
        ("FEMA Flood Shelter Hygiene Protocols Sanitation", inc_fld.id, "FLOOD")
    ]

    print("\n=== CITATION FORENSICS WITH INCIDENT CONTEXT (10 CASES) ===")
    correct_count = 0

    for idx, (q, inc_id, dtype) in enumerate(test_cases, 1):
        resp = RAGService.query_copilot(db, query=q, incident_id=inc_id)

        has_citations = len(resp.citations) > 0
        all_valid = True

        for cite in resp.citations:
            doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == cite.doc_id).first()
            if not doc:
                all_valid = False
                break
            if doc.source_organization != cite.organization:
                all_valid = False
                break
            chunks = db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc.id).all()
            if not chunks:
                all_valid = False
                break

        if has_citations and all_valid:
            correct_count += 1
            status = "VALIDATED"
        else:
            status = "INVALID / NO CITATIONS"

        top_cite_str = f"[{resp.citations[0].organization}] {resp.citations[0].title[:35]}..." if resp.citations else "No Citation"
        print(f"Answer #{idx:02d} | Query: '{q[:40]}...' -> Citation: {top_cite_str} -> Result: {status}")

    print(f"\nCONTEXTUAL CITATION CORRECTNESS SCORE = {correct_count} / {len(test_cases)} ({correct_count/len(test_cases)*100:.1f}%)")

finally:
    db.close()
