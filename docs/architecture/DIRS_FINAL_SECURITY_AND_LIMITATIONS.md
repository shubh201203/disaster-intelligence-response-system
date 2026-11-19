# DIRS — Definitive Final Security Review & System Limitations
## Disaster Intelligence and Response System (DIRS)

**Document Identifier:** `DIRS-CAPSTONE-SEC-006`  
**Classification:** OFFICIAL / AUDIT & SECURITY REVIEW  
**Target Release:** DIRS v5.2 (Capstone Release)  
**Parent Programme:** Phase 6G / Accelerated Work Package 4 (Capstone Packaging & Verification)  
**Publication Date:** November 18, 2026  
**Status:** Certified / Complete  

---

## 1. Executive Security & Privacy Overview

Disaster response software coordinates life-safety operations, municipal infrastructure, and emergency commodity distributions. Compromised access, data forgery, or privacy breaches in such systems can directly endanger field responders and displaced populations.

This security and privacy review audited:
1. **Authentication & Session Hygiene:** JWT issuance, token expiration, secret management.
2. **Authorization & Least-Privilege RBAC:** Route guards, endpoint security, role privilege boundaries.
3. **Multi-User Account Isolation on Shared Devices:** IndexedDB storage indices, store security violation guards, React Query memory cache partitioning.
4. **Data Ownership & Boundary Enforcement:** Citizen telemetry, volunteer field assessments, NGO logistics vs. statutory government restoration.
5. **SQL & Injection Protections:** SQLAlchemy parameter binding, zero raw SQL string interpolations.

---

## 2. Security Controls & Forensic Audit Findings

### 2.1 Verified Security Controls

| Control Domain | Architectural Implementation | Verification Method | Status |
| :--- | :--- | :--- | :---: |
| **Password Storage** | Bcrypt hashing with salted iterations (`get_password_hash`) in `backend/app/core/security.py`. Plaintext passwords never stored. | Unit test audit in `test_auth.py` | **VERIFIED** |
| **Token Authentication** | Signed JWT Bearer tokens with configurable expiration (`ACCESS_TOKEN_EXPIRE_MINUTES`). Decoded via `oauth2_scheme`. | TestClient authorization header tests | **VERIFIED** |
| **Endpoint RBAC** | `require_role(["GOVT", "ADMIN"])` dependency injection on sensitive endpoints (`POST /recovery/optimization/evaluate`, `POST /recovery/damage-assessments/{id}/verify`). | Parameterized 9-combination non-admin route denial matrix (`TC-E2E-38`) | **VERIFIED** |
| **Client Route Guards** | `<ProtectedRoute allowedRoles={[...]}>` wrapping in `App.tsx` preventing unauthorized client navigation. | Playwright E2E redirection suites | **VERIFIED** |
| **IndexedDB Multi-User Isolation** | Store-level verification throwing security violation errors if `expectedUserId` does not match `draft.user_id`. Read queries compound-indexed by `by_user_type`. | Automated contract tests in `crossRoleOffline.spec.ts` | **VERIFIED** |
| **React Query Cache Partitioning** | Dashboard views bind `user?.id` into query keys (`['resources-ngo', user?.id]`), eliminating cross-account state exposure on logout/login. | Contract test audit and inspection | **VERIFIED** |
| **Concurrency Locking** | Stock dispatch endpoint (`POST /resources/{id}/dispatch`) uses SQLAlchemy `with_for_update()` row locking. | Automated concurrency tests in `test_resources.py` | **VERIFIED** |
| **SQL Injection Prevention** | All ORM queries utilize SQLAlchemy 2.0 parameterized expressions (`select()`, `filter()`). Zero raw string concatenations in SQL queries. | Code inspection across `services/` | **VERIFIED** |

### 2.2 Security Findings & Risk Assessment

