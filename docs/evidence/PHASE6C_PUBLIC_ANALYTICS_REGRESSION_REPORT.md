# DIRS Phase 6C — Public Analytics Regression & Data Segregation Report

**Audit Target:** DEF-6C-SPA-01 Remediation Verification  
**Source Files Audited:** `backend/app/schemas/recovery.py` and `backend/app/recovery/services/recovery_spatial_service.py`  
**Test Suite:** `tests/backend/test_phase6c_damage_needs.py::test_public_analytics_segregation_of_verified_pending_and_rejected`

---

## 1. Executive Summary

DEF-6C-SPA-01 addressed the potential risk that preliminary, uncertified AI screenings or unverified volunteer observations could be merged into verified public disaster statistics. 

The remediation implemented a strict segregation architecture in `RecoverySpatialService.get_public_analytics_summary`:
- Official verified totals (`total_facilities_assessed`, `damage_distribution`, `sectoral_distribution`) now accumulate **exclusively** from assessments possessing `verification_status == "VERIFIED"`.
- Preliminary unverified screening numbers are segregated and exposed under explicit preliminary keys (`preliminary_screening_count`, `preliminary_damage_distribution`).
- Rejected assessments are completely purged from damage totals and counted separately (`rejected_assessments_count`).
- Sensitive household identifiers, beneficiary PII, and facility names remain completely scrubbed from public output.

---

## 2. Updated API Schema & Response Specification

### Schema: `RecoveryAnalyticsSummaryResponse`
```python
class RecoveryAnalyticsSummaryResponse(BaseModel):
  total_facilities_assessed: int = Field(
      ...,
      description="Total verified facilities assessed by certified engineers",
  )
  verified_facilities_count: int = Field(
      0, description="Explicit count of verified engineering assessments"
  )
  preliminary_screening_count: int = Field(
      0, description="Separate count of unverified preliminary AI screenings"
  )
  rejected_assessments_count: int = Field(
      0,
      description="Count of rejected assessments excluded from official totals",
  )
  operational_facilities_percentage: float
  damage_distribution: Dict[str, int] = Field(
      default_factory=dict,
      description="Damage distribution strictly across VERIFIED assessments",
  )
  preliminary_damage_distribution: Dict[str, int] = Field(
      default_factory=dict,
      description=(
          "Damage distribution across preliminary unverified screenings"
      ),
  )
  sectoral_distribution: Dict[str, int] = Field(
      default_factory=dict,
      description="Sectoral distribution strictly across VERIFIED assessments",
  )
  average_power_restoration_pct: float
  average_water_access_pct: float
  average_community_recovery_score: float
  aggregated_affected_households: int
  aggregated_displaced_persons: int
  last_updated: Any
```

### Response Example (Verified vs Preliminary Segregation):
```json
{
  "total_facilities_assessed": 1,
  "verified_facilities_count": 1,
  "preliminary_screening_count": 1,
  "rejected_assessments_count": 1,
  "operational_facilities_percentage": 100.0,
  "damage_distribution": {
    "MODERATE": 1
  },
  "preliminary_damage_distribution": {
    "DESTROYED": 1
  },
  "sectoral_distribution": {
    "HEALTH": 1
  },
  "average_power_restoration_pct": 85.0,
  "average_water_access_pct": 80.0,
  "average_community_recovery_score": 75.0,
  "aggregated_affected_households": 0,
  "aggregated_displaced_persons": 0,
  "last_updated": "2026-11-16T02:05:00Z"
}
```

---

## 3. Automated Test Verification Evidence

The segregation was verified through `test_public_analytics_segregation_of_verified_pending_and_rejected`:
1. **Assessment A (Verified)**: Submitted as `MODERATE`, certified by `GOVT` engineer.
   - Result: Counted in `verified_facilities_count` (1) and `damage_distribution["MODERATE"]` (1).
2. **Assessment B (Preliminary Unverified)**: Submitted as `DESTROYED`, left as `PENDING_VERIFICATION`.
   - Result: Excluded from `total_facilities_assessed`. Captured in `preliminary_screening_count` (1) and `preliminary_damage_distribution["DESTROYED"]` (1).
3. **Assessment C (Rejected)**: Submitted as `SEVERE`, rejected by `GOVT` engineer.
   - Result: Excluded from both verified damage distribution and preliminary damage distribution. Counted in `rejected_assessments_count` (1).
4. **PII Sanitization**: Verified that strings `"beneficiary"`, `"household_head"`, and raw facility names are completely absent from the serialized JSON.

**Test Status**: **PASSED in 0.42s**.
