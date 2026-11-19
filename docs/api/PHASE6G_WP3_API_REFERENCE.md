# DIRS Phase 6G Accelerated Programme: Work Package 3
# API Reference & Data Transfer Contracts

**Document Identifier:** `DIRS-PH6G-WP3-API-REF-005`  
**Security Classification:** OFFICIAL / SENSITIVE  
**Target Release:** DIRS v5.2  
**Parent Roadmap Phase:** Phase 6G — Cross-Role UI Integration, E2E Verification & Capstone Forensic Closure  
**Status:** Certified / Completed  

---

## 1. Overview

This document provides the definitive REST API contracts, authentication requirements, and request/response payloads utilized across the cross-role user experiences and offline resilience workflows introduced in Work Package 3.

---

## 2. Authentication & Authorization

All endpoints (except `/api/v1/auth/login` and `/api/v1/auth/register`) require an HTTP Bearer JWT token in the `Authorization` header:
```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```

---

## 3. Core Endpoint Specifications

### 3.1 Field Damage Assessment Intake
* **Method:** `POST`
* **Route:** `/api/v1/recovery/damage-assessments/field-inspection`
* **Authorized Roles:** `VOLUNTEER`, `GOVT`, `ADMIN`
* **Description:** Submits field damage assessment telemetry. Automatically tags record with `verification_status = 'PENDING_VERIFICATION'`.
* **Request Payload (`DamageAssessmentFieldCreate`):**
```json
{
  "incident_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "sector": "HEALTH",
  "facility_name": "Ward 4 Primary Health Subcentre",
  "damage_level": "MODERATE",
  "is_operational": false,
  "estimated_reconstruction_cost": 250000.0,
  "structural_notes": "Ground floor submerged up to 0.8 meters, backup generator damaged",
  "evidence_media_urls": [],
  "latitude": 13.0850,
  "longitude": 80.2750,
  "assessor_confidence": 95.0
}
```
* **Success Response (`201 Created`):**
```json
{
  "id": "asm-8921-uuid",
  "assessment_code": "ASM-2026-0042",
  "incident_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "sector": "HEALTH",
  "facility_name": "Ward 4 Primary Health Subcentre",
  "damage_level": "MODERATE",
  "is_operational": false,
  "estimated_reconstruction_cost": 250000.0,
  "verification_status": "PENDING_VERIFICATION",
  "assessor_confidence": 95.0,
  "assessed_at": "2026-11-18T00:00:00Z"
}
```

---

### 3.2 Field Damage Inspection Engineering Certification
* **Method:** `POST`
* **Route:** `/api/v1/recovery/damage-assessments/{assessment_id}/verify`
* **Authorized Roles:** `GOVT`, `ADMIN`
* **Description:** Statutory engineering certification gate. Certifies, disputes, or rejects volunteer damage assessments.
* **Request Payload (`DamageAssessmentVerifyRequest`):**
```json
{
  "action": "VERIFY",
  "verified_damage_level": "MODERATE",
  "engineering_notes": "Command Engineer certified field inspection on site."
}
```
* **Success Response (`200 OK`):**
```json
{
  "id": "asm-8921-uuid",
  "assessment_code": "ASM-2026-0042",
  "verification_status": "VERIFIED",
  "verified_damage_level": "MODERATE",
  "engineering_notes": "Command Engineer certified field inspection on site.",
  "verified_by_user_id": "usr-govt-001",
  "verified_at": "2026-11-18T00:05:00Z"
}
```

---

### 3.3 Multi-Agency Resource Requests Listing
* **Method:** `GET`
* **Route:** `/api/v1/resources/requests`
* **Authorized Roles:** `VOLUNTEER`, `NGO`, `GOVT`, `ADMIN`
* **Description:** Retrieves all submitted resource demands with incident contextual joins.
* **Success Response (`200 OK`):**
```json
[
  {
    "id": "req-9912-uuid",
    "incident_id": "inc-4411-uuid",
    "incident_title": "Shelter Drinking Water Deficit",
    "category": "WATER",
    "quantity_requested": 400,
    "quantity_fulfilled": 100,
    "priority": "HIGH",
    "status": "PENDING",
    "created_at": "2026-11-18T00:00:00Z"
  }
]
```

---

### 3.4 Community Recovery Summary Telemetry
* **Method:** `GET`
* **Route:** `/api/v1/recovery/monitoring/community-metrics/summary`
* **Authorized Roles:** `CITIZEN`, `VOLUNTEER`, `NGO`, `GOVT`, `ADMIN`
* **Description:** High-level municipal recovery indicators for citizen awareness and command oversight.
* **Success Response (`200 OK`):**
```json
{
  "total_wards_monitored": 15,
  "average_recovery_score": 84.5,
  "average_confidence": 91.2,
  "sector_restoration_averages": {
    "power": 90.0,
    "water": 85.0,
    "health": 80.0,
    "schools": 88.0,
    "livelihoods": 75.0
  },
  "total_active_shelters": 8,
  "total_remaining_displaced": 450,
  "freshness_distribution": {
    "FRESH": 12,
    "MODERATE": 3,
    "STALE_AMBER": 0,
    "EXPIRED_RED": 0
  }
}
```
