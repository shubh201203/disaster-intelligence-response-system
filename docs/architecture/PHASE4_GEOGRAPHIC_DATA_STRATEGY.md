# DIRS Phase 4 — Geographic Relevance & India Data Alignment Strategy

## Executive Summary & Final Verdict

- **India Relevance Assessment:** **`STRONG`**
- **Geographic Alignment Strategy:** Hybrid Global-Benchmark Training + Indian Domain Calibration (IMD Weather Grids & Bhuvan ISRO Hazard Zones)

---

## 1. Assessment of Public Indian Disaster & Meteorological Datasets

| Candidate Indian Source | Governing Body | Data Type | License / Access | Geographic Scope | Technical Assessment |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **IMD High-Resolution Daily Weather Grids** | India Meteorological Dept | 0.25° x 0.25° Gridded Rainfall & Temp (1901–Present) | Open Government Data (OGD) India | India Subcontinent | **HIGH SUITABILITY.** Excellent for meteorological risk calibration. |
| **Bhuvan ISRO Disaster Geoportal** | ISRO / Dept of Space | Flood Inundation Maps, Cyclone Tracks, Landslide Zonation | Government Open Access | Pan-India | **HIGH SUITABILITY.** Provides geospatial hazard ground truth. |
| **NDMA Annual Disaster Reports** | NDMA India | State-level casualty & damage statistics | Public Document | India States | **MEDIUM SUITABILITY.** Unstructured PDF tables; requires manual tabular extraction. |

---

## 2. Comparison: US / Global Benchmarks vs Indian Regional Datasets

| Domain | Global Benchmark Dataset (xBD / OpenFEMA / NOAA) | Indian Regional Dataset (IMD / Bhuvan / NDMA) | Technical Trade-off & Resolution |
| :--- | :--- | :--- | :--- |
| **Damage Imagery (CV)** | **xBD / CrisisMMD:** 850,000+ polygons, standardized 4-class labels, high-res pre/post disaster pairs. | **Bhuvan ISRO:** Flood inundation satellite overlays; lack micro-building vector polygon annotations. | **Resolution:** Use **xBD** for primary CV model training; evaluate on CrisisMMD/regional flood photos. |
| **Weather / Risk** | **NOAA GHCN:** Global station network, hourly wind/pressure. | **IMD Gridded Daily:** 0.25° gridded daily monsoon rainfall & max temp. | **Resolution:** Use **IMD Gridded Weather** for Indian hazard risk calibration; use NOAA for global baseline. |
| **Incident Severity** | **OpenFEMA:** 180,000+ structured individual/public assistance records. | **NDMA Reports:** State-level annual aggregate damage totals. | **Resolution:** Train severity classifier on OpenFEMA + CrisisNLP; validate on NDMA disaster thresholds. |

---

## 3. Hybrid Execution Strategy

To ensure DIRS remains an authentic India-relevant capstone system without compromising ML training sample size:

```text
               TRAINING PHASE                             CALIBRATION & VALIDATION PHASE
   ┌────────────────────────────────────┐             ┌────────────────────────────────────┐
   │ High-Scale Global Benchmarks       │             │ Regional Indian Domain Data        │
   │  • xBD Building Damage Imagery     │  ─────────► │  • IMD Gridded Rainfall (0.25°)    │
   │  • OpenFEMA Incident Reports       │             │  • ISRO Bhuvan Cyclone/Flood Zones │
   │  • NOAA Global Climatology GHCN    │             │  • NDMA Emergency Guidelines       │
   └────────────────────────────────────┘             └────────────────────────────────────┘
```

This hybrid strategy ensures maximum model generalizability while preserving Indian operational disaster relevance.
