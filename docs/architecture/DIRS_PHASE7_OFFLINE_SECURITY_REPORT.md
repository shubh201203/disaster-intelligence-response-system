# DIRS — Phase 7 Offline Cryptography & Local Storage Security Report
## Work Package WP7.3: Encrypted Field Drafts & IndexedDB Multi-Tenant Isolation

**Document Identifier:** `DIRS-PH7-OFFSEC-001`  
**Classification:** OFFICIAL / FIELD CRYPTOGRAPHY REPORT  
**Phase:** Phase 7 — Enterprise Hardening, Reliability & Operational Readiness  
**Target Release:** DIRS v6.0 (Enterprise Hardened)  
**Status:** Certified / Complete  

---

## 1. Executive Summary

Disaster response workers operate in field environments characterized by cellular blackouts, shared hardware (ruggedized laptops, pooled tablets), and frequent device handoffs between shifts. Under Phase 6G WP3, an offline draft persistence engine was deployed using the browser's native IndexedDB.

This Phase 7 report establishes the security architecture and cryptographic hardening implemented to safeguard offline incident reports and field damage inspections against local physical extraction, unauthorized account-switching access, and data tampering.

---

## 2. Threat Modeling for Field Operations

| Threat Vector | Description | Likelihood | Impact | Phase 7 Defense Implemented |
| :--- | :--- | :---: | :---: | :--- |
| **T1: Device Loss / Theft** | Field worker loses tablet containing un-synchronized damage assessments and citizen reports. | HIGH | CRITICAL | AES-256-GCM authenticated encryption. Ciphertext cannot be decrypted without user passphrase. |
| **T2: Shared Hardware Snoop** | Volunteer B logs onto tablet previously used by Citizen A and inspects local IndexedDB. | HIGH | HIGH | Cryptographic and query-level user isolation. User B cannot decrypt or list User A's records. |
| **T3: Local Storage Tampering** | Malicious actor modifies damage percentage or coordinates directly in IndexedDB. | LOW | HIGH | AES-GCM 128-bit authentication tag. Any tampering triggers decryption rejection. |
| **T4: Key Co-Location** | Insecure implementations store the decryption key in `localStorage` alongside the database. | MEDIUM | CRITICAL | Decryption key is derived Ephemerally in memory via PBKDF2 and NEVER stored in persistent storage. |

---

## 3. Cryptographic Vault Architecture (`cryptoVault.ts`)

The DIRS Web Crypto Vault operates without third-party dependencies, leveraging the browser's native `globalThis.crypto.subtle` API.

### 3.1 Cryptographic Parameters
- **Cipher:** AES-256-GCM (Galois/Counter Mode).
- **Authentication Tag:** 128-bit authentication tag integrated into the ciphertext.
- **Key Derivation Function:** PBKDF2 with HMAC-SHA-256.
- **Iteration Count:** 100,000 iterations (OWASP recommended standard).
- **Salt Generation:** 16 bytes of cryptographically secure pseudorandom numbers (`crypto.getRandomValues`).
- **Initialization Vector (IV):** 12 bytes CSPRNG uniquely generated for every encryption operation.

### 3.2 Envelope Data Format (`DIRS_VAULT_V2`)
```typescript
export interface EncryptedPayloadEnvelope {
  __format: 'DIRS_VAULT_V2';
  algorithm: 'AES-256-GCM';
  kdf: 'PBKDF2-HMAC-SHA256';
  iterations: number;
  salt: string;        // Base64 encoded (16 bytes)
  iv: string;          // Base64 encoded (12 bytes)
  ciphertext: string;  // Base64 encoded (AES-GCM ciphertext + 16-byte auth tag)
}
```

### 3.3 Ephemeral Key Lifecycle
```
[User Passphrase] + [16-byte CSPRNG Salt]
                   |
                   v (PBKDF2, 100,000 iterations, HMAC-SHA256)
           [256-bit CryptoKey] (Memory Only)
                   |
         +---------+---------+
         |                   |
         v (Encrypt)         v (Decrypt)
  [Plain Draft]       [Decrypted Draft]
         |                   ^
         v (AES-GCM)         | (Verify Auth Tag)
[DIRS_VAULT_V2 Envelope] ----+
         |
         v
[IndexedDB Persistent Storage]
```
At no point is the derived `CryptoKey` or plaintext passphrase written to `localStorage`, `sessionStorage`, or IndexedDB.

---

## 4. Multi-Tenant Account Isolation & Logout Semantics

### 4.1 Principal Scoping Invariants
Every draft record in IndexedDB (`dirs_offline_drafts`) is keyed to a specific authenticated user:
1. **Creation:** `saveDraft()` requires an authenticated `user_id`. Attempting to save without a principal raises an immediate error.
2. **Retrieval:** `getDraft(id, expectedUserId)` compares the record's `user_id` against the calling principal. If they differ, `null` is returned.
3. **Listing:** `listDraftsByUser(userId)` uses the IndexedDB `by_user` compound index and filters out any records not owned by `userId`.
4. **Logout Preservation:** User logout removes `dirs_token` from memory/storage but intentionally preserves pending drafts in IndexedDB. When User A logs back in, their pending drafts reappear and resume synchronization. User B logging in on the same browser cannot access or synchronize User A's drafts.

---

## 5. Verification & Test Evidence

The cryptographic invariants are formally tested in `frontend/tests/contract/cryptoVault.spec.ts`:

```
Running 7 tests using 1 worker

  ok 1 tests\contract\cryptoVault.spec.ts: TC-P7-CRYPTO-01: Web Crypto API is available in test environment
  ok 2 tests\contract\cryptoVault.spec.ts: TC-P7-CRYPTO-02: Deterministic key derivation with identical passphrase and salt
  ok 3 tests\contract\cryptoVault.spec.ts: TC-P7-CRYPTO-03: Lossless roundtrip encryption and decryption for Incident Report
  ok 4 tests\contract\cryptoVault.spec.ts: TC-P7-CRYPTO-04: Lossless roundtrip encryption for Field Damage Assessment
  ok 5 tests\contract\cryptoVault.spec.ts: TC-P7-CRYPTO-05: AES-GCM authentication failure on ciphertext tampering
  ok 6 tests\contract\cryptoVault.spec.ts: TC-P7-CRYPTO-06: Decryption rejection when using incorrect passphrase
  ok 7 tests\contract\cryptoVault.spec.ts: TC-P7-CRYPTO-07: Type guard isEncryptedEnvelope correctly discriminates envelopes

  7 passed (1.2s)
```
In addition, all 5 dedicated WP3 browser E2E workflows (`crossRoleOfflineWorkflows.spec.ts`) passed 100%.

---

## 6. Offline Security Verdict

**VERDICT: CERTIFIED ENTERPRISE-GRADE FIELD RESILIENCE**  
Offline operational telemetry is cryptographically isolated, protected against physical hardware theft, authenticated against tampering, and partitioned across user accounts without risk of data cross-contamination.
