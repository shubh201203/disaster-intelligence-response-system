import sys
import os
import time
import numpy as np
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

from app.database import SessionLocal
from app.models.incident import Incident
from app.ai.rag.service import RAGService
from app.ai.rag.embeddings.model import EmbeddingProvider
from app.ai.rag.retrieval.hybrid_search import HybridSearchRetriever
from app.ai.rag.context.context_builder import IncidentContextBuilder
from app.ai.rag.generation.llm_provider import LLMProvider

db = SessionLocal()
try:
    RAGService.seed_authoritative_knowledge_base(db)

    inc = Incident(
        incident_code=f"INC-PERF-{uuid.uuid4().hex[:4]}",
        title="Category 4 Cyclone Vardah Performance Measurement",
        disaster_type="CYCLONE",
        description="Storm surge and flooding telemetry",
        latitude=13.0827,
        longitude=80.2707,
        people_affected=250,
        injuries=15,
        vulnerable_count=30
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    queries = [
        "What pre-evacuation alert distance is mandated for Category 3 cyclones?",
        "What minimum water volume per person per day is required in cyclone emergency shelters?",
        "At what floodwater depth should motorboat rescue teams be deployed?",
        "What minimum quantity of water purification tablets is mandated for 500 evacuees?",
        "What algorithm is mandated for disaster field medical triage?",
        "What medical supplies must be carried by mobile disaster field clinics?",
        "When should ground rescue vehicle movement be suspended during a cyclone?",
        "What equipment is required to clear fallen trees after cyclone landfall?",
        "How frequently must water level gauges be monitored during flash floods?",
        "How are casualties categorized under the START triage system?",
        "What structural features are required for cyclone evacuation shelters?",
        "What is the pre-positioning protocol for severe flood surges?",
        "Summarize situation and recommended actions for trapped rooftop flood victims.",
        "Why is medical triage prioritized for severe flood reports with injuries?",
        "What resources are forecasted for an incident affecting 300 citizens?",
        "How are inventory shortages identified between predicted demand and NGO stock?",
        "Which shelter is recommended for flood evacuees near sector 5?",
        "What is the rationale for pre-positioning mobile clinics during severe hazards?",
        "Show authoritative citations for cyclone shelter food ration requirements.",
        "What official source governs field medical triage procedures?"
    ]

    embed_times = []
    retrieval_times = []
    context_times = []
    generation_times = []
    total_times = []

    print("\n=== LATENCY TELEMETRY BENCHMARK (20 QUERIES) ===")

    for idx, q in enumerate(queries, 1):
        t0 = time.perf_counter()

        # 1. Embedding Latency
        t_emb_start = time.perf_counter()
        q_vec = EmbeddingProvider.encode(q)
        t_emb = (time.perf_counter() - t_emb_start) * 1000.0
        embed_times.append(t_emb)

        # 2. Context Latency
        t_ctx_start = time.perf_counter()
        dirs_context = IncidentContextBuilder.build_structured_context(db, inc.id)
        t_ctx = (time.perf_counter() - t_ctx_start) * 1000.0
        context_times.append(t_ctx)

        # 3. Hybrid Retrieval Latency
        t_ret_start = time.perf_counter()
        retrieved = HybridSearchRetriever.retrieve(db, query=q, disaster_type="CYCLONE", top_k=4)
        t_ret = (time.perf_counter() - t_ret_start) * 1000.0
        retrieval_times.append(t_ret)

        # 4. Generation / Fallback Latency
        t_gen_start = time.perf_counter()
        provider = LLMProvider()
        resp = provider.generate_grounded_response(q, "GENERAL_COPILOT", retrieved, dirs_context)
        t_gen = (time.perf_counter() - t_gen_start) * 1000.0
        generation_times.append(t_gen)

        t_total = (time.perf_counter() - t0) * 1000.0
        total_times.append(t_total)

    def stats(arr):
        return np.mean(arr), np.median(arr), np.percentile(arr, 95)

    print("\n--- LATENCY BREAKDOWN SUMMARY (ms) ---")
    print(f" * Embedding Latency          -> Mean: {stats(embed_times)[0]:.2f} ms | Median: {stats(embed_times)[1]:.2f} ms | P95: {stats(embed_times)[2]:.2f} ms")
    print(f" * Context Assembly Latency   -> Mean: {stats(context_times)[0]:.2f} ms | Median: {stats(context_times)[1]:.2f} ms | P95: {stats(context_times)[2]:.2f} ms")
    print(f" * Hybrid Retrieval Latency   -> Mean: {stats(retrieval_times)[0]:.2f} ms | Median: {stats(retrieval_times)[1]:.2f} ms | P95: {stats(retrieval_times)[2]:.2f} ms")
    print(f" * Fallback Generation Latency -> Mean: {stats(generation_times)[0]:.2f} ms | Median: {stats(generation_times)[1]:.2f} ms | P95: {stats(generation_times)[2]:.2f} ms")
    print(f" * TOTAL RESPONSE LATENCY      -> Mean: {stats(total_times)[0]:.2f} ms | Median: {stats(total_times)[1]:.2f} ms | P95: {stats(total_times)[2]:.2f} ms")

finally:
    db.close()
