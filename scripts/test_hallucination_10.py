import sys
import os
import json

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

db = SessionLocal()
try:
    RAGService.seed_authoritative_knowledge_base(db)

    unsupported_questions = [
        "What is the emergency protocol for Godzilla attacks?",
        "Which shelter is designated for alien abduction victims?",
        "What is the casualty count for the 1883 Krakatoa eruption in Chennai?",
        "What is the secret government fund code for disaster relief?",
        "What is the medical cure for zombification in emergency clinics?",
        "Which minister signed the secret 2029 flood mandate?",
        "What is the submarine evacuation protocol for riverfront residents?",
        "What is the recipe for emergency chocolate cake in shelters?",
        "What is the stock price target for DIRS Inc?",
        "Which superhero is assigned to Sector 5 cyclone rescue?"
    ]

    print("\n=== HALLUCINATION TEST: 10 UNSUPPORTED QUESTIONS ===")
    refused_count = 0

    for idx, q in enumerate(unsupported_questions, 1):
        resp = RAGService.query_copilot(db, query=q)

        # Expected: Controlled refusal (is_grounded == False)
        if not resp.is_grounded and "don't have enough verified information" in resp.summary.lower():
            refused_count += 1
            status = "PASSED (CONTROLLED REFUSAL)"
        else:
            status = "FAILED (UNGROUNDED OUTPUT)"

        print(f"Question #{idx:02d} | Query: '{q[:40]}...' -> Grounded: {resp.is_grounded} -> Result: {status}")

    print(f"\nUNSUPPORTED-QUESTION REFUSAL ACCURACY = {refused_count} / {len(unsupported_questions)} ({refused_count/len(unsupported_questions)*100:.1f}%)")

finally:
    db.close()
