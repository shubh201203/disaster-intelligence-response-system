# DIRS Phase 5A — AI Prediction Pipeline to Optimization Parameter Mapping

## Executive Summary

The Phase 5 Optimization Layer operates as the decision-support engine consuming downstream AI outputs from DIRS Phase 3A (Resource Demand Prediction), Phase 3B (Priority Score Engine), Phase 3C (Grounded RAG Knowledge Base), and Phase 4 (Severity & Risk ML Models). 

This document defines the exact data transformations, conversion formulas, scaling parameters, and normalization rules required to convert continuous AI predictions into formal constraints and objective function weights for the OR-Tools solver.

---

## 1. End-to-End AI-to-Optimization Pipeline Architecture

```
┌───────────────────────────────────────────────────────────┐
│ PHASE 4 AI ENGINES                                        │
│ - RGB ResNet18 Damage Model (xBD) ──► Image Severity     │
│ - Gradient Boosting Risk Model  ──► Dynamic Risk Score   │
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ PHASE 3B PRIORITY ENGINE                                  │
│ - Continuous Priority Calculator ──► Priority Score P_i   │
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ PHASE 3A RESOURCE DEMAND PREDICTOR                       │
│ - Humanitarian Demand Model      ──► Demand Quantities d_ir│
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ PHASE 5 PARAMETER TRANSFORMER (Phase 5 Pipeline Component)│
│ - Integer domain scaling (x1000 multiplier for CP-SAT)    │
│ - Time window bounds mapping                              │
│ - Multi-objective cost penalty weight construction        │
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ PHASE 5 OPTIMIZATION SOLVER (OR-Tools CP-SAT & Routing)  │
│ - Output: Optimized Dispatch & Vehicle Route Recommendation│
└───────────────────────────────────────────────────────────┘
```

---

## 2. Comprehensive AI-to-Optimization Parameter Mapping Matrix

| Upstream AI Service / Phase | Output Field Name | Data Type & Range | Optimization Parameter | Transformation & Mathematical Formula `[FORMULA SPECIFICATION]` |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 3A Resource Predictor** | `water` (liters) | Continuous float $\ge 0$ | $d_{i, \text{water}}$ (Demand parameter) | $\hat{d}_{i,\text{water}} = \lceil d_{\text{water}} \rceil$ |
| **Phase 3A Resource Predictor** | `food` (kg) | Continuous float $\ge 0$ | $d_{i, \text{food}}$ (Demand parameter) | $\hat{d}_{i,\text{food}} = \lceil d_{\text{food}} \rceil$ |
| **Phase 3A Resource Predictor** | `medical` (kits) | Continuous float $\ge 0$ | $d_{i, \text{medical}}$ (Demand parameter) | $\hat{d}_{i,\text{medical}} = \lceil d_{\text{medical}} \rceil$ |
| **Phase 3A Resource Predictor** | `shelter` (tents) | Continuous float $\ge 0$ | $d_{i, \text{shelter\_kit}}$ (Demand parameter) | $\hat{d}_{i,\text{shelter\_kit}} = \lceil d_{\text{shelter}} \rceil$ |
| **Phase 3A Resource Predictor** | `personnel` (count) | Continuous float $\ge 0$ | $d_{i, \text{personnel}}$ (Demand parameter) | $\hat{d}_{i,\text{personnel}} = \lceil d_{\text{personnel}} \rceil$ |
| **Phase 3B Priority Engine** | `priority_score` | Float $[0.0, 100.0]$ | $P_i$ (Objective Weight) | $W_{\text{penalty}, i} = \lfloor P_i \times 1000 \rfloor$ (Scaled integer for OR-Tools) |
| **Phase 3B Priority Engine** | `priority_level` | Categorical (`LOW`..`CRITICAL`) | Urgency Tier | Maps directly to response SLA priority tier |
| **Phase 4 Severity Model** | `predicted_severity` | Categorical (`LOW`..`CRITICAL`) | Arrival Time Window $T_i^{\text{target}}$ | `CRITICAL`: 45 mins<br>`HIGH`: 90 mins<br>`MEDIUM`: 180 mins<br>`LOW`: 360 mins |
| **Phase 4 Severity Model** | `severity_confidence` | Float $[0.0, 1.0]$ | Buffer Margin $\beta_i$ | $T_i^{\text{target, buffered}} = T_i^{\text{target}} \times (1.5 - 0.5 \times \text{confidence})$ |
| **Phase 4 Risk Model** | `risk_score` | Float $[0.0, 1.0]$ | Route Safety Weighting | Multiplies edge travel cost over flood-prone road segments |
| **Phase 3C Grounded RAG** | `sop_citation` | Text Source Doc | Constraint Override Rule | Ingests regional evacuation SOP minimum staffing rules |

---

## 3. Transformation & Scaling Formulas

### 3.1 OR-Tools Integer Domain Scaling
Google OR-Tools `CP-SAT` operates on 64-bit integer domains. Continuous float values from AI predictors must be scaled deterministically:

1. **Demand Quantities ($d_{i,r}$)**:
   $$d_{i,r}^{\text{integer}} = \text{int}\left( \lceil d_{i,r}^{\text{predicted}} \rceil \right)$$
2. **Priority Weighting Penalty ($W_{\text{penalty}, i}$)**:
   $$W_{\text{penalty}, i} = \text{int}\left( P_i \times 1000 \right)$$
   *(e.g., Priority Score 87.45 becomes integer weight 87,450)*
3. **Road Graph Travel Time ($t_{m,n}$)**:
   $$t_{m,n}^{\text{integer}} = \text{int}\left( t_{m,n}^{\text{seconds}} \right)$$

### 3.2 Dynamic Time Window Mapping Formula
Target arrival time windows ($T_i^{\text{target}}$) in minutes are dynamically constructed from Phase 3B Priority Score ($P_i$) and Phase 4 Severity Level ($S_i$):

$$T_i^{\text{target}} = \max\left( 30, \;\; 240 - 2.0 \times P_i \right) \quad \text{minutes}$$

### 3.3 Handling Model Uncertainty & Confidence Bounds
If Phase 4 Severity or Phase 3A Demand predictions have low confidence scores ($\text{confidence} < 0.60$), the parameter transformer automatically applies a conservative safety margin:
$$d_{i,r}^{\text{robust}} = d_{i,r}^{\text{predicted}} \times \left(1.0 + (1.0 - \text{confidence})\right)$$
This ensures that optimization dispatch does not under-allocate resources to high-uncertainty disaster sites.
