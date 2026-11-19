import sys
import os

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
from app.ai.rag.service import RAGService
from app.ai.rag.retrieval.hybrid_search import HybridSearchRetriever

db = SessionLocal()
try:
    RAGService.seed_authoritative_knowledge_base(db)

    cases = [
        ("Case A (Exact Terminology)", "National Cyclone Risk Mitigation Framework Pre-Evacuation Protocol", "CYCLONE"),
        ("Case B (Paraphrase)", "What actions should authorities consider when people are trapped by rapidly rising floodwater?", "FLOOD"),
        ("Case C (Unrelated Content)", "What is the exact recipe for chocolate cake?", None),
        ("Case D (Cross-Disaster)", "What cyclone wind speed limits apply to flood rescue boats?", "CYCLONE"),
        ("Case E (Insufficient Evidence)", "What is the secret nuclear launch code for government defense?", None)
    ]

    print("\n=== RETRIEVAL QUALITY AUDIT: CASES A-E ===")
    for name, q, dtype in cases:
        res = HybridSearchRetriever.retrieve(db, query=q, disaster_type=dtype, top_k=3)
        top_score = res[0]["similarity_score"] if res else 0.0
        top_title = res[0]["title"] if res else "None"
        top_org = res[0]["organization"] if res else "None"
        copilot_res = RAGService.query_copilot(db, query=q)
        print(f"\n[{name}]")
        print(f"  Query: '{q}'")
        print(f"  Top Similarity Score: {top_score:.4f}")
        print(f"  Top Document: [{top_org}] {top_title}")
        print(f"  Is Grounded: {copilot_res.is_grounded} | Provider: {copilot_res.provider}")
        print(f"  Summary: '{copilot_res.summary[:100]}...'")

finally:
    db.close()
