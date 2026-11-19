# DIRS Phase 3A — Core AI Intelligence Architecture & Model Specification

## 1. Executive Overview

Phase 3A transforms DIRS into an AI-assisted, human-in-the-loop disaster decision-support platform. The AI intelligence layer consists of four production-ready, explainable modules operating within a modular-monolith architecture:

1. **Incident Severity Classifier (`app/ai/severity/`)**
   - **Model:** Logistic Regression & Random Forest Classifier (persisted `severity_model.pkl`)
   - **Outputs:** Severity Class (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), Confidence Score (0-100%), Human Review Flag (`confidence < 70%`).
   - **Dataset:** Reproducible synthetic disaster dataset (1,500 samples) generated via `app/ai/severity/dataset.py`.
   - **Evaluation Metrics:** **93.78% Overall Accuracy**, **97.12% CRITICAL Class Recall**, **94.68% HIGH Class Recall**.

2. **Explainable AI Engine (`app/ai/severity/explainer.py`)**
   - Computes dynamic, feature-level contribution weights for every severity prediction.
   - Outputs structured, human-readable impact breakdowns (e.g. `+16.67 pts: High urgency distress keywords`, `+9.0 pts: Vulnerable demographics count`).

3. **Intelligent Priority Engine (`app/ai/priority/`)**
   - **Formula:** Transparent, normalized 0–100 weighted priority score.
   - **Configuration:** Centralized `PRIORITY_WEIGHTS` dictionary in `app/ai/priority/config.py` (Severity: 30%, Life Safety: 25%, Affected Population: 15%, Infrastructure: 15%, Disaster Type: 10%, Corroboration: 5%).
   - **Classifications:** `CRITICAL` (76-100), `HIGH` (51-75), `MEDIUM` (26-50), `LOW` (0-25).

4. **Spatio-Temporal & Text Duplicate Detector (`app/ai/duplicate_detection/`)**
   - **Algorithm:** Multi-criteria similarity scoring incorporating Haversine spatial distance (meters), temporal delta (minutes), exact disaster type matching, and TF-IDF cosine text similarity.
   - **Strict Human Oversight Rule:** **ABSOLUTELY NO AUTOMATIC DELETION**. Returns candidate reports with evidence breakdowns for Government Officer review (`MERGE`, `KEEP_SEPARATE`, `DISMISS`).

---

## 2. Package Structure (`backend/app/ai/`)

```text
backend/app/ai/
├── common/
│   ├── schemas.py          # Pydantic models for severity, priority, duplicates & model registry
│   ├── confidence.py       # Confidence thresholds & human review triggers
│   └── model_registry.py   # Persistent metadata registry for AI models
├── severity/
│   ├── features.py        # Feature extraction & text urgency scoring
│   ├── dataset.py         # Reproducible synthetic dataset generator
│   ├── model.py           # Training, model persistence & evaluation
│   ├── predictor.py       # Inference engine & confidence calculator
│   ├── explainer.py       # Explainable AI factor contribution calculator
│   └── service.py         # Severity service layer & DB persistence
├── priority/
│   ├── features.py        # Priority input normalization
│   ├── scoring.py         # Weighted 0-100 scoring & factor breakdown
│   ├── config.py          # Centralized PRIORITY_WEIGHTS configuration
│   └── service.py         # Priority engine service layer
└── duplicate_detection/
    ├── features.py        # Haversine distance & time difference utilities
    ├── similarity.py      # TF-IDF cosine similarity & multi-criteria scoring
    ├── clustering.py      # Candidate threshold filtering & evidence generation
    └── service.py         # Duplicate detection service layer
```

---

## 3. Persistent Data Model (`AIPrediction`)

All AI model inferences are logged to the `ai_predictions` database table for immutable auditability and decision explainability:

```python
class AIPrediction(Base):
    __tablename__ = "ai_predictions"

    id = Column(String(36), primary_key=True)
    entity_type = Column(String(50))         # "Incident"
    entity_id = Column(String(36))           # Incident UUID
    prediction_type = Column(String(50))     # "SEVERITY", "PRIORITY", "DUPLICATE"
    model_name = Column(String(100))
    model_version = Column(String(50))
    prediction = Column(String(100))         # e.g., "CRITICAL", "93.5"
    confidence = Column(Float)
    requires_human_review = Column(Boolean)
    explanation = Column(JSON)               # Explainable factors list
    input_snapshot = Column(JSON)            # Feature snapshot at prediction time
    created_at = Column(DateTime)
```

---

## 4. API Specification & WebSockets Integration

- `POST /api/v1/ai/incidents/{id}/severity` $\rightarrow$ Triggers severity prediction, logs `AIPrediction`, and broadcasts `AI_SEVERITY_UPDATED` WebSocket event.
- `POST /api/v1/ai/incidents/{id}/priority` $\rightarrow$ Triggers 0-100 priority engine, updates incident priority score, and broadcasts `AI_PRIORITY_UPDATED` WebSocket event.
- `POST /api/v1/ai/incidents/{id}/duplicates` $\rightarrow$ Evaluates spatio-temporal-text similarity and broadcasts `DUPLICATE_DETECTED` WebSocket event when candidates exist.
- `POST /api/v1/ai/incidents/{id}/analyze` $\rightarrow$ Executes full AI analysis pipeline (Severity + Priority + Duplicates).
- `GET /api/v1/ai/models` $\rightarrow$ Lists registered AI model metadata & performance metrics.

---

## 5. Human-in-the-Loop Emergency Safeguards

1. **Non-Blocking AI:** If an AI model fails or is offline, DIRS continues operating cleanly. Emergency operations are never blocked.
2. **Advisory Role:** AI predictions assist government administrators but **never** make irreversible automated decisions (no automated incident closing, rejecting, or report deletion).
3. **Low-Confidence Flagging:** Any prediction with a confidence score below 70.0% is flagged with `REQUIRES HUMAN REVIEW` in the Government Command Center UI.
