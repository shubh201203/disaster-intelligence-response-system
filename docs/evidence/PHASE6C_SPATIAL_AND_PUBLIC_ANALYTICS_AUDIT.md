# DIRS Phase 6C — Spatial Intelligence & Public Analytics Forensic Audit

**Audit Date:** 2026-11-16T01:59:45+05:30  
**Auditor Role:** Independent Geospatial Analytics Auditor & PostGIS Reviewer  
**Target Code:** `app/recovery/services/recovery_spatial_service.py` & `app/routers/recovery.py`

---

## 1. Executive Summary

This audit assesses the spatial querying mechanisms, coordinate validation, administrative ward aggregations, and public situational awareness endpoints delivered in Phase 6C.

**Core Findings:**
1. **PostGIS Queries & Dialect Fallbacks**: In PostgreSQL, spatial radius searches correctly use `ST_DWithin` on geometry cast to `Geography` for accurate metric meter distance evaluations (`SRID=4326`). A mathematically accurate Haversine great-circle fallback is maintained for non-PostGIS test harnesses.
2. **Explicit Synthetic Boundary Labeling**: Synthetic ward boundaries returned in `RecoverySpatialSummaryResponse` are explicitly labeled with `is_synthetic: true`, `is_synthetic_boundary: true`, and an unambiguous disclaimer stating that authoritative boundaries are pending state revenue department release.
3. **Public Analytics Aggregation Discrepancy**: The public situational summary (`/api/v1/recovery/analytics/summary`) correctly scrubs all household PII, but queries all current assessments without filtering out `verification_status == "PENDING_VERIFICATION"`, inadvertently including uncertified preliminary screening numbers into public totals.

---

## 2. PostGIS Spatial Implementation Audit

### 2.1 Geometry Construction & SRID Consistency
In `DamageAssessmentService.submit_field_inspection`:
```python
geom_point = None
if db.bind and db.bind.dialect.name == "postgresql":
  geom_point = ST_SetSRID(ST_MakePoint(data.longitude, data.latitude), 4326)
```
- Spatial Reference System: `SRID=4326` (WGS 84).
- Point Construction: `ST_MakePoint(longitude, latitude)` followed by `ST_SetSRID(..., 4326)`. Coordinates are correctly mapped as $(X=\text{lon}, Y=\text{lat})$.

### 2.2 Radius Spatial Search (`query_damage_by_radius`)
In [`recovery_spatial_service.py`, lines 49-96](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services/recovery_spatial_service.py#L49-L96):
- **Coordinate Boundary Validation**:
  Checks `-90.0 <= latitude <= 90.0` and `-180.0 <= longitude <= 180.0`. Rejects out-of-range coordinates with `HTTP 400 Bad Request`.
- **Search Radius Bounds**:
  Enforces `0.1 <= radius_km <= 500.0`.
- **PostgreSQL / PostGIS Implementation**:
  ```python
  radius_meters = radius_km * 1000.0
  point_geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
  q = q.filter(
      func.ST_DWithin(
          func.cast(RecoveryAssessment.geom, func.Geography),
          func.cast(point_geom, func.Geography),
          radius_meters,
      )
  )
```
  Casting to `Geography` ensures that distance calculations are calculated in true metric meters along the WGS 84 ellipsoid, avoiding distortion common to naive planar degree projections.
- **SQLite / Non-PostGIS Fallback**:
  Computes great-circle distance using the standard Haversine formulation:
  $$d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$
  with mean Earth radius $R = 6371.0\text{ km}$.

---

## 3. Administrative Boundaries & Synthetic GeoJSON Audit

### 3.1 Provenance of Ward Boundaries
In [`recovery_spatial_service.py`, lines 28-35](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services/recovery_spatial_service.py#L28-L35):
```python
SYNTHETIC_WARDS = {
    "WARD-01": {
        "name": "George Town / Port",
        "center": (13.0900, 80.2900),
        "radius_km": 2.5,
    },
    "WARD-02": {
        "name": "Royapuram",
        "center": (13.1100, 80.2950),
        "radius_km": 2.5,
    },
    "WARD-03": {"name": "T Nagar", "center": (13.0400, 80.2300), "radius_km": 3.0},
    "WARD-04": {
        "name": "Mylapore",
        "center": (13.0300, 80.2700),
        "radius_km": 2.5,
    },
    "WARD-05": {"name": "Adyar", "center": (13.0000, 80.2550), "radius_km": 3.0},
}
```
**Forensic Findings**:
- Administrative boundaries are **synthetic circular buffers** centered on approximate ward centroids in Chennai.
- The system **does not possess official cadastral polygons** from the Greater Chennai Corporation or Survey of India.
- **Mandatory Disclaimer Enforcement**:
  Every response from `/api/v1/recovery/spatial/damage-summary` returns:
  ```json
  "is_synthetic_boundary": true,
  "spatial_boundary_geojson": {
    "type": "Feature",
    "properties": {
      "ward_code": "WARD-04",
      "is_synthetic": true,
      "disclaimer": "Synthetic spatial boundary for simulation and test validation only. Authoritative boundary dataset pending state revenue department release."
    },
    "geometry": {
      "type": "Point",
      "coordinates": [80.27, 13.03]
    }
  }
  ```
- Compliance: Complies with the prompt requirement to explicitly label synthetic spatial boundaries and avoid claiming authoritative GIS provenance.

---

## 4. Public Situational Analytics Audit

In `RecoverySpatialService.get_public_analytics_summary` ([`recovery_spatial_service.py`, lines 197-245](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services/recovery_spatial_service.py#L197-L245)):
```python
asms = (
    db.query(RecoveryAssessment)
    .filter(RecoveryAssessment.is_current_version == True)
    .all()
)
```

### 4.1 PII Protection:
- Output schema `RecoveryAnalyticsSummaryResponse` only provides numerical aggregates (`total_facilities_assessed`, `operational_facilities_percentage`, `damage_distribution`, `sectoral_distribution`, `average_power_restoration_pct`, `aggregated_affected_households`).
- Strictly zero beneficiary names, phone numbers, or household locations are serialized.

### 4.2 Inclusion of Unverified Preliminary Screening:
- The query filters by `is_current_version == True`, but **does not filter** by `verification_status == "VERIFIED"`.
- Consequently, unverified Tier-1 AI screenings (`PENDING_VERIFICATION`) or uncertified volunteer field reports are included in the public situational dashboard totals.
- This creates a minor tension with the policy that unverified screening claims must not be presented to the public as official recovery statistics.

---

## 5. Material Findings & Risk Assessment

- **Finding DEF-6C-SPA-01 (Inclusion of Unverified Assessments in Public Analytics)**:
  - *Location*: `backend/app/recovery/services/recovery_spatial_service.py` line 205.
  - *Severity*: **MEDIUM (Data Presentation Compliance)**.
  - *Description*: `get_public_analytics_summary` aggregates all current assessments rather than filtering `RecoveryAssessment.verification_status == "VERIFIED"` (or segregating verified vs pending counts in public distribution).
  - *Remediation Recommendation*: Either filter by `RecoveryAssessment.verification_status == 'VERIFIED'` or provide two explicit fields in `RecoveryAnalyticsSummaryResponse`: `total_verified_facilities` and `total_pending_screening_facilities`.
