# DIRS Phase 4 — Real-World AI Model & Dataset Upgrade Research & Implementation Plan

> **CapStone Scope Boundary:**  
> DIRS Phase 3C is COMPLETE, VERIFIED, AND FROZEN. Phase 4 focuses strictly on upgrading DIRS's existing 4 AI capabilities from synthetic data validation to scientifically defensible real-world disaster data training, evaluation, and integration.

---

## 1. Existing AI Architecture Summary

DIRS currently operates 4 core AI prediction engines:
- **Incident Severity Classifier:** Classifies incidents into `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` based on reported casualties, vulnerable population, infrastructure impact, and text urgency.
- **Damage / Computer Vision Assessment:** Classifies structural damage from uploaded incident images into `NO_DAMAGE`, `LOW_DAMAGE`, `MODERATE_DAMAGE`, `SEVERE_DAMAGE`, `DESTROYED`.
- **Disaster Risk Prediction:** Predicts environmental hazard risk (`LOW`, `MODERATE`, `HIGH`, `EXTREME`) based on meteorological parameters, water body levels, population density, and infrastructure proximity.
- **Resource Demand Prediction:** Multi-output regression predicting required quantities of `water_packs`, `food_packets`, `medical_kits`, `shelter_beds`, and `rescue_personnel`.

---

## 2. Current Synthetic Data Usage

All existing Phase 3A and 3B models were trained and validated on synthetic datasets generated at runtime (`n_samples` = 1,000 to 2,000 per model). While synthetic datasets verified system pipeline integration, API schemas, and UI rendering (producing synthetic accuracy metrics >98%), they lack real-world statistical distributions, sensor noise, atmospheric correlations, and complex visual spatial features.

---

## 3. Candidate Real-World Datasets

### Category A: Computer Vision & Building Damage Imagery
1. **xBD (xView2 Building Damage Assessment Dataset)**
   - **Source:** Defense Innovation Unit (DIU) / Carnegie Mellon University.
   - **Description:** High-resolution pre/post-disaster satellite & aerial RGB imagery across 19 global disaster events (earthquakes, floods, hurricanes, wildfires).
   - **Scale:** 850,000+ annotated building polygons.
   - **Classes:** 4 standardized visual damage labels (`no-damage`, `minor-damage`, `major-damage`, `destroyed`).
   - **License:** CC BY-NC 4.0.
   - **Suitability:** **HIGH**. Standard benchmark in disaster AI research.
2. **CrisisMMD / AIDER Disaster Image Datasets**
   - **Source:** Qatar Computing Research Institute (QCRI) / IEEE CVPR Workshops.
   - **Description:** Ground-level & UAV disaster images collected during real hurricane, flood, and earthquake response.
   - **Classes:** Ground damage, flooded roads, collapsed infrastructure.
   - **License:** CC BY 4.0.
   - **Suitability:** **HIGH** (Direct match for citizen ground-level photo uploads).

### Category B: Meteorological & Disaster Risk Records
1. **NOAA Severe Weather Data Inventory (SWDI) & Global Historical Climatology Network (GHCN)**
   - **Source:** NOAA National Centers for Environmental Information (NCEI).
   - **Description:** Multi-decade global daily station meteorological records (rainfall accumulation, wind velocity, atmospheric pressure, temperature, humidity).
   - **License:** Public Domain / Open US Government Work.
   - **Suitability:** **HIGH**. Provides physical thermodynamic weather distributions.
2. **IMD (India Meteorological Department) High-Resolution Daily Gridded Weather Records**
   - **Source:** IMD National Data Centre (NDC).
   - **Description:** Gridded daily rainfall and temperature observations across Indian disaster zones.
   - **License:** Open Government Data (OGD) License India.
   - **Suitability:** **HIGH** for regional monsoon & tropical cyclone risk calibration.

### Category C: Emergency Incidents & Resource Deployment
1. **OpenFEMA Disaster Declarations Summaries & Incident Logs**
   - **Source:** Federal Emergency Management Agency (FEMA) Data Portal.
   - **Description:** Tabular records of declared disaster incidents with affected population, casualty metrics, county location, and emergency declaration severity levels.
   - **License:** Public Domain (OpenFEMA).
   - **Suitability:** **HIGH** for tabular Incident Severity modeling.
2. **Granular Incident Resource Deployment Logs**
   - **Analysis:** Micro-level resource deployment logs (exact water packs and medical kits distributed per individual report) are **NOT** available in open public emergency management datasets.
   - **Suitability:** **INSUFFICIENT DATA**. Real-data replacement is **NOT JUSTIFIED**.

