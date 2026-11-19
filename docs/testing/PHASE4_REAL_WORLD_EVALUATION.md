# DIRS Phase 4 — Real-World Synthetic vs Real Model Robustness Comparison

## Synthetic vs Real Performance & Robustness Comparison Matrix

| DIRS AI Model | Synthetic Baseline F1 | Real-World Clean F1 | Real-World Perturbed F1 | Robustness Retained | Selected Status |
| :--- | ---: | ---: | ---: | ---: | :---: |
| **Incident Severity** | 0.9880 | **0.9935** | **0.9328** | **93.89%** | `ACTIVE` |
| **Disaster Risk** | 0.9940 | **0.9775** | **0.8374** | **85.67%** | `ACTIVE` |
| **CV Damage Assessment** | 0.9920 | **1.0000** | **0.9752** | **97.52%** | `ACTIVE` |
| **Resource Demand** | 0.9980 (R²) | **0.9078 (R²)** | **0.8850 (R²)** | **97.49%** | `SYNTHETIC-CALIBRATED` |

## Robustness Interpretation & Key Findings

1. **Incident Severity:** Real-world model trained on OpenFEMA + CrisisNLP retains **93.89%** performance under 15% Gaussian feature noise.
2. **Disaster Risk:** Real-world meteorological risk model retains **85.67%** performance under atmospheric measurement noise.
3. **Computer Vision Damage:** Real image classifier retains **97.52%** performance under visual blur/compression noise.
4. **Resource Demand:** UN Sphere Humanitarian Minimum Standards calibrated regressor provides realistic multi-resource output bounding.
