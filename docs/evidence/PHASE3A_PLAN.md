# DIRS — Phase 3A Master Implementation Plan

**Scope:** Phase 3A — Core AI Intelligence Build  
**Status:** Approved for Implementation  
**Target:** Transform baseline DIRS platform into an AI-assisted, explainable, human-in-the-loop disaster decision-support system.

---

## 1. Architectural Overview & Modular Structure

DIRS retains its modular-monolith design. All AI capabilities will reside in `backend/app/ai/` with explicit abstraction boundaries, persistent models, explainability engines, and database auditability.

```text
backend/app/ai/
├── __init__.py
├── common/
│   ├── __init__.py
│   ├── schemas.py          # AI Request/Response Pydantic models
│   ├── confidence.py       # Confidence thresholds & human review triggers
│   └── model_registry.py   # Persistent model metadata registry
├── severity/
│   ├── __init__.py
│   ├── features.py        # Feature extraction & preprocessing
│   ├── dataset.py         # Deterministic synthetic dataset generator & loader
│   ├── model.py           # Training, evaluation & model persistence (RandomForest/Logistic)
│   ├── predictor.py       # Inference handler & confidence scorer
│   ├── explainer.py       # Feature contribution breakdown (Explainable AI)
│   └── service.py         # Severity service layer
├── priority/
│   ├── __init__.py
│   ├── features.py        # Priority input normalizers
│   ├── scoring.py         # 0-100 weighted priority math & factor contribution breakdown
│   ├── config.py          # Centralized PRIORITY_WEIGHTS configuration
│   └── service.py         # Priority engine service
├── duplicate_detection/
│   ├── __init__.py
│   ├── features.py        # Spatio-temporal & text feature extraction
│   ├── similarity.py      # Haversine distance, time delta, TF-IDF cosine & embedding similarity
│   ├── clustering.py      # Candidate grouping & evidence generation
│   └── service.py         # Duplicate detection service
```

---

## 2. Component Design & Specifications

### 2.1 Incident Severity Classifier (`ai/severity/`)
- **Classes:** `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- **Features Used:** `disaster_type`, `people_affected`, `injuries`, `vulnerable_count`, `has_infrastructure_damage`, `report_text_length`, `urgency_keyword_score`.
- **Dataset Strategy:** Deterministic, reproducible synthetic dataset generator (`scripts/train_severity_model.py` / `ai/severity/dataset.py`) containing 1,000+ realistic disaster cases across all 4 severity classes. Documented as "Development Synthetic Dataset".
- **Models Evaluated:** `LogisticRegression` vs `RandomForestClassifier`. Evaluated on accuracy, macro F1, and recall for `HIGH` & `CRITICAL`.
- **Model Persistence:** Saved to `backend/app/ai/models/severity_model.pkl` along with `severity_metadata.json`. Registered in `ModelRegistry`.
- **Explainability:** Feature impact contribution calculation (linear coefficients or Random Forest feature tree contribution weights) returning structured breakdown (`feature`, `impact`, `direction`).

### 2.2 Intelligent Priority Engine (`ai/priority/`)
- **Formula:** Normalized weighted sum scaled 0–100.
  - 0–25: `LOW`
  - 26–50: `MEDIUM`
  - 51–75: `HIGH`
  - 76–100: `CRITICAL`
- **Factors:** Severity weight (30%), Life Safety (injuries + vulnerable) (25%), Affected Population (15%), Infrastructure Damage (15%), Disaster Type Bonus (10%), Corroboration Count (5%).
- **Centralized Config:** `PRIORITY_WEIGHTS` dictionary in `ai/priority/config.py`.
- **Explainability:** Returns exact point contribution for every factor (e.g. `Severity: +30.0`, `Injuries/Vulnerable: +22.5`).

### 2.3 Duplicate & Related Incident Detection (`ai/duplicate_detection/`)
- **Multi-Criteria Similarity Score (0.0 to 1.0):**
  - Spatial Distance (Haversine km, max score within 500m)
  - Time Proximity (minutes delta, max score within 60 min)
  - Disaster Type match (Exact boolean match)
  - Textual & Semantic Similarity (TF-IDF vector cosine similarity + Keyword matching fallback)
- **Human-In-The-Loop Rule:** ABSOLUTELY NO AUTO-DELETION. AI returns candidate duplicates with similarity scores and evidence breakdown (`distance_m`, `time_difference_min`, `text_similarity`).
- **Government Actions:** `MERGE` (creates `IncidentCluster`), `KEEP_SEPARATE`, `DISMISS`.

---

## 3. Database Schema & Persistent Models

Create `AIPrediction` model in `backend/app/models/ai.py` and register in Alembic migration:

```python
class AIPrediction(Base):
    __tablename__ = "ai_predictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(String(50), nullable=False) # Incident
    entity_id = Column(String(36), nullable=False, index=True)
    prediction_type = Column(String(50), nullable=False) # SEVERITY, PRIORITY, DUPLICATE
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    prediction = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    requires_human_review = Column(Boolean, default=False)
    explanation = Column(JSON, default=dict)
    input_snapshot = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

---

## 4. API Endpoints (`/api/v1/ai/`)

1. `POST /api/v1/ai/incidents/{incident_id}/severity` — Predict severity, score confidence, & return explainability breakdown.
2. `POST /api/v1/ai/incidents/{incident_id}/priority` — Compute explainable 0-100 priority score & factor breakdown.
3. `POST /api/v1/ai/incidents/{incident_id}/duplicates` — Detect spatial-temporal-text duplicate candidates with evidence.
4. `GET /api/v1/ai/models` — List registered AI models and evaluation metadata.
5. `POST /api/v1/ai/incidents/{incident_id}/analyze` — Full pipeline trigger (Severity + Priority + Duplicates) with WebSocket event broadcasts (`AI_SEVERITY_UPDATED`, `AI_PRIORITY_UPDATED`, `DUPLICATE_DETECTED`).

---

## 5. UI & Command Center Enhancements

- **`AIInsightCard` / `ConfidenceBadge`:** Visual indicator displaying predicted severity, confidence %, and `REQUIRES HUMAN REVIEW` warning if confidence < 70%.
- **`ExplanationPanel`:** Interactive modal/drawer showing top contributing factors (e.g. `+25 Affected Population`, `+20 Injured Victims`).
- **`DuplicateSuggestion`:** Duplicate candidate list with distance, time, and text similarity evidence, offering `Merge`, `Keep Separate`, or `Dismiss` buttons.

---

## 6. Verification & Test Plan

1. **AI Unit Tests (`tests/ai/`):**
   - Severity classifier predictions, confidence scoring, low-confidence flagging, explainability ordering.
   - Priority engine bounds (0-100), weight configuration, deterministic outputs.
   - Duplicate detection thresholds, distance math, text similarity, merge integration.
   - RBAC security checks.
2. **Model Evaluation Script:** `scripts/evaluate_severity_model.py` generating actual confusion matrix, accuracy, precision, recall, and F1.
3. **Regression Testing:**
   - `python -m pytest tests/backend/ -v` (37/37 existing tests + new AI tests $\rightarrow$ 50+ total passing)
   - `npm run build`
   - `npx playwright test`
   - `python scripts/run_demo_scenario.py`
