# DIRS Phase 4 — Existing AI Implementation Audit Report

## Executive Summary

Before undertaking the Phase 4 real-world data upgrade, a complete forensic audit of all existing AI models, datasets, feature engineering pipelines, persisted model artifacts, and evaluation metrics was conducted across the DIRS codebase (`backend/app/ai/`, `scripts/`, `tests/backend/`).

The current system utilizes **synthetic dataset generators** for all 4 primary AI capabilities:
1. Incident Severity Prediction
2. Computer Vision Damage Assessment
3. Disaster Risk Prediction
4. Resource Demand Prediction

All 4 models pass their respective synthetic unit tests and evaluation pipelines with high accuracy (>98%), but their current performance reflects synthetic validation rather than empirical real-world field performance.

---

## Model-by-Model Detailed Forensic Audit

### 1. Incident Severity Prediction (`backend/app/ai/severity/`)

| Metric / Dimension | Implementation Detail |
| :--- | :--- |
| **Training Script** | `scripts/train_severity_model.py` / `backend/app/ai/severity/model.py` |
| **Dataset Generation** | `generate_synthetic_severity_dataset` (2,000 samples, 500/class) |
| **Data Realism** | Purely synthetic. Samples drawn from uniform/binomial random distributions per class. |
| **Features (6)** | `affected_population`, `injured_count`, `vulnerable_count`, `infrastructure_impact`, `disaster_type_code`, `distress_urgency_score` |
| **Target Variable** | 4-class categorical (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) |
| **Baseline Model** | `LogisticRegression` (Accuracy: 93.6%, Macro F1: 0.936) |
| **Selected Model** | `RandomForestClassifier` (n_estimators=100, max_depth=8) |
| **Persisted Artifact** | `backend/app/ai/models/severity_model.pkl` |
| **Current Metrics** | Synthetic Test Accuracy: **98.8%**, Macro F1: **0.988**, Critical Recall: **0.992** |
| **Explainability** | Linear factor attribution breakdown (`explain_severity_prediction`) |
| **Main Limitation** | Clean linear synthetic decision boundaries; lacks real-world noise, missing features, and actual incident reporting anomalies. |

---

### 2. Computer Vision Damage Assessment (`backend/app/ai/computer_vision/`)

| Metric / Dimension | Implementation Detail |
| :--- | :--- |
| **Training Script** | `scripts/evaluate_cv_model.py` / `backend/app/ai/computer_vision/model.py` |
| **Dataset Generation** | `generate_synthetic_cv_dataset` (1,000 samples, 200/class) |
| **Data Realism** | Purely synthetic visual feature distribution vectors. No actual images used in model training. |
| **Features (6)** | Classical PIL image features: `edge_density`, `entropy`, `color_var`, `darkness`, `asymmetry`, `roughness` |
| **Target Variable** | 5-class damage severity (`NO_DAMAGE`, `LOW_DAMAGE`, `MODERATE_DAMAGE`, `SEVERE_DAMAGE`, `DESTROYED`) |
| **Baseline Model** | `LogisticRegression` (Accuracy: 95.2%, Macro F1: 0.952) |
| **Selected Model** | `RandomForestClassifier` (n_estimators=100, max_depth=8) |
| **Persisted Artifact** | `backend/app/ai/models/cv_damage_model.pkl` |
| **Current Metrics** | Synthetic Test Accuracy: **99.2%**, Macro F1: **0.992**, Destroyed Recall: **0.990** |
| **Explainability** | Synthetic 4x4 spatial saliency heatmap derived from sub-region pixel variance |
| **Main Limitation** | **Not a deep learning computer vision model.** Features are scalar statistics; cannot learn spatial building patterns, structural collapses, or aerial spatial relationships. |

---

### 3. Disaster Risk Prediction (`backend/app/ai/risk_prediction/`)

