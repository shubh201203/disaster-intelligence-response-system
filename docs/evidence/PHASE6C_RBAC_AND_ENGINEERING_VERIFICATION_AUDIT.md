# DIRS Phase 6C — Role-Based Access Control & Engineering Verification Audit

**Audit Date:** 2026-11-16T01:58:45+05:30  
**Auditor Role:** Independent Security Auditor & Authorization Reviewer  
**Target Routes & Services:** `app/routers/recovery.py` and `app/recovery/services/damage_assessment_service.py`

---

## 1. Executive Summary

This audit assesses the server-side authorization enforcement governing Phase 6C damage assessment verification, field inspection submission, monotonic supersession, and needs ingestion.

**Key Findings:**
1. **Server-Side Enforcement**: All authorization controls are enforced server-side via FastAPI dependency injection (`require_role(...)` and `current_user.role` inspections). No reliance is placed on frontend or client-side checks.
2. **Denial Verification**: Requests by unauthorized roles (`CITIZEN`, `VOLUNTEER`, `NGO`) to restricted endpoints return genuine `HTTP 403 Forbidden` responses.
3. **Engineering Credential Granularity**: Authorization to certify, dispute, or reject damage assessments is granted to any user possessing `role = "GOVT"`. The current user schema does not feature an individual "licensed structural engineer" credential or specialized license attribute.

---

## 2. Server-Side RBAC Enforcement Matrix

| Endpoint | Ingestion / Action | Allowed Roles | Denied Roles (Tested) | Enforcement Mechanism | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `POST /damage-assessments/screen-image` | Tier-1 AI Screening | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | `CITIZEN` (HTTP 403) | `require_role(...)` dependency | **PASS** |
| `POST /damage-assessments/field-inspection` | Field Inspection Ingestion | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | `CITIZEN` (HTTP 403) | `current_user.role` check | **PASS** |
| `POST /damage-assessments/{id}/verify` | Engineering Verification | `GOVT`, `ADMIN` | `CITIZEN`, `VOLUNTEER`, `NGO` (HTTP 403) | `require_role("GOVT")` | **PASS** |
| `POST /damage-assessments/{id}/supersede` | Monotonic Reinspection ($V_k \to V_{k+1}$) | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | `CITIZEN` (HTTP 403) | `current_user.role` check | **PASS** |
| `GET /damage-assessments/{id}/history` | Lineage History | `GOVT`, `NGO`, `VOLUNTEER`, `ADMIN` | `CITIZEN` (HTTP 403) | `current_user.role` check | **PASS** |
| `POST /needs/structured` | Structured Needs Ingestion | `GOVT`, `NGO`, `ADMIN` | `CITIZEN`, `VOLUNTEER` (HTTP 403) | `current_user.role` check | **PASS** |
| `POST /reconciliation/reconcile-population` | Population Reconciliation | `GOVT`, `NGO`, `ADMIN` | `CITIZEN`, `VOLUNTEER` (HTTP 403) | `current_user.role` check | **PASS** |
| `GET /analytics/summary` | Situational Awareness | **PUBLIC (All Roles & Anonymous)** | None | No auth dependency (Public) | **PASS** |

---

## 3. Engineering Verification Gate Audit

### 3.1 Verification Logic & Actor Attribution
In `DamageAssessmentService.verify_damage_assessment` ([`damage_assessment_service.py`, lines 267-322](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services/damage_assessment_service.py#L267-L322)):
- **Action Validation**: Restricts input `action` strictly to `VERIFY`, `REJECT`, or `DISPUTE`. Invalid verbs trigger `HTTP 400 Bad Request`.
- **Actor Attribution**:
  - `asm.verified_by_id = verifier.id`
  - `asm.verified_at = datetime.now(timezone.utc)`
  - Verifier engineering comments are appended: `asm.structural_notes += f"\n[Engineering Review]: {data.engineering_notes}"`.
- **Audit Logging**:
  Instantiates `RecoveryOverrideLog` recording:
  - `user_id = verifier.id`
  - `action = f"ASSESSMENT_{action_upper}"`
  - `original_value = {"status": orig_status, "damage_level": orig_damage}`
  - `new_value = {"status": asm.verification_status, "damage_level": asm.damage_level}`
  - `justification_reason = data.engineering_notes`

### 3.2 Granularity of Engineering Credentials
In `backend/app/models/user.py`:
- `User.role` is an enumeration of `CITIZEN`, `VOLUNTEER`, `NGO`, `GOVT`.
- `VolunteerProfile` has `medical_certified`, `skills`, and `experience_years`.
- However, there is no `GovernmentProfile` or `engineering_license_number` column.
- Consequently, any user with `role = "GOVT"` (including general administrative staff) is granted verification authority by the system.

---

## 4. Assessment Version Supersession Audit

### 4.1 Monotonic Increment & Inactivation
In `DamageAssessmentService.supersede_assessment` ([`damage_assessment_service.py`, lines 329-399](file:///c:/Users/shubh/Downloads/DIRS/backend/app/recovery/services/damage_assessment_service.py#L329-L399)):
- **Precondition**: `old_asm.is_current_version` must be `True`. Attempting to supersede an already superseded record raises `HTTP 400 Bad Request`.
- **Version Number**: Monotonically increments: `new_version_num = old_asm.assessment_version + 1`.
- **Code Traceability**: New assessment code is formatted as `{old_asm.assessment_code}-V{new_version_num}`.
- **Deactivation**:
  - `old_asm.is_current_version = False`
  - `old_asm.superseded_by_id = new_asm.id`
  - `old_asm.reconciliation_status = "SUPERSEDED"`
- **Cluster Continuity**: Both records share the exact same `deduplication_cluster_id`.
- **Status Reset**: The newly created version starts as `verification_status = "PENDING_VERIFICATION"`, requiring fresh engineering certification before it is treated as verified.

---

## 5. Material Findings & Risk Assessment

- **Finding DEF-6C-RBAC-01 (Absence of Specific Engineering Credential Sub-Role)**:
  - *Location*: `backend/app/models/user.py` & `backend/app/routers/recovery.py` line 396.
  - *Severity*: **LOW (Architectural Granularity)**.
  - *Description*: Verification relies solely on `role == "GOVT"`. In a production municipal deployment, government users may include non-engineering administrative officers.
  - *Remediation Recommendation*: In Phase 7 or post-capstone hardening, introduce a `qualifications` JSON column or `IS_CERTIFIED_ENGINEER` boolean flag on government users to restrict engineering approvals to certified structural engineers.
