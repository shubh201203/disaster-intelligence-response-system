# DIRS Phase 3C — Remediation Baseline Documentation

**Date:** September 15, 2026  
**Status:** Baseline Established Before Remediation  
**Environment:** Windows 11, Python 3.11.9, Pytest 9.0.3, Vite/React, Playwright E2E  

---

## 1. Architecture Snapshot

```
User Query (Frontend Copilot Panel)
  → FastAPI Router (/api/v1/ai/rag/query)
  → RBAC Auth Dependency (get_current_user)
  → GroundingValidator.sanitize_query (Prompt-injection regex neutralization)
  → IncidentContextBuilder.build_structured_context (Live DB incident, GIS & AI state)
  → HybridSearchRetriever.retrieve (128-dim Word-Hashing Cosine + Lexical BM25 Overlap)
  → LLMProvider.generate_grounded_response (DIRS_GROUNDED_FALLBACK provider)
  → GroundingValidator.validate_and_structure_response (Threshold check top_similarity >= 0.35)
  → Persistence (RAGQueryLog DB record + WebSockets broadcast)
  → JSON Response (GroundedRAGResponse to UI)
```

---

## 2. Current Baseline Components

| Component | Current Implementation | Technical Reality |
| :--- | :--- | :--- |
| **Embedding Vectorization** | `LocalEmbeddingModel` | 128-bin unlearned word-hashing L2-normalized vector representation (`hash(word) % 128`). Does NOT use transformers or learned semantic weights. |
| **Retrieval Architecture** | `HybridSearchRetriever` | Weighted sum: $0.65 \times S_{cosine} + 0.35 \times S_{lexical}$ filtered by hazard domain (`CYCLONE`, `FLOOD`, `GENERAL`). |
| **Knowledge Base Sources** | `RAGService.seed_authoritative_knowledge_base` | Curated guideline summary markdowns (`CURATED_SUMMARY`) for NDMA, FEMA, and WHO. |
| **LLM Generation Provider** | `LLMProvider` | Deterministic grounded fallback provider (`DIRS_GROUNDED_FALLBACK`). External LLM generation requires `LLM_PROVIDER` and API key configuration. |
| **Grounding & Safety** | `GroundingValidator` | Similarity threshold $S_{max} \ge 0.35$ for grounded output; prompt-injection regex defense. |
| **Decision Recommendations**| `RecommendationEngine` & `Service` | Dynamic structured options requiring Government Officer approval (`ACCEPTED`, `REJECTED`, `MODIFIED`). |

---

## 3. Exact Empirical Baseline Benchmark Metrics

| Evaluation Dimension | Baseline Score | Percentage / Result | Details / Notes |
| :--- | :---: | :---: | :--- |
| **Backend Pytest Suite** | **85 / 85** | **100.0%** | All unit and integration tests passing cleanly. |
| **Phase 3C Pytest Suite** | **21 / 21** | **100.0%** | Dedicated vector, retriever, context, and recommendation tests passing. |
| **Frontend Production Build** | **PASSED** | **Exit Code 0** | Clean Vite + TypeScript build (`built in 4.55s`, 0 errors). |
| **Playwright E2E Suite** | **4 / 4 Specs** | **100.0%** | All 4 multi-role browser specs passing against live stack. |
| **18-Step Extended Demo** | **PASSED** | **Exit Code 0** | End-to-end Cyclone + Flood simulation script executed seamlessly. |
| **50-Case RAG Benchmark** | **38 / 50** | **76.0%** | 38 passed, 12 un-contextualized paraphrase queries refused due to feature-hashing score dilution below 0.35. |
| **Hallucination Refusal** | **10 / 10** | **100.0%** | 100% refusal accuracy on unsupported/fictional questions. |
| **Contextual Citation** | **10 / 10** | **100.0%** | 100% citation validity when incident context attached. |
| **Prompt Injection Defense** | **5 / 5** | **100.0%** | User injection, document injection, data exfiltration, citation manipulation, and RBAC defense. |

---

## 4. Known Baseline Limitations

1. **Feature-Hashing Paraphrase Weakness:** Queries using paraphrased natural language without exact keyword overlap spread L2 weights across 128 bins, dropping cosine similarity below $0.35$ and causing controlled refusal on valid questions.
2. **Curated Guidelines:** Seed documents are locally authored markdown summary guidelines rather than original full-text PDF publications.
3. **Fallback Testing Environment:** Testing was executed using the deterministic fallback provider (`DIRS_GROUNDED_FALLBACK`); external LLM integration requires explicit API key telemetry.
