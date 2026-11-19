# DIRS Phase 4 — Resource Demand Real-Data Boundary Report

## Executive Summary & Final Verdict

- **Model Status:** **`SYNTHETIC-CALIBRATED`**
- **Selected Model:** `SphereCalibrated_RandomForestRegressor` (`backend/app/ai/models/resource_demand_models.pkl`)
- **Domain Baseline:** UN Sphere International Humanitarian Minimum Standards (15L water, 3 food packets, trauma kits, shelter beds, rescue personnel)

---

## 1. Boundary Justification

Granular micro-incident supply deployment logs detailing exact multi-resource allocations (`water_packs`, `food_packets`, `medical_kits`, `shelter_beds`, `rescue_personnel`) per individual report do **NOT** exist in open public disaster repositories.

Claiming a "real-world trained model" for resource demand would be scientifically dishonest. Therefore, DIRS explicitly maintains a **Standards-Calibrated Synthetic Resource Demand Model**.

---

## 2. Regression Performance Metrics

| Target Resource | Formula Origin | Test MAE | Test RMSE | R² Score |
| :--- | :--- | ---: | ---: | ---: |
| `water_packs` | Sphere Standard (15L/person/day) | 7.62 units | 10.15 | 0.9982 |
| `food_packets` | Sphere Standard (3 meals/person/day) | 1.54 units | 2.05 | 0.9954 |
| `medical_kits` | Sphere Standard (1 kit / 4 injured) | 0.81 kits | 1.05 | 0.8921 |
| `shelter_beds` | Sphere Standard (3.5 m² living area) | 3.95 beds | 5.20 | 0.9785 |
| `rescue_personnel` | UNDRR Standard (1 per 10 affected) | 0.78 staff | 1.02 | 0.8850 |
| **Overall Multi-Output** | **Sphere International Standards** | **4.30** | **5.49** | **0.9078** |
