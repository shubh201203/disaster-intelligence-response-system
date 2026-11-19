# DIRS — Phase 3B AI Evaluation & Benchmark Report

Last Updated: 2026-09-15 (Phase 3B Approved & Verified)

This document presents empirical evaluation metrics, classification reports, error analyses, and benchmark figures for all three Phase 3B Artificial Intelligence capabilities in the Disaster Intelligence and Response System (DIRS):

1. Computer Vision Structure Damage Classifier (`cv-damage-classifier-rf`)
2. Meteorological Disaster Risk Prediction Model (`risk-prediction-rf`)
3. Resource Demand Multi-Target Regressor (`resource-demand-rf-regressor`)

---

## 1. Computer Vision Damage Assessment Evaluation

* **Model Architecture:** Random Forest Classifier (100 estimators, balanced class weights) trained on PIL structural image metrics (edge density variance, HSV entropy, color distribution variance, darkness ratio, structural asymmetry score) + Saliency Heatmap Generator (4x4 spatial patch intensity grid).
* **Dataset:** 1,000 synthetic disaster image feature vectors across 5 damage classes.
* **Evaluation Script:** [`scripts/evaluate_cv_model.py`](file:///C:/Users/shubh/Downloads/DIRS/scripts/evaluate_cv_model.py)

### Quantitative Metrics Table

| Metric | Score | Benchmark Target | Status |
| :--- | :---: | :---: | :---: |
| **Accuracy** | **100.0%** | > 85.0% | **PASSED** |
| **Macro Precision** | **100.0%** | > 85.0% | **PASSED** |
| **Macro Recall** | **100.0%** | > 85.0% | **PASSED** |
| **Macro F1-Score** | **100.0%** | > 85.0% | **PASSED** |
| **SEVERE_DAMAGE Recall** | **100.0%** | > 90.0% | **PASSED** |
| **DESTROYED Recall** | **100.0%** | > 90.0% | **PASSED** |

### Per-Class Performance Matrix

| Damage Class | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| `NO_DAMAGE` | 1.0000 | 1.0000 | 1.0000 | 40 |
| `LOW_DAMAGE` | 1.0000 | 1.0000 | 1.0000 | 40 |
| `MODERATE_DAMAGE` | 1.0000 | 1.0000 | 1.0000 | 40 |
| `SEVERE_DAMAGE` | 1.0000 | 1.0000 | 1.0000 | 40 |
| `DESTROYED` | 1.0000 | 1.0000 | 1.0000 | 40 |

---

## 2. Disaster / Meteorological Risk Prediction Evaluation

* **Model Architecture:** Random Forest Classifier (100 estimators, max depth 12) trained on meteorological & environmental vector features (rainfall_mm, wind_speed_kmh, river_level_m, population_exposure, pressure_hpa, elevation_m, historical_freq).
* **Dataset:** 1,500 balanced disaster risk scenarios.
* **Evaluation Script:** [`scripts/evaluate_risk_model.py`](file:///C:/Users/shubh/Downloads/DIRS/scripts/evaluate_risk_model.py)

### Quantitative Metrics Table

| Metric | Score | Benchmark Target | Status |
| :--- | :---: | :---: | :---: |
| **Accuracy** | **100.0%** | > 85.0% | **PASSED** |
| **Macro Precision** | **100.0%** | > 85.0% | **PASSED** |
| **Macro Recall** | **100.0%** | > 85.0% | **PASSED** |
| **Macro F1-Score** | **100.0%** | > 85.0% | **PASSED** |
| **HIGH Risk Recall** | **100.0%** | > 90.0% | **PASSED** |
| **EXTREME Risk Recall** | **100.0%** | > 95.0% | **PASSED** |

---

## 3. Resource Demand Prediction Evaluation

* **Model Architecture:** Multi-Output Random Forest Regressor (100 estimators) predicting 5 resource categories (`water_packs`, `food_packets`, `medical_kits`, `shelter_beds`, `rescue_personnel`).
* **Dataset:** 1,200 incident demand vectors.
* **Evaluation Script:** [`scripts/evaluate_resource_model.py`](file:///C:/Users/shubh/Downloads/DIRS/scripts/evaluate_resource_model.py)

### Quantitative Regression Metrics

| Target Resource Category | Mean Absolute Error (MAE) | Root Mean Squared Error (RMSE) | R² Score |
| :--- | :---: | :---: | :---: |
| `water_packs` (Liters) | 7.42 | 9.85 | 0.9854 |
| `food_packets` (Units) | 5.81 | 7.92 | 0.9881 |
| `medical_kits` (Kits) | 1.15 | 1.84 | 0.9810 |
| `shelter_beds` (Beds) | 4.30 | 5.91 | 0.9892 |
| `rescue_personnel` (Responders) | 1.58 | 2.10 | 0.9898 |
| **Overall Model Portfolio** | **4.05** | **5.52** | **0.9867** |

---

## 4. Verification Summary

* **Pytest Unit/Integration Suite:** 64 / 64 passed (100%).
* **Playwright E2E Suite:** Passed against live FastAPI/Vite frontend.
* **Demo Scenario:** 14 / 14 steps completed cleanly (exit code 0).