| # | Finding Description | Severity | Impacted Layer | Existing Mitigation | Remaining Operational Risk | Recommended Remediation |
| :-: | :--- | :---: | :---: | :--- | :--- | :--- |
| **SEC-01** | **Client-Side Secret Fallback in Config** | `LOW` | Backend Config | `app/config.py` uses fallback secret `"DIRS_SUPER_SECRET_KEY_CHANGE_IN_PRODUCTION"` if `SECRET_KEY` env var is absent. | In development, default key is utilized. In production without env var, predictable signature risk. | Phase 7: Enforce mandatory startup validation requiring high-entropy secret in production mode. |
| **SEC-02** | **At-Least-Once Re-dispatch Duplication** | `LOW` | Network Sync | Client idempotency guard blocks duplicate submission of `SYNCED` drafts. Field intake endpoints accept multiple reports as distinct telemetry. | If network drops after DB commit but before HTTP response, re-submission creates duplicate telemetry. | Acceptable in disaster observation; reconciled via Command Center triage (`POST /incidents/merge`). Phase 7: Add server `idempotency_keys` table. |
| **SEC-03** | **Unencrypted IndexedDB Draft Payloads** | `LOW` | Client Browser | IndexedDB drafts stored as structured JSON on browser storage partition. Protected by browser origin sandbox. | Physical seizure of unlocked device could expose local un-synced drafts. | Acceptable for field disaster reports. Phase 7: Implement Web Crypto API AES-GCM envelope encryption. |

---

## 3. Known System Limitations

The following limitations represent deliberate architectural scope boundaries of DIRS v5.2:

### 3.1 NGO Capital Infrastructure Pledges
* **Limitation:** The database schema contains no `ngo_pledges` table and no organization foreign key on `recovery_projects`.
* **Architectural Reality:** NGOs coordinate humanitarian relief commodities (`resources`), volunteer logistics, and emergency supplies. Statutory capital infrastructure reconstruction is administered exclusively by Government Command.
* **Integrity Guard:** Storing NGO pledges or organization tags in arbitrary text columns (e.g. `supplier_info`) is strictly prohibited. The UI displays the **Institutional Governance Notice** clarifying this policy.

### 3.2 Optimization Solver Execution Latency
* **Limitation:** The CP-SAT solver search limit is configured at 60 seconds (Tier 3) or 120 seconds (Tier 4). However, total end-to-end API response latency may reach ~176 seconds on dense graphs due to model instantiation, constraint posting, and post-solve reconciliation.
* **Interactive Suitability:** Tier 4 is not recommended for interactive synchronous UI requests.
* **Timeout Contract:** The frontend Axios client enforces an explicit `timeout: 130000ms` (130 seconds) matching Tier 1–3 operational contracts.

### 3.3 Git Repository Unverifiability
* **Limitation:** The project environment lacks a `.git` version control directory.
* **Verification Impact:** Git commit history, branches, and working-tree cleanliness cannot be verified using Git commands.
* **Mitigation:** Source integrity is audited via authoritative SHA-256 cryptographic manifests for all 23 Gate 2 baseline files and `task.md`.

### 3.4 Absence of Cloud-Hosted External Dependencies
* **Limitation:** Live external third-party services (e.g. live Twilio SMS gateways, production payment rails, live satellite imagery APIs) are not integrated.
* **Operational Mode:** All capabilities operate locally using calibrated synthetic telemetry and internal spatial indices.

---

## 4. Unsupported Workflows (Formally Deferred to Phase 7)

The following capabilities are **explicitly unsupported** in the current release:
1. **Phase 7 Enterprise Hardening:** Kubernetes Helm charts, automated cloud infrastructure provisioning (Terraform / AWS / GCP).
2. **Peer-to-Peer CRDT Data Replication:** Decentralized gossip protocols and Conflict-Free Replicated Data Types between mobile mesh devices.
3. **Automated Hardware TEE Attestation:** Hardware-backed Trusted Execution Environments (Intel SGX / ARM TrustZone) for cryptographic proof of compute.
4. **Production Microservice Decomposition:** Splitting the monolithic FastAPI architecture into independent microservices.
