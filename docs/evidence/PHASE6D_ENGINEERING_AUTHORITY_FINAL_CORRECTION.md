# DIRS Phase 6D-A — DEF-6D-10: Engineering Authority & Workflow Qualification
## Reconciliation of Platform RBAC, Authorized Evidence Pathways, and Licensure Demarcation

**Document ID:** `DIRS-PHASE6D-DOC-24`  
**Classification:** SYSTEM GOVERNANCE & ACCESS CONTROL AUDIT  
**Lead Authors:** Principal Systems Security Architect & Forensic Software Auditor  
**Date:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Executive Summary & Defect Remediation (DEF-6D-10)

In early architectural drafts, the phrase "structural engineer certification" was used interchangeably with "government verification."

**Audit Finding (DEF-6D-10):**
In Phase 6C (specifically **DEF-6C-RBAC-01**), an explicit credential boundary was established:
- The DIRS backend enforces `current_user.role == "GOVT"`.
- The system **does NOT connect to any external statutory board or licensing registry** (e.g., Council of Architecture, Institution of Engineers, State Licensing Boards) to validate that the user is a certified or licensed civil/structural engineer.
- Describing a `GOVT` user approval as a "licensed structural engineer certification" is legally inaccurate and technically unfounded.

**Remediation Mandate:**
1. **Preserve Phase 6C RBAC Unchanged:** Zero modifications to existing JWT role definitions or database schemas.
2. **Accurate Terminology:** A `GOVT` account verification confers **Government Administrative Workflow Approval**, not statutory structural engineering certification.
3. **Authorized Evidence Pathway for Tier 1:** Establish an explicit multi-step evidence pathway for Tier 1 life-safety classification.
4. **Flagging Mechanism:** Where certified professional structural assessments are unavailable, the system flags the project as `FLAG_QUALIFIED_STRUCTURAL_AUDIT_REQUIRED` rather than fabricating certification.

---

## 2. Authorized Evidence Pathway for Tier 1 Life-Safety Scheduling

Because an automated solver must not schedule millions of rupees based on speculative claims, projects can only enter `TIER_1_MANDATORY` through an explicit, auditable three-step evidence chain:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        TIER 1 AUTHORIZED EVIDENCE PATHWAY                              │
└────────────────────────────────────────────────────────────────────────────────────────┘

  STEP 1: FIELD INSPECTION & OBSERVATIONAL EVIDENCE
  ─────────────────────────────────────────────────
  - Evidence: High-resolution photographic evidence stored in `evidence_media_urls`.
  - Preliminary Tagging: Computer Vision damage screening (`cv_damage_assessments.id`).
  - Recorded Damage: Categorical damage must be explicitly marked `DESTROYED` or `SEVERE`.

  STEP 2: GOVERNMENT ADMINISTRATIVE VERIFICATION GATE
  ──────────────────────────────────────────────────
  - Actor: Authorized platform user with `role == "GOVT"`.
  - Action: Reviews photos, CV tags, and field notes.
  - State Transition: `verification_status` updated from `PENDING_VERIFICATION` to `VERIFIED`.
  - Database Audit: `verified_by_id = user.id`, `verified_at = timestamp`.
  - System Scope: Certifies that the report originates from a recognized municipal official.

  STEP 3: TIER 1 SAFETY CLASSIFICATION AUDIT
  ──────────────────────────────────────────
  - Threshold Condition: S_{L, j} ≥ 0.85 AND verification_status == "VERIFIED".
  - If External Structural Report Attached:
    - User attaches accredited inspection certificate number to `sanction_order_number`.
    - Flag: `STRUCTURAL_ENGINEERING_REPORT_ATTACHED`.
  - If External Structural Report NOT Attached:
    - Flag: `TIER_1_PROVISIONAL_PENDING_LICENSED_INSPECTION`.
    - System Action: Schedules project in proposed recovery portfolio, but places 
      contract disbursement on administrative hold until a qualified structural engineer 
      signs off on physical site shoring.
```

---

## 3. Demarcation of System Reality vs. Future Integration

| Capability Dimension | Live DIRS Platform Baseline (Phase 1–6C) | Future Enterprise Target (Post-Capstone) |
| :--- | :--- | :--- |
| **Authentication Check** | `current_user.role in ("GOVT", "ADMIN")` | PKI Smart-Card or e-Sign with National Engineering Registry. |
| **Verification Scope** | Verifies administrative validity of municipal field inspection. | Cryptographically validates active license status and disciplinary standing. |
| **Audit Logging** | Writes user ID, IP address, and timestamp to `RecoveryOverrideLog`. | Appends cryptographically signed PDF certificate to immutably hashed ledger. |
| **Legal Representation** | Departmental administrative sanction order. | Statutory civil liability seal under National Building Code. |

---

## 4. Preservation of Phase 6C RBAC Security

The remediation enforces these standards through **strict terminology and workflow gates** without touching code or database schemas:
- No new database columns or tables are created.
- Existing `role` enums (`GOVT`, `VOLUNTEER`, `CITIZEN`, `NGO`, `ADMIN`) remain identical.
- All public reports, APIs, and generated manifests will display the notice:
  > *"Verified by authorized Government Administrative User. Professional engineering licensure is not verified by this platform."*

---
*End of DIRS Phase 6D-A DEF-6D-10 Remediation Document.*
