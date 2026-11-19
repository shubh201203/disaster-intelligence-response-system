# DIRS — Phase 3B Technical Architecture & Design Specification

Last Updated: 2026-09-15 (Phase 3B Approved & Verified)

This document describes the technical architecture, data pipelines, schema design, model contracts, security controls, and WebSocket event specifications for Phase 3B AI capabilities in the Disaster Intelligence and Response System (DIRS).

---

## 1. System Overview & Module Integration

Phase 3B expands DIRS from Phase 3A explainable severity prediction into a full multi-modal AI disaster intelligence platform:

```
                          [ INCIDENT / SENSOR DATA ]
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
[ Computer Vision ]        [ Risk Prediction ]        [ Resource Demand ]
 - PIL Structural Metrics   - Meteorological Scenarios - 5-Category Forecast
 - RF Damage Classifier     - RF Risk Score (0-100)    - Stock Shortage Checks
 - 4x4 Saliency Grid        - 6 Contributing Factors   - 15% Error Bounds
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     ▼
                     [ Persistence & Audit Trail ]
                      - DB: CVDamageAssessment
                      - DB: RiskAssessment
                      - DB: ResourceDemandPrediction
                      - DB: AIPrediction (Immutable)
                                     │
                                     ▼
                     [ Human Officer Governance ]
                      - Confidence Threshold < 70%
                      - Human Review Flag
                      - Government Audit Override
                                     │
                                     ▼
                     [ Real-Time WebSockets Feed ]
                      - AI_CV_ANALYSIS_COMPLETED
                      - AI_RISK_UPDATED
                      - AI_RESOURCE_DEMAND_UPDATED
```

---

## 2. Database Schema & Data Models

Phase 3B introduces three main ORM models in [`backend/app/models/ai.py`](file:///C:/Users/shubh/Downloads/DIRS/backend/app/models/ai.py):

### 2.1 `CVDamageAssessment`
* `id` (UUID Primary Key)
* `incident_id` (Foreign Key -> `incidents.id`)
* `media_id` (Foreign Key -> `incident_media.id`)
* `damage_class` (String Enum: `NO_DAMAGE`, `LOW_DAMAGE`, `MODERATE_DAMAGE`, `SEVERE_DAMAGE`, `DESTROYED`)
* `confidence` (Float 0.0 to 100.0)
* `class_probabilities` (JSON Dict)
* `explanation_metadata` (JSON Dict: `saliency_heatmap_4x4`, `edge_density`, `entropy`)
* `requires_human_review` (Boolean, `True` if confidence < 70.0)
* `is_overridden` (Boolean, default `False`)
* `override_damage_class` (String, default `None`)
* `override_notes` (Text)
* `reviewer_id` (Foreign Key -> `users.id`)

### 2.2 `RiskAssessment`
* `id` (UUID Primary Key)
* `incident_id` (Foreign Key -> `incidents.id`)
* `geographic_scope` (String)
* `disaster_type` (String Enum: `FLOOD`, `CYCLONE`, `FIRE`, `LANDSLIDE`, `EARTHQUAKE`)
* `risk_score` (Float 0.0 to 100.0)
* `risk_level` (String Enum: `LOW`, `MODERATE`, `HIGH`, `EXTREME`)
* `confidence` (Float 0.0 to 100.0)
* `requires_human_review` (Boolean)
* `input_snapshot` (JSON Dict)
* `contributing_factors` (JSON Array of feature contribution objects)
* `is_overridden` (Boolean)
* `override_level` (String)

### 2.3 `ResourceDemandPrediction`
* `id` (UUID Primary Key)
* `incident_id` (Foreign Key -> `incidents.id`)
* `predictions` (JSON Dict: 5 resource categories with quantity, unit, lower/upper bounds)
* `overall_confidence` (Float)
* `requires_human_review` (Boolean)
* `contributing_features` (JSON Array of strings)
* `shortages_detected` (JSON Array of inventory shortage objects)
* `is_overridden` (Boolean)
* `override_demands` (JSON Dict)

---

## 3. WebSockets & Security Controls

* **WebSocket Events:**
  - `AI_CV_ANALYSIS_COMPLETED`
  - `AI_RISK_UPDATED`
  - `AI_RESOURCE_DEMAND_UPDATED`
* **RBAC Controls:**
  - `POST /api/v1/ai/incidents/{id}/vision`: CITIZEN (own incident), VOLUNTEER, GOVT
  - `POST /api/v1/ai/risk`: GOVT, VOLUNTEER
  - `POST /api/v1/ai/resource-demand`: GOVT, NGO
  - `POST /api/v1/ai/override`: **GOVT only** (strictly enforced via `RoleChecker(["GOVT"])`)
