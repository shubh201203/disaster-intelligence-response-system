# PHASE 5F-A — Data Strategy & Provenance Framework

**System:** Disaster Incident Response System (DIRS)  
**Phase:** 5F-A (Shelter & Volunteer Optimization: Research, Audit & Formulation)  
**Classification:** SYNTHETIC-CALIBRATED BENCHMARK SPECIFICATION  
**Date:** 2026-09-22  

---

## 1. Provenance Classifications & Data Hygiene

In accordance with strict project scientific hygiene rules, DIRS explicitly distinguishes between three tiers of operational data:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: GRAPH TOPOLOGY FOUNDATION (Phase 5C)                                │
│ • Synthetic-calibrated Chennai/Tamil Nadu disaster-corridor graph           │
│   using WGS-84 coordinates.                                                 │
│ • Road network topology and realistic connectivity graph representation.    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│ TIER 2: SYNTHETIC-CALIBRATED DISASTER DATA (Phase 5D, 5E, 5F)               │
│ • Statistically calibrated incident populations and damage demographics.    │
│ • Calibrated shelter capacity and amenity configurations.                   │
│ • Synthetic registered volunteer pools with realistic skill distributions.  │
│ • Deterministic pseudo-random generation using fixed PRNG seeds (seed=42).  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│ TIER 3: FUTURE OFFICIAL INGESTION PIPELINES (Post-Capstone / Future Scope)  │
│ • Greater Chennai Corporation (GCC) Relief Shelter Registry.                │
│ • Tamil Nadu State Disaster Management Authority (TNSDMA) Civil Defense.    │
│ • National Disaster Management Authority (NDMA) Volunteer Portals.          │
└─────────────────────────────────────────────────────────────────────────────┘
```

> [!CAUTION]
> **Strict Claim Boundaries:**
> 1. No real-time government volunteer tracking data is utilized.
> 2. No live personal identifiable information (PII) of actual citizens or responders is stored.
> 3. No official operational deployment of Tamil Nadu or Chennai municipal disaster shelters is claimed.
> 4. No live municipal GIS integration or live traffic telemetry is claimed.
> 5. All evaluations in Phase 5F are conducted using deterministic synthetic-calibrated benchmark datasets.

---

## 2. Demographic & Shelter Capacity Calibration Standards

The synthetic generation parameters are calibrated against Indian humanitarian emergency relief guidelines (NDMA Standard Operating Procedures and SPHERE International Minimum Humanitarian Standards):

### 2.1 Incident Evacuation Calibration

| Demographic Parameter | Calibrated Value Range | Empirical Rationale (Urban Flood Context) |
|---|---|---|
| **Displaced Population ($p_i$)** | $25 \text{ to } 500\text{ persons}$ | Corresponds to neighborhood residential blocks or inundation pockets. |
| **Vulnerable Subgroup Ratio ($p_{i, \text{ACC}} / p_i$)** | $15\% \text{ to } 25\%$ | Proportion of elderly citizens, wheelchair users, and infants requiring accessible facilities. |
| **Medical Assistance Ratio ($p_{i, \text{MED}} / p_i$)** | $5\% \text{ to } 12\%$ | Individuals with water-borne exposure, hypothermia, physical injury, or chronic medication needs. |

### 2.2 Shelter Capacity Calibration

| Shelter Archetype | Design Capacity ($K_s$) | Amenities Modeled | Example Calibration Proxy |
|---|---|---|---|
| **Primary Corporation School** | $100 \text{ to } 250\text{ persons}$ | Food, Water, Sanitation, Low Accessibility | Chennai Corporation High School |
| **Community / Marriage Hall** | $250 \text{ to } 500\text{ persons}$ | Food, Water, Sanitation, Generator Power | Zonal Community Center |
| **Indoor Sports Complex / Stadium** | $500 \text{ to } 1,500\text{ persons}$ | Full Medical Aid, Full Accessibility, Full Power | Jawaharlal Nehru Indoor Stadium |

### 2.3 Volunteer Skill & Workload Calibration

| Volunteer Skill Category | Population Share in Benchmark | Qualification Verification Prerequisite |
|---|---|---|
| **`GENERAL`** | $50\%$ | Basic registration verified. Community relief distribution. |
| **`LOGISTICS`** | $20\%$ | Warehouse sorting, vehicle driving, supply dispatch. |
| **`MEDICAL`** | $18\%$ | Requires `medical_certified == True` (Doctor, Nurse, Paramedic, EMT). |
| **`RESCUE`** | $12\%$ | Swift-water rescue, structural clearing, inflatable boat handling. |

---

## 3. Future Real Data Ingestion Strategy (Prospective Architecture)

To transition from synthetic calibration to live municipal deployment in future operational phases:
1. **GCC Relief Camp Registry API:** Prospective integration with Greater Chennai Corporation's GIS shelter inventory (`gcc.gov.in/gis`) to pull verified geo-coordinates, room counts, and ward officer contacts.
2. **Aapda Mitra Volunteer Portal (NDMA):** Prospective integration with India's national disaster volunteer database for pre-vetted identity verification, certificate tracking, and training status.
3. **OpenStreetMap Humanitarian Data (HOT-OSM):** Automated extraction of public schools, colleges, and civic auditoriums tagged `amenity=shelter` or `building=civic`.
