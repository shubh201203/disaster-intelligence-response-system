# DIRS — Capstone Evidence Extraction: Security & Offline Architecture
## Module 07: Client Cryptographic Vault, Local Persistence, Server Defenses & Idempotency

**Document Identifier:** `DIRS-CAPSTONE-EVIDENCE-07`  
**Classification:** OFFICIAL / ACADEMIC CAPSTONE EVIDENCE  
**Degree Programme:** Bachelor of Technology (B.Tech) in Computer Science & Engineering  
**Institution:** VIT-AP University, Andhra Pradesh, India  
**Target Release:** DIRS v6.0 (Enterprise Hardened)  
**Audit Status:** STRICT READ-ONLY FORENSIC EXTRACTION  
**Evidence Sources:** `frontend/src/utils/offlineDraftStore.ts`, `frontend/src/utils/cryptoVault.ts`, `backend/app/core/idempotency.py`, `backend/app/main.py`  

---

## 1. Local-First Offline Resilience Architecture

To ensure zero operational data loss during disaster telecommunications blackouts, DIRS implements a **Local-First Offline Persistence Engine** combining the browser's native IndexedDB API with authenticated Web Crypto encryption.

### 1.1 IndexedDB Database & Object Store Schema
- **Database Name:** `dirs_offline_db`
- **Database Version:** `1`
- **Primary Object Store:** `dirs_offline_drafts` (KeyPath: `client_draft_id`)
- **Compound & Secondary Indices:**
  - `by_user`: Index on `user_id` (enforces strict multi-tenant isolation on shared devices).
  - `by_type`: Index on `workflow_type` (`INCIDENT_REPORT` | `FIELD_INSPECTION`).
  - `by_status`: Index on `sync_status` (`DRAFT`, `SYNCING`, `SYNCED`, `FAILED`, `CONFLICT`).
  - `by_user_type`: Compound index on `['user_id', 'workflow_type']`.

### 1.2 Offline Draft Finite State Machine (FSM)

```
       [User Edits Form]
               |
               v
           [ DRAFT ] <------------------+
               |                        |
        Network Restored?               | (Session Expired 401:
               |                        |  Preserve Draft for Re-Auth)
               v                        |
          [ SYNCING ] ------------------+
          /    |    \
         /     |     \
  HTTP 201  Network  HTTP 409
  Accepted  Dropped  Conflict
     /         |         \
    v          v          v
[ SYNCED ]  [ FAILED ]  [ CONFLICT ]
 (Server     (Retry      (Flagged for
  Ack Code)   Allowed)    Resolution)
```

1. **`DRAFT`:** Draft is created and encrypted locally in IndexedDB.
2. **`SYNCING`:** Network dispatch is initiated. The draft's `client_draft_id` is transmitted in the `Idempotency-Key` HTTP header.
3. **`SYNCED`:** Backend accepts the payload, returns HTTP 201, and issues an authoritative server UUID and code. The draft records `server_acknowledged_id`.
4. **`FAILED`:** If connectivity drops during transmission, the draft reverts to `FAILED` with an error message; the user can trigger manual or automatic retry.
5. **`CONFLICT`:** If the server detects a collision (HTTP 409), the state machine halts to prevent data overwrite.

---

## 2. Client-Side Web Crypto Authenticated Vault

- **Implementation Files:** `frontend/src/utils/cryptoVault.ts`, `frontend/src/utils/offlineDraftStore.ts`
- **Zero Third-Party Dependencies:** Relies exclusively on `globalThis.crypto.subtle` (W3C Web Cryptography Standard).

### 2.1 Cryptographic Parameters & Key Derivation
- **Cipher:** AES-256-GCM (Galois/Counter Mode with 128-bit authentication tag).
- **Initialization Vector (IV):** 12 bytes of cryptographically secure pseudorandom numbers (`crypto.getRandomValues`) generated uniquely for every encryption operation.
- **Key Derivation Function (KDF):** PBKDF2 with HMAC-SHA-256.
- **Iteration Count:** 100,000 iterations (OWASP recommended standard).
- **Salt Generation:** 16 bytes CSPRNG uniquely generated per draft envelope.

### 2.2 Envelope Data Format (`DIRS_VAULT_V2`)
When sensitive payloads (citizen casualty reports, structural damage estimates) are stored at rest, the payload column contains a structured envelope:
```json
{
  "__format": "DIRS_VAULT_V2",
  "algorithm": "AES-256-GCM",
  "kdf": "PBKDF2-HMAC-SHA256",
  "iterations": 100000,
  "salt": "base64_encoded_16_byte_salt",
  "iv": "base64_encoded_12_byte_iv",
  "ciphertext": "base64_encoded_ciphertext_and_128bit_auth_tag"
}
```

