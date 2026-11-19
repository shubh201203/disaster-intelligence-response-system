# DIRS Phase 4 - Model Selection Gate Report

## Model Selection Rationale and Criteria

Models were selected based on High-Risk Class Recall, Macro F1 Score, GroupKFold Event Generalization, and Inference Latency:

- Severity Engine: Selected GradientBoostingClassifier (v2.0.0-realworld).
  - Impact-Framework Consistency Macro F1: 0.9695 (Critical Recall: 96.82%).
  - Independent Predictive Validity Macro F1: 0.1744 (Text Urgency + Hazard Code Only).
- Disaster Risk Engine: Selected GradientBoostingClassifier (v2.0.0-realworld).
  - Macro F1: 0.9123 (Extreme Risk Recall: 92.50%).
  - Leakage Control: Zero temporal leakage (antecedent T-24h to T-72h weather observations predicting T -> T+24h event outcome).
- CV Damage Engine: Selected ResNet18 Deep Vision Backbone + RandomForestClassifier (v2.0.0-realworld).
  - Raw Satellite RGB Image Benchmark Macro F1: 0.8210 (Accuracy: 82.24%, Destroyed Recall: 80.89%).
  - Manifest: backend/app/ai/models/cv_model_manifest.json
- Resource Demand Engine: Selected SphereCalibrated_RandomForestRegressor (v2.0.0-calibrated).
  - Status: SYNTHETIC-CALIBRATED (Anchored in UN Sphere International Minimum Standards; Overall MAE: 4.30 units, Overall R2: 0.9078).
