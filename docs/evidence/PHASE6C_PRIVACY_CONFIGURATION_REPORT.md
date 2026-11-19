# DIRS Phase 6C — Privacy Configuration & Fail-Closed Secret Security Report

**Audit Target:** DEF-6C-SEC-01 Remediation Verification  
**Source Files Audited:** `backend/app/config.py` and `backend/app/core/security.py`  
**Test Suite:** `tests/backend/test_phase6c_damage_needs.py::test_beneficiary_hash_salt_missing_fails_closed`

---

## 1. Executive Summary

DEF-6C-SEC-01 eliminated the security risk posed by having an insecure, hardcoded default salt for beneficiary pseudonymization. 

The remediation implemented a strict **Fail-Closed Security Model**:
- Removed the static fallback string from `backend/app/config.py`.
- Updated `hash_beneficiary_id` in `backend/app/core/security.py` to raise a `RuntimeError` immediately if `BENEFICIARY_HASH_SALT` is empty, missing, or whitespace.
- Prevents unkeyed hashing or predictable rainbow-table attacks across multi-tenant or multi-environment deployments.
- Confirmed that deterministic pseudonymization is maintained when a stable secret is supplied.

---

## 2. Source Code Changes

### 2.1 Configuration Layer (`backend/app/config.py`)
```python
# Before (Vulnerable)
BENEFICIARY_HASH_SALT: str = os.getenv(
    "BENEFICIARY_HASH_SALT", "dirs_recovery_salt_k9x2m8q4_secure"
)

# After (Remediated)
BENEFICIARY_HASH_SALT: str = os.getenv("BENEFICIARY_HASH_SALT", "")
```

### 2.2 Security Hashing Function (`backend/app/core/security.py`)
```python
# Before (Vulnerable)
def hash_beneficiary_id(raw_id: str) -> str:
  if not raw_id:
    return ""
  salt = getattr(
      settings, "BENEFICIARY_HASH_SALT", "dirs_recovery_salt_k9x2m8q4_secure"
  )
  salted_input = f"{salt}:{raw_id.strip()}:{salt}"
  return hashlib.sha256(salted_input.encode("utf-8")).hexdigest()


# After (Remediated - Fail Closed)
def hash_beneficiary_id(raw_id: str) -> str:
  """Computes a cryptographic salted SHA-256 pseudonymized hash of sensitive

  national/household beneficiary ID.

  Requires settings.BENEFICIARY_HASH_SALT to be explicitly configured.
  Fails closed if the salt is absent or unconfigured. Insecure fallbacks are
  strictly disabled.
  """
  if not raw_id:
    return ""
  salt = getattr(settings, "BENEFICIARY_HASH_SALT", "") or os.getenv(
      "BENEFICIARY_HASH_SALT", ""
  )
  if not salt or not str(salt).strip():
    raise RuntimeError(
        "CRITICAL SECURITY CONFIGURATION ERROR: BENEFICIARY_HASH_SALT is not"
        " configured. Beneficiary pseudonymization requires an explicitly"
        " configured secret salt. Insecure default fallbacks are disabled."
    )
  salted_input = f"{str(salt).strip()}:{raw_id.strip()}:{str(salt).strip()}"
  return hashlib.sha256(salted_input.encode("utf-8")).hexdigest()
```

---

## 3. Secret Lifecycle, Persistence & Rotation Policy

1. **Environment Configuration**: `BENEFICIARY_HASH_SALT` must be defined in the production container environment or `.env` file prior to service launch.
2. **Persistence Across Restarts**: As an environment-level configuration, the salt remains stable across process reboots, ensuring that beneficiary IDs hashed on Day 1 will match the hash of identical beneficiaries submitted on Day 30.
3. **Rotation Implications**:
   > [!IMPORTANT]
   > Changing or rotating `BENEFICIARY_HASH_SALT` will alter the SHA-256 digest of all subsequent beneficiary IDs. This would prevent the system from recognizing duplicate claims across records created prior to rotation. Therefore, automatic secret rotation is **strictly prohibited**. In the event of a key compromise requiring rotation, a database migration script must be executed to re-hash legacy records using the new key.
4. **Legal / Technical Distinction**: The process represents deterministic **cryptographic pseudonymization** under GDPR Article 4(5), not irreversible anonymization, as knowledge of the salt and an individual's ID enables matching.

---

## 4. Automated Regression Verification

The fail-closed mechanism was validated by `test_beneficiary_hash_salt_missing_fails_closed`:
- Unsetting `BENEFICIARY_HASH_SALT` via pytest `monkeypatch` caused `hash_beneficiary_id` to raise `RuntimeError("CRITICAL SECURITY CONFIGURATION ERROR...")`.
- Setting a valid salt produced deterministic, repeatable 64-character SHA-256 digests.

**Test Status**: **PASSED in 0.05s**.
