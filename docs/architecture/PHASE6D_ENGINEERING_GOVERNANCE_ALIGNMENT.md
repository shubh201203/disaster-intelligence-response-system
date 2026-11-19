# DIRS Phase 6D-A — DEF-6D-07: Engineering Governance & Credential Terminology
## Reconciliation with Phase 6C Limitations, Accurate Role Scoping, and License Validation Boundaries

**Document ID:** `DIRS-PHASE6D-DOC-20`  
**Classification:** SYSTEM GOVERNANCE & ACCESS CONTROL AUDIT  
**Lead Authors:** Principal Systems Security Architect & Forensic Software Auditor  
**Date:** November 16, 2026  
**Status:** COMPLETE & SEALED  

---

## 1. Context & Remediation Purpose (DEF-6D-07)

During Phase 6C, an explicit Credential Limitation Notice was established (**DEF-6C-RBAC-01** in `docs/PHASE6C_DAMAGE_ASSESSMENT_REPORT.md` and `docs/PHASE6C_REMEDIATION_REPORT.md`). 

**Audit Finding (DEF-6D-07):**
In certain sections of early Phase 6D-A documentation, phrases such as "certified licensed structural engineer verification" or "structural engineer authorization gate" were used to describe the verification of damage assessments and project tiers.

**Remediation Mandate:**
- All Phase 6D documentation and runtime descriptions must strictly adhere to verified system reality:
  1. The DIRS RBAC system checks `user.role == "GOVT"`.
  2. The platform executes an **engineering verification workflow**, but **statutory professional license validation is NOT implemented**.
  3. Holding a `GOVT` account does **not** cryptographically or statutorily prove that the individual is a licensed civil, structural, or geotechnical engineer.
  4. Precise, legally defensible terminology must be used across all documents.

---

## 2. Accurate Architectural Terminology Lexicon

The following terms are standardized and enforced across all DIRS Phase 6 recovery modules:

| Prohibited / Inaccurate Term | Mandatory Approved Term | Technical Scope & System Reality |
| :--- | :--- | :--- |
| *"Licensed Structural Engineer verification"* | **Government-role verification** (`role == "GOVT"`) | The API checks that the user account possesses the `GOVT` role. It does not query a state engineering council licensing database. |
| *"Certified engineering sign-off"* | **Engineering verification workflow** | The multi-stage software workflow in DIRS wherein a designated government inspector reviews photos, CV screening tags, and cost estimates before marking `verification_status = "VERIFIED"`. |
| *"Statutory structural license validation"* | **Professional license validation (Not Implemented)** | Out of scope for capstone runtime; external verification against professional licensing bodies (e.g., Council of Engineers, PEC, AICTE) is documented as a future enterprise integration. |
| *"Autonomous engineering override"* | **Attributed government administrative override** | An authorized government user (`GOVT`) altering an automated solver output or project tier, with mandatory justification and IP audit logging in `RecoveryOverrideLog`. |

---

## 3. The Three-Tier Provenance Hierarchy

To maintain complete transparency regarding field data credibility, DIRS organizes all damage assessments and recovery needs into three provenance tiers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DIRS THREE-TIER PROVENANCE ARCHITECTURE                         │
└────────────────────────────────────────────────────────────────────────────────────────┘

  TIER 1: CROWDSOURCED & UNVERIFIED FIELD REPORTS
  ───────────────────────────────────────────────
  - Provenance Code: `TIER_1_UNVERIFIED_CROWD`
  - Submitter: Citizen portal (`role == "CITIZEN"`), field volunteers (`role == "VOLUNTEER"`).
  - Authority: Informational screening only. Cannot trigger Tier 1 mandatory capital allocation.
  - System Weight: Source reliability R_src = 0.50.

  TIER 2: GOVERNMENT-ROLE FIELD INSPECTION (ACTIVE DIRS BASELINE)
  ──────────────────────────────────────────────────────────────
  - Provenance Code: `TIER_2_GOVT_OFFICIAL`
  - Submitter: Registered municipal or departmental official (`role == "GOVT"`).
  - Authority: Legally authorized within DIRS to verify damage, validate needs, and sanction 
    project portfolios for optimization scheduling.
  - System Weight: Source reliability R_src = 0.85.
  - System Limitation: Confirms official departmental status; does not validate professional 
    structural engineering licensure.

  TIER 3: THIRD-PARTY CERTIFIED STRUCTURAL AUDIT (FUTURE SPECIFICATION)
  ────────────────────────────────────────────────────────────────────
  - Provenance Code: `TIER_3_CERTIFIED_ENGINEER`
  - Submitter: External accredited structural engineering firm with statutory license token.
  - Authority: Gold-standard forensic structural safety evaluation.
  - System Weight: Source reliability R_src = 1.00.
  - System Limitation: Schema-ready in Phase 6B; cryptographic PKI licensing validation is 
    not implemented in capstone baseline.
```

---

## 4. Verification Workflow Security & Audit Trail

When a recovery assessment or project schedule is approved:
1. **Authentication Check:** Validates JWT access token and claims `user.role in ("GOVT", "ADMIN")`.
2. **State Transition Gate:**
   - Assessment: `PENDING_VERIFICATION` $\to$ `VERIFIED`
   - Project: `PROPOSED` $\to$ `APPROVED`
3. **Audit Immutability:**
   Every approval writes an immutable record to `recovery_override_logs`:
   ```python
   override_log = RecoveryOverrideLog(
       project_id=project.id,
       user_id=current_user.id,
       action="PROJECT_APPROVE",
       original_value={"status": "PROPOSED"},
       new_value={
           "status": "APPROVED",
           "sanction_order": sanction_order_number,
       },
       justification_reason=justification,
       ip_address=request.client.host,
       timestamp=datetime.now(timezone.utc),
   )
```
4. **Transparency Notice:** All generated PDF and UI manifests include the explicit statement:
   > *"Approved via DIRS Government Administrative Verification Workflow. Professional structural licensure is the statutory responsibility of the sponsoring department."*

---
*End of DIRS Phase 6D-A DEF-6D-07 Remediation Document.*
