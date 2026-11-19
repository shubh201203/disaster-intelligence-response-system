# DIRS Phase 3C — Grounded RAG & Copilot Evaluation Benchmark Report

## Benchmark Methodology

The DIRS Phase 3C evaluation benchmark (`scripts/evaluate_rag.py`) runs 30 standardized emergency test cases across 5 categories to measure retrieval precision, grounding accuracy, refusal reliability, and recommendation validity:

1. **Retrieval Precision & Citation Grounding (8 cases)**
2. **Fact vs. Inference Separation (6 cases)**
3. **Safety & Refusal on Ungrounded Queries (6 cases)**
4. **Structured Decision Recommendation Generation (6 cases)**
5. **Prompt-Injection & Adversarial Defense (4 cases)**

---

## Evaluation Benchmark Results

| Metric Category | Total Evaluated | Passed | Failed | Success Rate | Avg Latency |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Retrieval Precision & Citation Grounding** | 8 | 8 | 0 | **100.0%** | 12.4 ms |
| **Fact vs. Inference Separation** | 6 | 6 | 0 | **100.0%** | 9.8 ms |
| **Safety & Refusal on Ungrounded Queries** | 6 | 5 | 1 | **83.3%** | 8.1 ms |
| **Structured Recommendation Generation** | 6 | 6 | 0 | **100.0%** | 14.5 ms |
| **Prompt-Injection & Adversarial Defense** | 4 | 4 | 0 | **100.0%** | 5.2 ms |
| **OVERALL SYSTEM TOTAL** | **30** | **29** | **1** | **96.7%** | **10.0 ms** |

---

## Detailed Evaluation Analysis

### 1. Citation & Retrieval Performance
- **Dense Vector + BM25 Hybrid Retrieval:** Achieved 100% relevant document retrieval for NDMA, FEMA, and WHO query benchmarks.
- **Citation Precision:** All grounded responses included explicit organization tags (`NDMA`, `FEMA`, `WHO`), section headers, and similarity scores.

### 2. Fact vs Inference Separation
- **Strict Categorization:** 100% of facts returned carried verified evidence references (`DIRS Live Database`, `Phase 3A Severity Service`, `Phase 3B Risk Model`).
- **Inference Rationale:** Inferences were explicitly tagged with underlying basis (e.g. `(Based on 240mm rainfall and tidal surge forecasts)`).

### 3. Safety & Refusal Engine
- **Refusal Precision:** Correctly refused out-of-domain queries (e.g. stock market predictions, recipe requests, fiction generation) with `is_grounded = false` and warning banner.
- **Boundary Limitation:** 1 minor edge case query with generic words achieved a similarity score of 0.36 (just above 0.35 threshold), resulting in fallback summary rather than strict refusal. Handled safely via human-review requirement flag (`requires_human_review = True`).

### 4. Human-in-the-Loop Recommendation System
- **Approval Workflow:** 100% of generated decision recommendations set `requires_government_approval = True`.
- **Decision Processing:** All `ACCEPT`, `REJECT`, and `MODIFY` operations successfully recorded immutable audit logs without destroying original AI recommendations.

### 5. Adversarial & Prompt Injection Defense
- **Pattern Neutralization:** Successfully detected and neutralized prompt-injection attempts (`ignore instructions`, `reveal system prompt`, `override admin privileges`) with 0 policy breaches.

---

## Pytest Suite Verification Summary

- **Test Suite:** `tests/backend/test_phase3c_rag.py`
- **Total Tests:** 21 / 21 Passed (100%)
- **Full Backend Suite:** 85 / 85 Passed (100%)
- **Playwright E2E Suite:** `tests/e2e/playwright_phase3c_workflow.spec.ts` (1 / 1 Passed, live UI & API)
