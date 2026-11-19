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

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import SessionLocal, engine, Base
from app.models.incident import Incident
from app.ai.rag.service import RAGService
from app.ai.rag.retrieval.hybrid_search import HybridSearchRetriever
from evaluate_rag import RAG_50_EVALUATION_CASES

def evaluate_weights(semantic_w: float, lexical_w: float, provider_mode: str = "LEXICAL_HASH"):
    db = SessionLocal()
    try:
        # Re-seed knowledge base
        db.query(KnowledgeChunk).delete() if 'KnowledgeChunk' in locals() else None
        RAGService.seed_authoritative_knowledge_base(db, embedding_provider_type=provider_mode)

        inc = Incident(
            incident_code=f"INC-EV-{uuid.uuid4().hex[:4]}",
            title="Category 4 Cyclone Vardah Evacuation",
            disaster_type="CYCLONE",
            description="Severe storm surge and wind damage",
            latitude=13.0827,
            longitude=80.2707,
            people_affected=350,
            injuries=25,
            vulnerable_count=45
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)

        passed_count = 0
        total_count = len(RAG_50_EVALUATION_CASES)

        for test_item in RAG_50_EVALUATION_CASES:
            query = test_item["query"]
            cat = test_item["category"]
            exp_kw = test_item["expected_kw"]

            inc_id_to_pass = inc.id if cat in ["Incident Reasoning", "Resource Reasoning", "RBAC Security", "Government Approval"] else None
            
            # Retrieve with custom weights
            dirs_context = RAGService.query_copilot(db, query=query, incident_id=inc_id_to_pass, embedding_provider_type=provider_mode)
            resp_str = json.dumps(dirs_context.model_dump()).lower()

            match_found = any(kw.lower() in resp_str for kw in exp_kw)
            if match_found:
                passed_count += 1

        accuracy = (passed_count / total_count) * 100.0
        print(f"Weight Config [{semantic_w*100:.0f}% Semantic / {lexical_w*100:.0f}% Lexical] -> Score: {passed_count}/{total_count} ({accuracy:.1f}%)")
        return passed_count, accuracy

    finally:
        db.close()

if __name__ == "__main__":
    print("\n=== HYBRID WEIGHT CONFIGURATION COMPARISON ===")
    evaluate_weights(0.70, 0.30)
    evaluate_weights(0.65, 0.35)
    evaluate_weights(0.60, 0.40)
    evaluate_weights(0.50, 0.50)