---

## 4. Dataset Quality Assessment Scorecard

| Candidate Dataset | Target Model | Real? | Label Quality | Size / Coverage | License | Leakage Risk | Integration Difficulty | Overall Score |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: |
| **xBD / CrisisMMD Imagery** | Damage Assessment | YES | `HIGH` | 850,000+ polygons / 10,000+ images | CC BY-NC 4.0 | `LOW` (Group split by event) | `MEDIUM` | **HIGH (SELECTED)** |
| **NOAA / IMD Climatology** | Risk Prediction | YES | `HIGH` | 50,000+ daily station records | Public Domain / OGD | `LOW` (Temporal split) | `LOW` | **HIGH (SELECTED)** |
| **OpenFEMA Incident Logs** | Severity Prediction | YES | `HIGH` | 60,000+ disaster incident records | Public Domain | `LOW` (Stratified split) | `LOW` | **HIGH (SELECTED)** |
| **Granular Supply Deployment** | Resource Demand | NO | `LOW` | N/A | N/A | `HIGH` | `HIGH` | **NOT JUSTIFIED** |

---

## 5. Dataset Licensing & Provenance Registry

All selected datasets adhere to open academic and public domain licenses:
- **xBD / CrisisMMD:** Open research license (CC BY-NC 4.0 / CC BY 4.0).
- **NOAA SWDI / GHCN:** Public Domain (US Federal Government Open Data).
- **OpenFEMA:** Public Domain (FEMA Open Data).
- **Sphere Humanitarian Standards:** International Open Standards (UN OCHA / Red Cross) used for Resource Demand calibration.

---

## 6. Recommended Dataset Selection & Model Mapping

```text
DIRS AI Engine               Selected Data Strategy                      Decision Status
-------------------         ----------------------------------------     ---------------
1. Severity Prediction   →  OpenFEMA + CrisisNLP Tabular Logs           SELECTED (Real)
2. Damage Assessment     →  xBD / CrisisMMD Disaster Damage Imagery      SELECTED (Real)
3. Risk Prediction       →  NOAA / IMD Historical Climatology Data       SELECTED (Real)
4. Resource Demand       →  Sphere Humanitarian Calibrated Baseline      CALIBRATED SYNTHETIC (Honest)
```

---

## 7. Train / Validation / Test Strategy

To prevent data leakage and ensure realistic operational evaluation:

1. **Computer Vision Damage Model:**
   - **Split Method:** `GroupKFold` split by **disaster event**.
   - Train on N disaster events; test on completely unseen disaster events (e.g. train on Hurricane Harvey, test on Hurricane Michael).
   - Rationale: Evaluates generalization to geographically unseen disaster scenes.

2. **Disaster Risk Model:**
   - **Split Method:** `Temporal Split`.
   - Train on historical observations (e.g., 2015–2022); validate/test on subsequent years (2023–2025).
   - Rationale: Prevents temporal leakage of future climate trends into training sets.

3. **Incident Severity Model:**
   - **Split Method:** `Stratified K-Fold` (70% Train, 15% Validation, 15% Test).
   - Stratified across severity classes to maintain balanced evaluation.

---

## 8. Data Leakage Audit Strategy

Automated checks will be integrated into dataset preprocessing:
- **Image Duplicate Audit:** Perceptual hashing (`imagehash` dhash/phash) to remove duplicate or near-duplicate aerial tiles crossing train/test splits.
- **Geospatial Grouping Audit:** Ensure imagery from the same spatial grid square is grouped entirely within either train or test.
- **Tabular Target Leakage:** Strip post-event operational response IDs and target-derived features prior to model ingestion.

---

## 9. Candidate Models & Baselines

```text
Task                     Baseline Model                   Candidate Models
-------------------      ----------------------------     --------------------------------------
1. Severity              Logistic Regression              Random Forest, XGBoost
2. Damage (CV)           Classical PIL Visual RF          Pretrained CNN / Transfer Learning (ResNet18/MobileNetV3)
3. Risk                  Logistic Regression              Random Forest, XGBoost
4. Resource Demand       Multi-output Ridge Baseline      Calibrated Multi-output Random Forest
```

---

## 10. Evaluation Metrics

- **Classification Models (Severity, Risk, CV Damage):**
  - Accuracy, Precision, Recall, Macro F1 Score.
  - **High-Risk Class Recall:** Safety-critical metric prioritizing recall for `CRITICAL` severity, `EXTREME` risk, and `DESTROYED` damage.
  - Confusion Matrix analysis.

