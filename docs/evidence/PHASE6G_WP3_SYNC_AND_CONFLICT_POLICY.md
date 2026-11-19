# DIRS Phase 6G Accelerated Programme: Work Package 3
# Synchronization & Conflict Resolution Policy Specification

**Document Identifier:** `DIRS-PH6G-WP3-SYNC-POLICY-003`  
**Security Classification:** OFFICIAL / SENSITIVE  
**Target Release:** DIRS v5.2  
**Parent Roadmap Phase:** Phase 6G — Cross-Role UI Integration, E2E Verification & Capstone Forensic Closure  
**Status:** Certified / Completed  

---

## 1. Guiding Principles & Zero-Fabrication Mandate

Offline data synchronization in disaster response entails unique operational risks. Conflicting field reports, outdated assessments, or network drops must not lead to silent data destruction or fabricated compromise values.

The DIRS Phase 6G WP3 synchronization engine enforces five mandatory principles:

1. **Local-First Safety:** Form data is persisted to client-side storage before any network dispatch is attempted.
2. **Deterministic Status Lifecycle:** Every draft occupies exactly one state in the finite state machine (`DRAFT`, `SYNCING`, `SYNCED`, `FAILED`, `CONFLICT`).
3. **No Silent Overwrites:** Server state is never unilaterally overwritten by outdated client timestamps.
4. **Preservation on Auth Failure:** An expired JWT token (`HTTP 401`) never invalidates, deletes, or purges client drafts.
5. **Auditable Transition Records:** All synchronization attempts record timestamp, error code, and server acknowledgement identifiers.

---

## 2. HTTP Status Code Handling Policy

| HTTP Response Code | State Transition | Policy & Client Behavior |
| :--- | :--- | :--- |
| **`200 OK` / `201 Created`** | `SYNCING` $\to$ `SYNCED` | Payload acknowledged by backend. Record `server_assigned_id`. Clear `sync_error`. Draft is retained in `SYNCED` state until operator clicks "Clear Completed" or manually purges. |
| **`400 Bad Request`** | `SYNCING` $\to$ `FAILED` | Malformed request. Record server error detail in `sync_error`. Preserve payload in IndexedDB. Operator can load draft back into form to correct issues. |
| **`401 Unauthorized`** | `SYNCING` $\to$ `DRAFT` | Auth session expired. **Do NOT delete draft**. Record session expiration notice. Prompt operator to re-authenticate at `/login`. Once re-authenticated, draft is immediately syncable. |
| **`403 Forbidden`** | `SYNCING` $\to$ `FAILED` | Role authorization mismatch (e.g. Citizen attempted to submit inspection). Record role boundary notice. Preserve payload for review or export. |
| **`409 Conflict`** | `SYNCING` $\to$ `CONFLICT` | Resource state collision (e.g. incident already closed or verified by command). Transition to `CONFLICT`. Prevent auto-retry until operator reviews conflicting record. |
| **`422 Unprocessable`** | `SYNCING` $\to$ `FAILED` | Schema validation error (e.g. invalid latitude, missing required field). Format structured validation errors into `sync_error`. Enable "Load into form" for field correction. |
| **`500+ / Timeout / NetErr`** | `SYNCING` $\to$ `FAILED` | Server error or network drop. Record transport error message. Retain in queue for automated or manual retry upon network restoration. |

---

## 3. Conflict Resolution Protocols

### 3.1 Scenario A: Incident Reporting Duplicate / Overlap
* **Trigger:** Multiple citizens or volunteers report the same disaster incident (e.g. same flooded intersection) while offline.
* **Resolution Rule:**
  * The backend accepts both incident submissions as distinct observational telemetry records (`Incident` table).
  * Incidents receive distinct UUIDs and cluster within the GIS spatial index (500m radius).
  * Government Command Center retains executive authority to merge duplicate incident reports via `POST /api/v1/incidents/merge` without losing citizen telemetry history.

### 3.2 Scenario B: Field Inspection Concurrency
* **Trigger:** Two volunteers submit damage assessments for the same facility during a telecommunications blackout.
* **Resolution Rule:**
  * Both submissions are accepted into `recovery_assessments` as distinct field records, each tagged with `verification_status = 'PENDING_VERIFICATION'`.
  * The Government Engineering Gate in Command Center displays all incoming assessments with timestamps and assessor confidence ratings.
  * The certifying engineer selects the authoritative observation or records a unified verified level (`POST /recovery/damage-assessments/{id}/verify`), logging full engineering rationale. Neither field observation is deleted.

### 3.3 Scenario C: Resource Stock Dispatch Contention
* **Trigger:** An NGO coordinator attempts to dispatch inventory while disconnected, but depot stock was depleted by another dispatcher.
* **Resolution Rule:**
  * When online, the dispatch request dispatches to `POST /resources/{id}/dispatch?quantity=X`.
  * If requested quantity exceeds available stock, the server rejects with `HTTP 400 Insufficient available inventory`.
  * The client transitions the action to `FAILED` and renders current depot balance, preventing phantom dispatches.

---

## 4. Purge & Lifecycle Governance

1. **Automated Cleanup:** Drafts are **never** automatically purged while in `DRAFT`, `FAILED`, or `CONFLICT` state.
2. **Operator Purge:** A draft may only be removed from IndexedDB when:
   * The operator explicitly clicks the trash/delete icon on an individual draft.
   * The operator clicks "Clear Completed", which deletes records whose status is strictly `SYNCED`.
3. **Storage Quota Management:** Native IndexedDB provides 50MB+ of origin storage on modern browsers. Under standard operational loads (average draft size: ~1.5 KB), a responder device can securely store upwards of 30,000 offline reports without storage exhaustion.

---

## 5. Delivery Semantics & Idempotency Boundary Disclosures

### 5.1 At-Least-Once Delivery Semantics
Under mobile network latency, sporadic cell tower drops, and transient packet loss, the client-server synchronization protocol guarantees **At-Least-Once Delivery**, NOT unassisted exactly-once delivery:
* **Genuine Server Acknowledgement Requirement:** A client draft transitions to `SYNCED` **strictly upon receipt of a verified HTTP 200/201 response** containing the server-generated resource identifier (`server_acknowledged_id`).
* **Client-Side Idempotency Guard:** If a draft has already reached `SYNCED` status with an assigned `server_acknowledged_id`, the client hook `syncDraft()` immediately returns the existing acknowledgement and aborts any duplicate HTTP dispatch.
* **In-Flight Network Interruption Case:** If a client dispatches an HTTP request, the backend persists the record, but the cellular network drops before the HTTP response reaches the browser:
  - The client catches the network drop and marks the draft `FAILED`.
  - Upon network restoration, the client or operator re-triggers synchronization.
  - Because standard REST endpoints (`POST /api/v1/incidents`, `POST /api/v1/recovery/damage-assessments/field-inspection`) generate new UUID primary keys per HTTP request without an enterprise idempotency table or unique client correlation constraint, the re-submission may create a second observational record on the backend.
  - In DIRS architecture, this is intentional and safe: field reports and damage inspections represent observational telemetry. Multiple reports are clustered by GIS spatial indexing and reconciled via Government Command triage (`POST /api/v1/incidents/merge` and engineering verification gates).
  - **Explicit Architectural Boundary:** DIRS does NOT claim end-to-end exactly-once delivery without a server-backed distributed idempotency table (`idempotency_keys`). Claims of guaranteed exactly-once delivery under arbitrary network failures are technically inaccurate and formally rejected.

