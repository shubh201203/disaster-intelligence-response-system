# DIRS — Testing & Verification Strategy Specification

Last Updated: 2026-09-15 (Phase 3C Grounded RAG & Copilot Approved & Fully Verified)

This document specifies the verification strategy, test suites, and empirical benchmarks for DIRS.

---

## 1. Test Architecture Summary

| Test Layer | Framework | Scope | Location | Status | Passed |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Backend Unit & Integration** | Pytest | API Endpoints, Services, AI Models, DB ORM | [`tests/backend/`](file:///C:/Users/shubh/Downloads/DIRS/tests/backend/) | **PASSED** | 85 / 85 (100%) |
| **Phase 3C RAG Pytest Suite** | Pytest | Vector Indexing, Hybrid Search, Grounding, Recommendations | [`tests/backend/test_phase3c_rag.py`](file:///C:/Users/shubh/Downloads/DIRS/tests/backend/test_phase3c_rag.py) | **PASSED** | 21 / 21 (100%) |
| **End-to-End Multi-Role Workflow** | Playwright | Live UI + API End-to-End Multi-Role Workflows | [`tests/e2e/`](file:///C:/Users/shubh/Downloads/DIRS/tests/e2e/) | **PASSED** | 4 / 4 specs (100%) |
| **RAG Evaluation Benchmark** | Python Script | 30 Emergency Query Benchmark Cases | [`scripts/evaluate_rag.py`](file:///C:/Users/shubh/Downloads/DIRS/scripts/evaluate_rag.py) | **PASSED** | 29 / 30 (96.7%) |
| **Reproducible Scenario Simulation** | Python Script | 18-step Cyclone + Flood Lifecycle | [`scripts/run_demo_scenario.py`](file:///C:/Users/shubh/Downloads/DIRS/scripts/run_demo_scenario.py) | **PASSED** | Exit Code 0 |

---

## 2. Test Execution Commands

### 2.1 Backend Pytest Suite (85 Tests)
```powershell
$env:DATABASE_URL="sqlite:///C:/Users/shubh/Downloads/DIRS/dirs_dev.db"
python -m pytest tests/backend/ -v
```

### 2.2 Phase 3C Dedicated RAG Pytest Suite (21 Tests)
```powershell
$env:DATABASE_URL="sqlite:///C:/Users/shubh/Downloads/DIRS/dirs_dev.db"
python -m pytest tests/backend/test_phase3c_rag.py -v
```

### 2.3 RAG Evaluation Benchmark Script (30 Cases)
```powershell
python scripts/evaluate_rag.py
```

### 2.4 Playwright E2E Suite (4 Specs)
```powershell
npx playwright test tests/e2e/
```

### 2.5 18-Step Scenario Simulation
```powershell
python scripts/run_demo_scenario.py
```
