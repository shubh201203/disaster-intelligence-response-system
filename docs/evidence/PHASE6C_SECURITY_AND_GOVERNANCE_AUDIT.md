# DIRS Phase 6C — Security, Governance & Human-in-the-Loop Audit

## 1. Governance Objectives & Human-in-the-Loop Safeguards

In safety-critical disaster intelligence, machine-learning predictions must never autonomously trigger high-stakes interventions. Phase 6C enforces strict human-in-the-loop governance:
- **No Autonomous Structural Condemnation**: The output of the Phase 3B ResNet18/Random Forest CV classifier is strictly marked as `PENDING_VERIFICATION` and `is_screened_only = true`.
- **Engineering Verification Gate**: Only certified Government Structural Engineers (`role = "GOVT"`) possess the authorization to certify or escalate damage classifications. Attempts by unauthorized actors (`CITIZEN`, `VOLUNTEER`) are rejected with HTTP 403 Forbidden.
- **Statutory Warning Banner**: Every API response returning AI screening outputs includes an immutable disclaimer prohibiting direct contractual, financial, or legal reliance on automated inference.

---

## 2. Role-Based Access Control (RBAC) Matrix

| Endpoint | CITIZEN | VOLUNTEER | NGO | GOVT | ADMIN | Enforcement Mechanism |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `POST /damage-assessments/screen-image` | Denied | **Allowed** | **Allowed** | **Allowed** | **Allowed** | `require_role("GOVT", "NGO", "VOLUNTEER", "ADMIN")` |
| `POST /damage-assessments/field-inspection` | Denied | **Allowed** | **Allowed** | **Allowed** | **Allowed** | `require_role("GOVT", "NGO", "VOLUNTEER", "ADMIN")` |
| `POST /damage-assessments/{id}/verify` | Denied | Denied | Denied | **Allowed** | **Allowed** | `require_role("GOVT")` |
| `POST /damage-assessments/{id}/supersede` | Denied | **Allowed** | **Allowed** | **Allowed** | **Allowed** | Re-inspection allowed; requires verification |
| `POST /needs/structured` | Denied | Denied | **Allowed** | **Allowed** | **Allowed** | Household needs ingestion restricted |
| `POST /reconciliation/reconcile-population` | Denied | Denied | **Allowed** | **Allowed** | **Allowed** | Population analytics restricted |
| `GET /spatial/*` (Radius, BBox, Summary) | Denied | **Allowed** | **Allowed** | **Allowed** | **Allowed** | Operational spatial intelligence |
| `GET /analytics/summary` | **Allowed** | **Allowed** | **Allowed** | **Allowed** | **Allowed** | Public endpoint (Scrubbed PII) |

---

## 3. Privacy Preservation & PII Defense

### 3.1 Salted Cryptographic Beneficiary Hashing
Beneficiary identification numbers (e.g., Aadhaar cards, voter IDs, ration cards) are vulnerable to identity theft and unauthorized tracking. Phase 6C strictly implements:
- Server-side salted SHA-256 hashing using the application salt (`dirs_recovery_secret_salt_2026`).
- The raw beneficiary ID is rejected from persistence layers and never logged in plain text.
- Even if the primary database is compromised, beneficiary IDs cannot be reversed via dictionary or rainbow-table attacks.

### 3.2 Household Name Masking
Names of household heads are pseudonymized on ingestion:
- `"Kavitha Murugesan"` $\to$ `"K***n"`
- `"Sundararajan"` $\to$ `"S***n"`
- Single-letter or two-letter strings are masked as `"*"` to prevent deanonymization.

### 3.3 Public Situation Dashboard Scrubbing
The `/api/v1/recovery/analytics/summary` endpoint is fully public and requires no authentication token. To protect affected populations:
- Excludes all individual facility names, inspector names, verifier notes, and household identifiers.
- Excludes unverified AI screening claims.
- Delivers only aggregated sector counts, verified operational status percentages, and ward-level summary indicators.

---

## 4. Immutable Audit Logging & Supersession Integrity

Every state-altering operation is permanently logged to `RecoveryOverrideLog` and `AuditLog`:
1. **Verification Overrides**: Records inspector identity, engineer verifier identity, original damage assessment, verified damage assessment, and engineering justification.
2. **Supersession Lineage**: When record $V_k$ is superseded by $V_{k+1}$, the previous record is frozen (`is_current_version = false`, `reconciliation_status = "SUPERSEDED"`). The override log records the transition timestamp, justification reason, and cost variance.
3. **Database Integrity**: All audit logs are append-only. No `DELETE` or `UPDATE` triggers are exposed on audit tables.