### 2.3 Ephemeral In-Memory Key Lifecycle & Anti-Theft Defense
A major design rule of DIRS is: **The encryption key is NEVER stored on disk beside the ciphertext.**
1. `sessionVaultKeys`: A private in-memory JavaScript `Map<string, CryptoKey>()` caches the derived key strictly in volatile execution memory.
2. **Device Theft / Inspection Defense:** If a field tablet is lost or inspected by an unauthorized person, inspecting the IndexedDB storage reveals only `DIRS_VAULT_V2` ciphertext. Without the user's passphrase, the ciphertext cannot be decrypted.
3. **Browser Reload / Process Restart:** When the browser tab closes or reloads, memory is wiped. The encrypted drafts remain preserved in IndexedDB with status `VAULT_LOCKED` until the user re-enters their passphrase via `unlockVault(passphrase)`.
4. **Tamper Detection & Safe Failure:** If an attacker modifies the ciphertext or IV in IndexedDB, the AES-GCM MAC tag validation fails upon decryption. The store catches the error, marks `sync_error: 'DECRYPTION_FAILED'`, and **never silently deletes or discards the draft**.
5. **Lossless Coexistence with Plaintext (v1) Drafts:** Unencrypted legacy drafts lacking `DIRS_VAULT_V2` are recognized by `isEncryptedEnvelope()` and returned directly, ensuring zero data loss during version upgrades.

---

## 3. Server-Side Defense-in-Depth

### 3.1 Production Fail-Closed Secret Validation (`backend/app/config.py`)
Under Phase 7, DIRS enforces fail-closed startup validation using Pydantic v2 `@model_validator(mode="after")`. In `production` or `staging` environments:
- The backend raises `RuntimeError` and **refuses to start** if `SECRET_KEY` equals the development default or is less than 32 characters long.
- The backend raises `RuntimeError` if `BENEFICIARY_HASH_SALT` is less than 16 characters long.

### 3.2 Content Security Policy & Security Headers (`backend/app/main.py`)
Injected via `security_headers_middleware`:
- **Content-Security-Policy (CSP):**
  ```http
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org; connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:* wss: https:; font-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'
  ```
- **Clickjacking Protection:** `X-Frame-Options: DENY` and `frame-ancestors 'none'`.
- **MIME Sniffing Prevention:** `X-Content-Type-Options: nosniff`.
- **Referrer Policy:** `Referrer-Policy: strict-origin-when-cross-origin`.
- **Obsolete Header Disabled:** `X-XSS-Protection: 0` (modern OWASP recommendation disabling buggy legacy auditors in favor of CSP).
- **Transport Security:** `Strict-Transport-Security: max-age=31536000; includeSubDomains` on HTTPS.

### 3.3 Strict CORS Origin Whitelist (`backend/app/main.py`)
Replaces insecure wildcard CORS (`*`) with an explicit origin array matching W3C Fetch Section 3.2.2:
```python
allowed_origins = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://testserver"
]
```

### 3.4 ASGI Request Payload Limiter (`backend/app/main.py`)
Protects against denial-of-service via oversized uploads:
1. Validates `Content-Length` against `settings.MAX_REQUEST_BODY_BYTES` (10MB default).
2. For chunked or streaming uploads lacking `Content-Length`, wraps `request.receive` at the ASGI level to count incoming body bytes dynamically, rejecting oversized streams with `HTTP 413 Payload Too Large`.

---

## 4. Server-Side Idempotency Service

- **Implementation File:** `backend/app/core/idempotency.py`
- **Integrated Endpoints:** `POST /api/v1/incidents`, `POST /api/v1/recovery/damage-assessments/field-inspection`

### 4.1 Deduplication Architecture & Collision Detection
1. **Composite Scoping:** Keys are partitioned by `(user_id, endpoint, idempotency_key)` to prevent cross-tenant key pollution.
2. **SHA-256 Fingerprinting:** Evaluates $\text{SHA-256}(\text{Canonical JSON}(\text{payload}))$. If a client reuses an idempotency key with different data, the system rejects it with `HTTP 409 Conflict` (Payload Collision).
3. **In-Progress Concurrency Lock:** Parallel duplicate requests arriving while the first request is executing are rejected with `HTTP 409 Conflict` (Lock Active).
4. **WebSocket Broadcast Isolation:** Event broadcasting is isolated so that a dropped WebSocket client connection cannot fail the HTTP transaction or release the idempotency lock after the database commit has already succeeded.

### 4.2 Formal Operational Classification
- **Process-Local Protection:** **VERIFIED** (Thread-safe memory locking and replay within a single server process).
- **Multi-Worker Protection:** **NOT SUPPORTED** (Without Redis, uvicorn worker processes cannot share memory state).
- **Restart-Persistent Protection:** **NOT SUPPORTED** (In-memory storage clears on reboot).
- **Transactionally Durable Protection:** **NOT SUPPORTED** (Requires database migration for dedicated idempotency table, which is prohibited against the frozen database).