| Metric / Dimension | Implementation Detail |
| :--- | :--- |
| **Training Script** | `scripts/evaluate_risk_model.py` / `backend/app/ai/risk_prediction/model.py` |
| **Dataset Generation** | `generate_synthetic_risk_dataset` (2,000 samples, 500/class) |
| **Data Realism** | Synthetic uniform ranges for meteorological and geospatial parameters. |
| **Features (11)** | `temperature`, `rainfall_accumulated_mm`, `wind_speed_kmh`, `relative_humidity`, `barometric_pressure_hpa`, `water_body_level_m`, `historical_disaster_frequency`, `population_density_exp`, `elevation_m`, `infrastructure_proximity_m`, `disaster_type_code` |
| **Target Variable** | 4-class risk severity (`LOW`, `MODERATE`, `HIGH`, `EXTREME`) |
| **Baseline Model** | `LogisticRegression` (Accuracy: 96.4%, Macro F1: 0.964) |
| **Selected Model** | `RandomForestClassifier` (n_estimators=100, max_depth=8) |
| **Persisted Artifact** | `backend/app/ai/models/risk_model.pkl` |
| **Current Metrics** | Synthetic Test Accuracy: **99.4%**, Macro F1: **0.994**, Extreme Recall: **0.995** |
| **Explainability** | Environmental contributor attribution scoring |
| **Main Limitation** | Synthetic independent feature generation ignores true thermodynamic correlations (e.g. pressure drop vs wind speed correlation in tropical cyclones). |

---

### 4. Resource Demand Prediction (`backend/app/ai/resource_demand/`)

| Metric / Dimension | Implementation Detail |
| :--- | :--- |
| **Training Script** | `scripts/evaluate_resource_model.py` / `backend/app/ai/resource_demand/model.py` |
| **Dataset Generation** | `generate_synthetic_resource_demand_dataset` (2,000 samples) |
| **Data Realism** | Synthetic linear mathematical formulas with added Gaussian noise. |
| **Features (6)** | `affected_population`, `injured_count`, `vulnerable_count`, `infrastructure_impact`, `severity_code`, `disaster_type_code` |
| **Target Variables (5)** | `water_packs`, `food_packets`, `medical_kits`, `shelter_beds`, `rescue_personnel` |
| **Baseline Model** | Multi-output `Ridge` Regression (Overall R²: 0.998, MAE: 2.34) |
| **Selected Model** | Multi-output `RandomForestRegressor` (n_estimators=100, max_depth=10) |
| **Persisted Artifact** | `backend/app/ai/models/resource_demand_models.pkl` |
| **Current Metrics** | Overall R²: **0.999**, Overall MAE: **2.12** |
| **Explainability** | Resource allocation breakdown and shortfall alert generation |
| **Main Limitation** | Models formulaic rules directly; true emergency supply logistics vary based on regional inventory and accessibility constraints. |

---

## Comprehensive Existing Model Comparison Matrix

| Model | Current Data | Synthetic? | Real? | Features | Target | Model Architecture | Current Metrics | Main Limitation |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- | :--- |
| **Incident Severity** | `generate_synthetic_severity_dataset` | YES | NO | 6 tabular metrics | Severity (`LOW` to `CRITICAL`) | `RandomForestClassifier` (depth 8) | Acc: 98.8%, F1: 0.988 | Clean linear synthetic boundaries; lacks real incident noise. |
| **Damage Assessment** | `generate_synthetic_cv_dataset` | YES | NO | 6 scalar PIL features | Damage (`NO_DAMAGE` to `DESTROYED`) | `RandomForestClassifier` (depth 8) | Acc: 99.2%, F1: 0.992 | Classical feature extraction; NOT deep learning CV. |
| **Risk Prediction** | `generate_synthetic_risk_dataset` | YES | NO | 11 weather/geo features | Risk Level (`LOW` to `EXTREME`) | `RandomForestClassifier` (depth 8) | Acc: 99.4%, F1: 0.994 | Lacks physical thermodynamic weather correlations. |
| **Resource Demand** | `generate_synthetic_resource_demand_dataset` | YES | NO | 6 incident metrics | 5 supply quantities | Multi-output `RandomForestRegressor` | R²: 0.999, MAE: 2.12 | Learns formulaic rules; real deployment logs are absent. |

---

## Key Technical Takeaways for Phase 4

1. **CV Damage Model:** Requires the largest architectural evolution — transitioning from scalar feature Random Forest to a real image classification model (e.g. transfer learning / CNN / ResNet baseline) trained on real disaster imagery (e.g., xBD / CrisisMMD).
2. **Disaster Risk Model:** Can be significantly improved by replacing independent uniform feature generation with real historical daily meteorological observations (NOAA GHCN / IMD weather data).
3. **Incident Severity Model:** Can be upgraded using real emergency incident logs (OpenFEMA / CrisisNLP disaster reports).
4. **Resource Demand Model:** Real granular micro-incident supply deployment logs are not available in public open datasets. Real data upgrade is **NOT JUSTIFIED**; instead, synthetic generation will be calibrated against **Sphere International Humanitarian Emergency Standards** and explicitly labeled as calibrated synthetic.