- **Regression Model (Resource Demand):**
  - MAE (Mean Absolute Error), RMSE, R² Score per resource type.

---

## 11. Robustness Testing Plan

Models will be evaluated under real-world degradation perturbations:
- **Tabular Inputs (Severity & Risk):** Gaussian feature noise (10%–20%), missing feature imputation, extreme outlier values.
- **Image Inputs (Damage CV):** Brightness variations, Gaussian blur, compression artifacts, resolution downscaling.
- **Reported Metric:** `Clean Performance` vs `Perturbed Performance` degradation delta.

---

## 12. DIRS System Integration & Fallback Strategy

- **API Interface Preservation:** Existing API endpoints (`/api/ai/severity/predict`, `/api/ai/computer-vision/assess`, `/api/ai/risk/predict`, `/api/ai/resource-demand/predict`) will maintain their Pydantic request/response contracts.
- **Model Registry & Versioning:** Models will be versioned using `ModelRegistry` (`v1.0.0-synthetic` vs `v2.0.0-realworld`).
- **Human Oversight & Override:** Confidence scoring thresholds (<70% confidence triggers mandatory Human-in-the-Loop review) and immutable audit logging will remain strictly active.

---

## 13. Scope Boundaries (Items That Should NOT Be Built)

- **DO NOT** implement route optimization, vehicle routing, or OR-Tools.
- **DO NOT** implement volunteer dispatch algorithms or post-disaster analytics dashboards.
- **DO NOT** build a complex MLOps/Kubernetes infrastructure. Keep pipelines modular, Python script-driven, and locally reproducible.

---

## 14. Recommended Phase 4 Execution Sequence

1. **Step 1:** Complete forensic audit and research gate approval (CURRENT STEP).
2. **Step 2:** Construct reproducible data directory hierarchy (`data/raw`, `data/processed`, `data/metadata`).
3. **Step 3:** Implement dataset download/ingestion and automated preprocessing pipelines.
4. **Step 4:** Execute data quality and leakage audit scripts.
5. **Step 5:** Train baseline models (Logistic Regression / Classical RF).
6. **Step 6:** Train real-data candidate models (XGBoost, Transfer Learning CNN).
7. **Step 7:** Run evaluation, robustness perturbation, and synthetic-vs-real comparisons.
8. **Step 8:** Register validated real-world models in DIRS model registry.
9. **Step 9:** Execute full DIRS regression suite (Pytest 85/85, Phase 3C 21/21, Playwright 4/4, Demo 18/18).
10. **Step 10:** Publish final Phase 4 scientific research report.

---

## 15. Estimated Engineering Effort & Key Risks

- **Estimated Effort:** 3–4 targeted engineering sprints within the capstone boundary.
- **Key Risks:**
  - *Hardware Constraints:* Deep learning CV training on local CPU/GPU. *Mitigation:* Use lightweight backbones (MobileNetV3 / ResNet18) or pre-extracted feature embeddings.
  - *Dataset Download Size:* Satellite datasets can be multi-gigabyte. *Mitigation:* Ingest a curated, subsetted benchmark partition (e.g. 2,000–5,000 balanced disaster image tiles).

---

## PHASE 4 RESEARCH GATE

| Research Gate Dimension | Status / Verdict | Notes / Recommendation |
| :--- | :---: | :--- |
| **Severity Real Data** | `READY` | OpenFEMA & CrisisNLP tabular incident datasets identified and mapped. |
| **CV Real Data** | `READY` | xBD / CrisisMMD building damage imagery benchmark identified and structured. |
| **Risk Real Data** | `READY` | NOAA GHCN / IMD historical meteorological time series datasets mapped. |
| **Resource Real Data** | `PARTIAL` | Granular micro-incident logs unavailable; Sphere Humanitarian Standards calibration approved. |
| **Recommended Datasets** | `OpenFEMA`, `xBD / CrisisMMD`, `NOAA GHCN` | High-quality open datasets adhering to public/academic licenses. |
| **Recommended Models** | `XGBoost`, `ResNet18 / MobileNetV3`, `Random Forest` | Lightweight, defensible models with classical baselines. |
| **Major Risks** | Image dataset download size & CV training latency | Mitigated via standardized benchmark subset partition. |
| **Estimated Effort** | 3–4 Sprints | Fits comfortably within capstone scope. |
| **READY FOR IMPLEMENTATION** | **YES** | Pending user plan review. |

---

## STOP HERE
*Awaiting explicit user review and approval before proceeding to dataset ingestion and model training.*
