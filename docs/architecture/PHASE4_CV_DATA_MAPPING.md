# DIRS Phase 4 — Computer Vision Dataset Selection & Task Mapping

## Executive Summary & Final Verdict

- **Primary CV Dataset:** **xBD (xView2 Building Damage Assessment Dataset)**
- **Secondary / Robustness Dataset:** **CrisisMMD Ground-Level Emergency Imagery Corpus**
- **CV Task Definition:** **Multi-Class Structural Damage Severity Classification** (4 classes: `NO_DAMAGE`, `LOW_DAMAGE`, `SEVERE_DAMAGE`, `DESTROYED`)
- **Selected Deep Learning Candidate:** **ResNet18 / MobileNetV3 Transfer Learning Backbone**
- **Decision Status:** **`READY`**

---

## 1. Candidate CV Dataset Evaluation Scorecard

| Dataset | Task Scope | Images / Tiles | Annotations | Disaster Types | Geography | License | Annotation Quality | Selection Status |
| :--- | :--- | ---: | :--- | :--- | :--- | :--- | :---: | :---: |
| **xBD (xView2)** | Satellite/Aerial Building Damage | 850,000+ polygons (45,000+ km²) | Polygonal Vector Masks + 4 Damage Classes | Earthquake, Flood, Hurricane, Tsunami, Wildfire | Global (US, Asia, LatAm) | CC BY-NC 4.0 | `HIGH` (Expert Vector) | **`PRIMARY`** |
| **CrisisMMD** | Ground-Level Citizen Photo Damage | 16,080 photo crops | Image-level damage severity tiers | Hurricane, Flood, Earthquake, Wildfire | US, Caribbean, Mexico | CC BY 4.0 | `HIGH` (Multi-annotator) | **`SECONDARY / ROBUSTNESS`** |
| **AIDER** | UAV Drone Emergency Scenes | 6,400 images | Event scene tags | Fire, Flood, Collapse | Regional | CC BY 4.0 | `MEDIUM` | **`REJECTED`** |

---

## 2. CV Task Definition & DIRS Target Mapping

The CV task is defined strictly as **Multi-Class Image Damage Severity Classification** to preserve the existing DIRS API contract (`/api/ai/computer-vision/assess`). Object detection and semantic segmentation were evaluated but rejected to avoid unnecessary architectural bloat during capstone execution.

### Target Mapping Schema:

$$\text{xBD Class Label} \longrightarrow \text{DIRS Damage Output Tier}$$

- `no-damage` $\longrightarrow$ **`NO_DAMAGE`**
- `minor-damage` $\longrightarrow$ **`LOW_DAMAGE`**
- `major-damage` $\longrightarrow$ **`SEVERE_DAMAGE`**
- `destroyed` $\longrightarrow$ **`DESTROYED`**

---

## 3. Comparative CV Model Benchmark Design

To scientifically demonstrate the transition from synthetic classical features to real-world deep learning, three distinct models will be evaluated on the **EXACT SAME UNTOUCHED REAL-WORLD TEST SPLIT** (GroupKFold by disaster event):

```text
Real Disaster Image Test Set (GroupKFold: Unseen Disaster Event)
                        │
      ┌─────────────────┼─────────────────┐
      ▼                 ▼                 ▼
 [Baseline A]      [Baseline B]      [Candidate C]
 Existing Classical   Classical PIL     Lightweight Transfer
 PIL Features on      Features on       Learning CNN (ResNet18 /
 Synthetic Data       Real Data         MobileNetV3)
      │                 │                 │
      ▼                 ▼                 ▼
 Comparative Metric Table (Macro F1, Critical Recall, Confusion Matrix, Latency)
```

### Benchmark Protocol:
1. **Baseline A:** Existing Random Forest model trained on synthetic feature distributions, evaluated on real image test features.
2. **Baseline B:** Same Random Forest model re-trained on 6 handcrafted PIL features (`edge_density`, `entropy`, `color_var`, `darkness`, `asymmetry`, `roughness`) extracted directly from real disaster imagery.
3. **Candidate C:** Fine-tuned `ResNet18` or `MobileNetV3` deep CNN operating directly on raw RGB disaster image patches ($224 \times 224$).

---

## 4. Summary & Verification

Primary dataset selection (**xBD**) and task definition map directly to DIRS requirements. Benchmark protocol ensures rigorous comparative evaluation. Target status: **`READY`**.
