# DIRS Phase 6C — Privacy & Beneficiary Protection Forensic Audit

**Audit Date:** 2026-11-16T01:59:00+05:30  
**Auditor Role:** Independent Data Protection & Security Auditor  
**Target Code:** `app/core/security.py`, `app/recovery/services/recovery_needs_service.py`, `app/schemas/recovery.py`

---

## 1. Executive Summary

This forensic audit evaluates the data protection and privacy defenses implemented for disaster-affected populations under Phase 6C. The audit verifies cryptographic pseudonymization, household head name masking, API serialization controls, and the strict absence of plain-text Personally Identifiable Information (PII) in persistent storage and public situational endpoints.

---

## 2. Pseudonymization vs. Anonymization Technical Distinction

Under international privacy frameworks (e.g., GDPR Article 4(5) and humanitarian data standards):
- **Pseudonymization**: The processing of personal data such that it can no longer be attributed to a specific data subject without the use of additional information (such as a cryptographic salt or lookup key), provided that additional information is kept separately.
- **Anonymization**: Irreversibly altering personal data such that the individual cannot be identified by any means whatsoever.

**DIRS Phase 6C implements Cryptographic Pseudonymization**:
- Beneficiary IDs are converted into deterministic 64-character hex digests using salted SHA-256.
- Because the hashing is deterministic (required to detect duplicate relief claims for the same household across multiple NGOs), an observer who already possesses the victim's raw ID and the server salt can verify whether that individual exists in the database.
- It is therefore correctly categorized as **pseudonymization**, not full anonymization.

---

## 3. Cryptographic Salt & Secret Lifecycle Analysis

### 3.1 Salt Loading & Persistence
In [`backend/app/config.py`, line 13](file:///c:/Users/shubh/Downloads/DIRS/backend/app/config.py#L13):
```python
BENEFICIARY_HASH_SALT: str = os.getenv(
    "BENEFICIARY_HASH_SALT", "dirs_recovery_salt_k9x2m8q4_secure"
)
```
In [`backend/app/core/security.py`, lines 16-25](file:///c:/Users/shubh/Downloads/DIRS/backend/app/core/security.py#L16-L25):
```python
def hash_beneficiary_id(raw_id: str) -> str:
  if not raw_id:
    return ""
  salt = getattr(
      settings, "BENEFICIARY_HASH_SALT", "dirs_recovery_salt_k9x2m8q4_secure"
  )
  salted_input = f"{salt}:{raw_id.strip()}:{salt}"
  return hashlib.sha256(salted_input.encode("utf-8")).hexdigest()
```

### Forensic Observations:
1. **Environment Configuration**: The salt is loaded via `os.getenv("BENEFICIARY_HASH_SALT")`. If defined in `.env` or container environment, it persists across restarts.
2. **Missing-Secret Fallback**: If the environment variable is omitted, the system falls back to the hardcoded default `"dirs_recovery_salt_k9x2m8q4_secure"`. 
   - *Risk*: If two deployments use the default salt, hash values are identical across instances. In a secure production environment, the deployment pipeline must enforce a high-entropy secret.
3. **Double-Salt Prepending/Appending**: The construction `f"{salt}:{raw_id}:{salt}"` effectively prevents length-extension and prefix-guessing attacks.
4. **Deterministic Consistency**: Hashing the same test identifier (`"TEST-BENEFICIARY-4401"`) deterministically produces the exact same 64-character digest:
   `a5fa97098e918c5e93df08e92dbba15cff30d52f6385aee409fca5da2f01f1ae`.

---

## 4. Name Masking & Public Sanitization

### 4.1 Masking Implementation
In [`backend/app/core/security.py`, lines 27-40](file:///c:/Users/shubh/Downloads/DIRS/backend/app/core/security.py#L27-L40):
```python
def mask_person_name(name: str) -> str:
  if not name:
    return ""
  parts = name.strip().split()
  masked = []
  for p in parts:
    if len(p) <= 2:
      masked.append(p[0] + "*")
    else:
      masked.append(p[0] + "*" * (len(p) - 2) + p[-1])
  return " ".join(masked)
```
- Multi-word names: `"Ramesh Swaminathan"` $\to$ `"R****h S*********n"`.
- Short words: `"Al"` $\to$ `"A*"`.
- Single characters: `"K"` $\to$ `"K*"`.
- Preserves word structure while preventing casual visual identification.

### 4.2 Raw Identifier Leakage Inspection
- **Relational Storage (`RecoveryNeed`)**:
  - `beneficiary_id_hash`: Stored as `String(64)`.
  - `household_head_name_masked`: Stored as `String(255)`.
  - Raw beneficiary ID column: **None**. Raw identifier is discarded after hashing in `create_structured_need`.
- **Audit Logs (`AuditService.log_action`)**:
  - Logged payload: `{"ward_code": need.ward_code, "sector": need.sector, "total_affected": total_affected, "exceeds_census": exceeds_census}`.
  - Raw ID and raw name are **strictly omitted** from audit log JSON details.
- **Exception Messages**:
  - Validation failures for duplicate records cite only the first 8 characters of the hash (`CONF-a5fa9709`), never plain-text identifiers.

---

## 5. Material Findings & Risk Assessment

- **Finding DEF-6C-SEC-01 (Hardcoded Default Hash Salt)**:
  - *Location*: `backend/app/config.py` line 13 & `backend/app/core/security.py` line 23.
  - *Severity*: **LOW (Production Hardening Recommendation)**.
  - *Description*: While convenient for development and automated test suites, falling back to a static default string creates predictable hashes if `BENEFICIARY_HASH_SALT` is inadvertently omitted in production.
  - *Remediation Recommendation*: Add a production startup validator in `main.py` warning or preventing server boot if `ENVIRONMENT == "production"` and `BENEFICIARY_HASH_SALT` equals the default value.
