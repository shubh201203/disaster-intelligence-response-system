# DIRS Phase 4 — Incident Severity Real-World Model Evaluation Report

## 1. Executive Summary & Dual-Framework Disclosure

- **Selected Model:** `GradientBoostingClassifier`
- **Model Version:** `v2.0.0-realworld` (`backend/app/ai/models/severity_model.pkl`)
- **Dataset:** OpenFEMA Individual & Public Assistance + CrisisNLP Emergency Corpus (5,000 records)
- **Target Construction:** Derived Composite Impact Index ($S_{\text{impact}}$) mapped to quantile severity tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- **Validation Methodology:** 5-Fold `GroupKFold` by Disaster Event ID (Zero spatial/scene leakage)

---

## 2. Quantitative Performance Metrics (Dual-Framework Analysis)

| Evaluation Perspective | Features Included | Accuracy | Macro Precision | Macro Recall | Macro F1 | Critical Recall |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| **Impact-Framework Consistency** | Full Feature Set (6 inputs: affected, injured, vulnerable, infra, hazard, text urgency) | **97.11%** | **97.02%** | **96.88%** | **0.9695** | **96.82%** |
| **Independent Predictive Validity** | Non-Target Features ONLY (`disaster_type_code`, `distress_urgency_score`) | **33.03%** | **23.10%** | **25.00%** | **0.1744** | **1.27%** |

---

## 3. Methodological Disclosure & Scientific Rationale

- **Impact-Framework Consistency (F1 = 0.9695):** Demonstrates that the `GradientBoostingClassifier` faithfully reproduces the operational disaster triage rules defined by the Composite Impact Index ($S_{\text{impact}}$).
- **Independent Predictive Validity (F1 = 0.1744):** Discloses that without physical casualty counts (`injured_count`, `vulnerable_count`), text distress urgency and hazard type alone cannot independently predict exact quantitative severity tiers. This transparent disclosure prevents false claims of independent predictive accuracy.
