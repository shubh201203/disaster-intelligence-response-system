# DIRS Phase 6C — API Traceability Matrix & Contract Specification

## 1. Scope & Namespace
All Phase 6C endpoints are exposed under the `/api/v1/recovery` namespace. They build directly on the frozen Phase 6B relational schema and extend the recovery intelligence capabilities across Tier-1 AI damage screening, human engineering verification, structured needs assessment, population reconciliation, and spatial analytics.

---

## 2. API Traceability Matrix

| Method | Endpoint | Description | Request Model | Response Model | Authorized Roles | Audit Log Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/recovery/damage-assessments/screen-image` | Tier-1 AI damage screening from base64 visual imagery | `DamageScreeningRequest` | `DamageScreeningResponse` | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | `CV_SCREEN_DAMAGE` |
| `POST` | `/api/v1/recovery/damage-assessments/field-inspection` | Ingests on-site structural engineering field inspection | `DamageAssessmentFieldCreate` | `RecoveryAssessmentResponse` | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | `CREATE_DAMAGE_ASSESSMENT` |
| `POST` | `/api/v1/recovery/damage-assessments/{id}/verify` | Government engineering verification and certification gate | `DamageAssessmentVerifyRequest` | `RecoveryAssessmentResponse` | `GOVT`, `ADMIN` | `VERIFY_DAMAGE_ASSESSMENT` |
| `POST` | `/api/v1/recovery/damage-assessments/{id}/supersede` | Monotonic version supersession ($V_k \to V_{k+1}$) | `RecoveryAssessmentSupersede` | `RecoveryAssessmentResponse` | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | `ASSESSMENT_SUPERSEDE` |
| `GET` | `/api/v1/recovery/damage-assessments/{id}/history` | Chronological version lineage and supersession audit trail | None | `DamageAssessmentHistoryResponse` | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | None (Read) |
| `POST` | `/api/v1/recovery/needs/structured` | Ingests multi-sectoral needs with demographic conservation | `StructuredRecoveryNeedCreate` | `StructuredRecoveryNeedResponse` | `GOVT`, `NGO`, `ADMIN` | `CREATE_STRUCTURED_NEED` |
| `GET` | `/api/v1/recovery/needs/structured` | Lists sector recovery needs with demographic breakdowns | Query Params (`sector`, `ward_code`) | `List[StructuredRecoveryNeedResponse]` | `GOVT`, `NGO`, `ADMIN` | None (Read) |
| `POST` | `/api/v1/recovery/reconciliation/reconcile-population` | Deduplicates beneficiary records and detects conflicts | `PopulationReconciliationRequest` | `PopulationReconciliationResponse` | `GOVT`, `NGO`, `ADMIN` | None (Analytical) |
| `GET` | `/api/v1/recovery/spatial/radius` | PostGIS spatial distance query within $R$ kilometers | Query Params (`lat`, `lon`, `radius_km`) | `List[RecoveryAssessmentResponse]` | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | None (Read) |
| `GET` | `/api/v1/recovery/spatial/bbox` | PostGIS spatial bounding-box envelope search | Query Params (`min_lat`, `min_lon`, ...) | `List[RecoveryAssessmentResponse]` | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | None (Read) |
| `GET` | `/api/v1/recovery/spatial/damage-summary` | Administrative ward damage and needs rollup with GeoJSON | Query Params (`ward_code`) | `RecoverySpatialSummaryResponse` | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | None (Read) |
| `GET` | `/api/v1/recovery/analytics/summary` | Public situational awareness dashboard (scrubbed PII) | None | `RecoveryAnalyticsSummaryResponse` | Public (`None`) | None (Public Read) |

---

## 3. Request / Response Contract Schemas

### 3.1 AI Screening (`/damage-assessments/screen-image`)
```json
// Request
{
  "image_base64": "/9j/4AAQSkZJRg...",
  "incident_id": "8bb38f82-353d-4c3d-bebe-08f331f40d7c"
}

// Response (HTTP 200)
{
  "cv_assessment_id": "a9010bb1-8e55-4fa8-9d41-4c6fef4e872e",
  "damage_level": "MODERATE",
  "confidence_pct": 84.5,
  "confidence_score": 0.845,
  "predicted_class": "MODERATE",
  "probabilities": {
    "NONE": 0.02,
    "MINOR": 0.08,
    "MODERATE": 0.845,
    "SEVERE": 0.045,
    "DESTROYED": 0.01
  },
  "physical_features": {
    "debris_density": 0.35,
    "structural_collapse": 0.12,
    "water_inundation": 0.05,
    "smoke_burn": 0.00,
    "roof_damage": 0.42,
    "vegetation_obstruction": 0.10
  },
  "disclaimer": "Automated AI screening (Tier-1). Preliminary advisory only. Not certified for structural condemnation, financial compensation, or reconstruction contracting until reviewed and approved by a licensed Government Structural Engineer.",
  "is_screened_only": true,
  "verification_status": "PENDING_VERIFICATION",
  "requires_engineering_review": true
}
```

### 3.2 Structured Recovery Need (`/needs/structured`)
```json
// Request
{
  "ward_code": "WARD-04",
  "district": "Chennai",
  "sector": "HOUSING",
  "total_affected_households": 25,
  "total_displaced_persons": 100,
  "demographic_breakdown": {
    "general_need": 65,
    "accessibility_need": 15,
    "medical_need": 15,
    "med_accessibility_need": 5,
    "total_displaced_persons": 100
  },
  "potable_water_demand_liters_day": 1500.0,
  "temporary_shelter_units_needed": 25,
  "census_baseline_population": 12500,
  "beneficiary_raw_id": "AADHAAR-9988-1122",
  "household_head_name": "Rajaraman"
}

// Response (HTTP 201)
{
  "id": "e458da91-d2bf-463e-a107-16010b985c49",
  "ward_code": "WARD-04",
  "district": "Chennai",
  "sector": "HOUSING",
  "affected_households": 25,
  "displaced_persons": 100,
  "demographic_breakdown": {
    "general_need": 65,
    "accessibility_need": 15,
    "medical_need": 15,
    "med_accessibility_need": 5,
    "total_displaced_persons": 100
  },
  "potable_water_demand_liters_day": 1500.0,
  "temporary_shelter_units_needed": 25,
  "beneficiary_id_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "household_head_name_masked": "R***n",
  "is_reconciled": true,
  "census_baseline_population": 12500,
  "data_timestamp": "2026-11-16T01:47:00Z"
}
```
