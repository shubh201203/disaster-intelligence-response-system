# DIRS — MILESTONE 4, GATE 3
## FORMAL IMPLEMENTATION SPECIFICATION: END-TO-END WORKFLOW & ACCEPTANCE TESTING

**Project:** Disaster Intelligence and Response System (DIRS)  
**Phase:** 6D-B — Mathematical Recovery Portfolio Optimization  
**Milestone:** 4 — Frontend UI Integration & Decision Support  
**Gate:** Gate 3 — End-to-End Workflow & Acceptance Testing  
**Document Type:** Formal Implementation-Ready Technical Specification  
**Project Owner Approvals:**  
1. Browser Matrix: **Option A — Chromium Only** (Pre-installed local Chromium 1243)  
2. Backend Interaction: **Option A — Hybrid Mocked UI + Separately Authorized Isolated Live Backend Smoke Test**  
3. Stage Structure: **Approved 5-Stage Implementation Plan**  
4. Test Inventory: **Approved 39-Test Canonical Inventory** (35 Original Canonical IDs + 4 Approved Independent Additions)  
**Status:** READY FOR PROJECT OWNER STAGE 1 AUTHORIZATION  
**Timestamp:** 2026-11-17  
**Project Root:** `C:\Users\shubh\Downloads\DIRS`  
**Authoritative References:** `DIRS_MILESTONE_4_GATE3_PHASE_A_PREFLIGHT.md`, `DIRS_MILESTONE_4_GATE3_PHASE_B_SPECIFICATION_REVIEW.md`

---

## 1. EXECUTIVE SUMMARY

Milestone 4, Gate 2 ("Full UI Implementation & Decision Support Dashboards") was formally certified, accepted, and closed on 2026-11-17 (`DIRS_MILESTONE_4_GATE2_COMPLETION_REPORT.md`). The frozen baseline of 23 files remains 100% intact with zero drift.

Following the Project Owner's explicit approval of the Gate 3 Phase A preflight recommendations and the formal 39-test inventory resolution, this document establishes the **Formal Implementation Specification for Gate 3: End-to-End Workflow & Acceptance Testing**.

Gate 3 introduces automated, browser-level acceptance testing to verify the end-to-end user journeys of the Disaster Recovery Optimization interface across multiple authentication roles, client-side route guards, interactive scenario configuration editors, candidate project management tables, synchronous solver submission flows with live indeterminate states, and multi-tier results visualizations.

In accordance with Project Owner directives, Gate 3 enforces:
1. **Chromium-Exclusive Execution:** Uses the installed Chromium runtime (`chromium-1243`) without downloading external browser packages or binary dependencies.
2. **Hybrid Test Architecture:** Leverages Playwright network route interception (`page.route`) for deterministic UI and visualization testing, combined with a separately authorized, tightly isolated live backend smoke test executed against an isolated SQLite test database.
3. **Strict 5-Stage Implementation Lifecycle:** Sequenced from harness setup, through auth guards, configuration workflows, solver visualizations, to operational quality and final gate sign-off.
4. **Canonical 39-Case Test Matrix:**
   - Preserves all thirty-five (35) original canonical test IDs (`TC-E2E-01` through `TC-E2E-35`) with their exact historically approved meanings and primary objectives.
   - Incorporates four (4) approved independent top-level tests (`TC-E2E-36`, `TC-E2E-37`, `TC-E2E-38`, `TC-E2E-39`) to provide dedicated coverage for HTTP 403 Forbidden, Malformed JSON recovery, parameterized non-admin administrative route-denial matrix (covering all 3 administrative routes `/admin`, `/admin/simulation`, `/admin/recovery-optimization` across `CITIZEN`, `VOLUNTEER`, and `NGO` roles; 3 × 3 = 9 combinations), and network transport disconnection.
   - Incorporates approved status-specific sub-step assertions for `FEASIBLE` (under `TC-E2E-22`) and `UNKNOWN` (under `TC-E2E-28`).
5. **Decoupled Live Backend Smoke Test:** Preserved outside the 39 browser E2E test inventory as a separately authorized integration activity conditioned on nine (9) strict database isolation invariants.
6. **Architectural Timeout Integrity:** Enforces the established 120-second backend solver cap (`settings.RECOVERY_OPTIMIZATION_TIMEOUT_SECONDS`) and 130,000-millisecond frontend client timeout (`TIMEOUT_MS`), rejecting artificial 60-second timeouts.
7. **Absolute Baseline Protection:** All 23 Gate 2 baseline files, existing contract tests (76/76), and backend regression tests (590/590) are strictly preserved.

---

## 2. GOVERNANCE BASELINE & ARCHITECTURAL INVARIANTS

All Gate 3 test suites are constrained by the immutable governance and architectural invariants established in Gates 0 through 2:

1. **Role Least-Privilege Access:** The `ADMIN` role is strictly restricted to `/admin/recovery-optimization`. Any navigation attempt to `/admin` or `/admin/simulation` must trigger an automatic fallback redirect to `/admin/recovery-optimization`. The `GOVT` role retains authorized access across all three administrative routes. Non-administrative roles (`CITIZEN`, `VOLUNTEER`, `NGO`) attempting direct navigation to any administrative route (`/admin`, `/admin/simulation`, `/admin/recovery-optimization`) are denied access by `ProtectedRoute` and redirected to their designated dashboard at `/citizen` (`fallbackPath = user.role === 'ADMIN' ? '/admin/recovery-optimization' : '/citizen'` in `frontend/src/App.tsx` L24). Zero administrative content is exposed, and no redirect loops occur.
2. **Synchronous, Stateless Solver Execution:** The backend solver route `POST /api/v1/recovery/optimization/evaluate` is completely stateless and in-memory. It receives no SQLAlchemy database session, writes no operational database records, and persists no schedules.
3. **Mandatory Human Confirmation:** The UI must prohibit automated solver evaluation dispatch; users must review parameters and explicitly confirm dispatch via `ConfirmDialog`.
4. **Zero Automatic Schedule Application:** Optimization outputs are strictly decision-support advisories; project schedules are never applied to operational records automatically.
5. **Lossless Numeric String Preservation:** Monetary values exceeding IEEE-754 double precision limits, BigInt integer cent balances, and high-precision Decimal values are formatted and rendered as exact strings without floating-point truncation.
6. **Strict 1-Based Period Coordinates:** All temporal dimensions, planning horizons ($T \in [1, 120]$), project start/completion dates, and budget columns are strictly 1-based.
7. **Dual-Ledger Accounting Separation:** Community Capacity Units (CCU) and Indian Rupee (INR) cash balances are tracked in parallel without implicit exchange rates.
8. **Timeout Architecture:**
   - Backend solver wall-clock cap: **120 seconds** (`settings.RECOVERY_OPTIMIZATION_TIMEOUT_SECONDS = 120`).
   - Frontend HTTP client timeout: **130,000 milliseconds** (`TIMEOUT_MS = 130_000` in `api/recoveryOptimization.ts`).
   - The 10-second differential ensures the frontend client never aborts prematurely before the backend solver finishes or returns its 120-second timeout outcome.
9. **Status Presentation Semantics:**
   - `OPTIMAL`: Usable schedule (`hasUsableSchedule === true`). Renders green status banner, KPI stats, timeline, and solvency matrix.
   - `FEASIBLE`: Usable schedule (`hasUsableSchedule === true`). Renders blue status banner, distinct "Feasible" status label, KPI stats, timeline, and solvency matrix. Separately asserted from OPTIMAL.
   - `INFEASIBLE`: No usable schedule (`hasUsableSchedule === false`). Renders amber diagnostic banner and 4-tier diagnostics view with assumption core minimality metadata.
   - `UNKNOWN`: No usable schedule (`hasUsableSchedule === false`). Renders slate banner. Must NOT invent a cause or display fabricated solver explanations.
   - `MODEL_INVALID`: No usable schedule (`hasUsableSchedule === false`). Renders red banner with model diagnostic alert and invalid constraint details.
   - `POST_SOLVE_RECONCILIATION_FAILED`: Schedule rejected and unusable (`hasUsableSchedule === false`). Renders red rejection banner with mathematical reconciliation failure details.

---

## 3. CANONICAL 39-TEST INVENTORY (AUTHORITATIVE MAPPING)

The Gate 3 test matrix comprises exactly thirty-nine (39) browser E2E test cases across four test specification files:

### 3.1 Stage 2: Authentication, Route Guards & Least Privilege (8 Tests)
**File:** `frontend/tests/e2e/recoveryAuthRoutes.spec.ts`

| Test ID | Test Scenario Name | Execution Type | Target Route / Interaction | Primary Assertion & Verification |
| :--- | :--- | :---: | :--- | :--- |
| **TC-E2E-01** | Unauthenticated Access Redirect | Browser E2E | Direct visit `/admin/recovery-optimization` without token | Intercepted by `ProtectedRoute`; redirected to `/login`. |
| **TC-E2E-02** | Valid ADMIN Login & Routing | Browser E2E | Submit Login form with `ADMIN` credentials | Authenticated; redirected to `/admin/recovery-optimization`. |
| **TC-E2E-03** | ADMIN Intercepted from `/admin` | Browser E2E | Direct visit `/admin` with `ADMIN` token | Intercepted; redirected to `/admin/recovery-optimization`. |
| **TC-E2E-04** | ADMIN Intercepted from `/admin/simulation` | Browser E2E | Direct visit `/admin/simulation` with `ADMIN` token | Intercepted; redirected to `/admin/recovery-optimization`. |
| **TC-E2E-05** | GOVT Super-Access to Admin Routes | Browser E2E | Visit `/admin`, `/admin/simulation`, `/admin/recovery-optimization` | Full authorized access to all administrative routes. |
| **TC-E2E-06** | Sidebar Role Badge & Navigation | Browser E2E | Inspect sidebar navigation DOM for `ADMIN` | Amber "ADMIN" badge rendered; only "Recovery Optimization" link shown. |
| **TC-E2E-07** | User Logout Session Cleared | Browser E2E | Click "Sign Out" in user menu | `dirs_token` removed from `localStorage`; redirected to `/login`. |
| **TC-E2E-38** | Parameterized Non-Admin Route-Denial Matrix | Browser E2E | Parameterized matrix across 3 roles (`CITIZEN`, `VOLUNTEER`, `NGO`) and 3 admin routes (`/admin`, `/admin/simulation`, `/admin/recovery-optimization`) | Denies all 9 combinations; redirects to source-backed dashboard `/citizen`; zero admin content exposed; zero redirect loops. |

#### Detailed Specification: TC-E2E-38 — Parameterized Non-Admin Administrative Route-Denial Matrix
* **Stage:** Stage 2
* **File:** `frontend/tests/e2e/recoveryAuthRoutes.spec.ts`
* **Execution:** Chromium browser E2E with deterministic mocked authentication/session responses.
* **Top-Level Inventory Count:** Exactly one (1) canonical top-level test ID (`TC-E2E-38`), executed as a data-driven parameterized test with distinct reporting labels for each of the nine (9) role/route combinations.

**Parameterized Cases (3 Roles × 3 Routes = 9 Combinations):**

| Role | `/admin` | `/admin/simulation` | `/admin/recovery-optimization` | Source-Backed Redirect Destination |
| :--- | :---: | :---: | :---: | :---: |
| **CITIZEN** | Denied | Denied | Denied | `/citizen` |
| **VOLUNTEER** | Denied | Denied | Denied | `/citizen` |
| **NGO** | Denied | Denied | Denied | `/citizen` |

**Mandatory Verification Criteria for Every Combination:**
1. **Authenticated Synthetic Identity:** Assert the user session is authenticated as the designated non-admin synthetic identity (`CITIZEN`, `VOLUNTEER`, or `NGO`).
2. **Route Access Denial:** Assert direct navigation to the target administrative route (`/admin`, `/admin/simulation`, or `/admin/recovery-optimization`) is strictly denied.
3. **Source-Backed Redirect Destination:** Assert the application redirects to `/citizen`, exactly matching `ProtectedRoute` in `frontend/src/App.tsx` (`const fallbackPath = user.role === 'ADMIN' ? '/admin/recovery-optimization' : '/citizen'`).
4. **Content Isolation:** Assert zero administrative DOM elements (e.g., `CommandCenter`, `DisasterSimulationView`, `RecoveryOptimizationView`, solver banners, candidate project grids) are mounted or exposed.
5. **Session Stability:** Assert zero redirect loops occur and zero uncaught JavaScript exceptions are thrown during navigation.

**Role-Access Separation:**
* `TC-E2E-03`: `ADMIN` role direct visit to `/admin` is intercepted and redirected to `/admin/recovery-optimization`.
* `TC-E2E-04`: `ADMIN` role direct visit to `/admin/simulation` is intercepted and redirected to `/admin/recovery-optimization`.
* `TC-E2E-05`: `GOVT` role retains super-access across all three administrative routes (`/admin`, `/admin/simulation`, `/admin/recovery-optimization`).
* `TC-E2E-38`: `CITIZEN`, `VOLUNTEER`, and `NGO` roles are systematically denied access to all three administrative routes and redirected to `/citizen`.
* *Governance Invariant:* `TC-E2E-38` complements and does not merge, renumber, or replace `TC-E2E-03`, `TC-E2E-04`, or `TC-E2E-05`.

### 3.2 Stage 3: Scenario Configuration & Candidate Projects (8 Tests)
**File:** `frontend/tests/e2e/recoveryScenarioConfig.spec.ts`

| Test ID | Test Scenario Name | Execution Type | Target Route / Interaction | Primary Assertion & Verification |
| :--- | :--- | :---: | :--- | :--- |
| **TC-E2E-08** | Scenario Template Loading | Browser E2E | Click preset catalog buttons | Clicking "Minimal Valid Template" or "Tier-1 Safety Template" populates horizon, duration, and budgets. |
| **TC-E2E-09** | Planning Horizon Boundary Validation | Browser E2E | Enter $T=0$, $T=121$, $T=12$ | Boundary values $T=0$ and $T=121$ show validation errors and disable execution; $T=12$ is accepted. |
| **TC-E2E-10** | Periodic Budget Cent Summation | Browser E2E | Enter per-period budget decimal strings | Validates integer-cent inputs; auto-sum accurately computes cumulative budget. |
| **TC-E2E-11** | Candidate Project Addition Modal | Browser E2E | Submit `AddCandidateModal` | New candidate project added to grid; verifies immediate state reactivity. |
| **TC-E2E-12** | Candidate Project Inline Edit | Browser E2E | Modify duration / estimated cost in grid | Project row updates reactively; preserves numeric precision. |
| **TC-E2E-13** | Candidate Project Deletion | Browser E2E | Click delete button on candidate row | Candidate row removed from grid; budget/metric counters update. |
| **TC-E2E-14** | Candidate Grid Pagination | Browser E2E | Switch page size (10, 25, 50, 100) and pages | Pagination controls navigate rows cleanly without state corruption. |
| **TC-E2E-15** | Candidate Grid Exact String Sorting | Browser E2E | Click column headers (e.g., Cost, Priority) | Multi-column sort preserves exact alphanumeric/numeric order. |

### 3.3 Stage 4: Solver Dispatch, Indeterminate State & Visualizations (13 Tests)
**File:** `frontend/tests/e2e/recoverySolverOutcomes.spec.ts`

| Test ID | Test Scenario Name | Execution Type | Target Route / Interaction | Primary Assertion & Verification |
| :--- | :--- | :---: | :--- | :--- |
| **TC-E2E-16** | Evaluation Disabled on Errors | Browser E2E | Trigger validation errors (e.g., $T=0$) | "Execute Optimization" button disabled; tooltips indicate active validation errors. |
| **TC-E2E-17** | Confirmation Dialog Summary | Browser E2E | Click "Evaluate Scenario" with valid configuration | `ConfirmDialog` modal opens, displaying scenario summary and parameter checklist. |
| **TC-E2E-18** | Confirmation Dialog Cancellation | Browser E2E | Click "Cancel" in `ConfirmDialog` | Modal dismisses cleanly; zero API calls dispatched; state preserved. |
| **TC-E2E-19** | Confirmation Dispatch Trigger | Browser E2E | Click "Execute Optimization" in modal | Modal closes; indeterminate solver overlay displays; API request dispatched. |
| **TC-E2E-20** | Stopwatch Increments Monotonically | Browser E2E | Inspect pending UI overlay | Stopwatch visibly increments formatted seconds monotonically (`{elapsedSeconds.toFixed(1)}s`). |
| **TC-E2E-21** | Background Control Interaction Lock | Browser E2E | Click background buttons while request pending | Backdrop modal blocks pointer events; background inputs remain inert. |
| **TC-E2E-22** | OPTIMAL & FEASIBLE Status Rendering | Mocked UI | Intercept POST $\rightarrow$ return `OPTIMAL` / `FEASIBLE` | Primary: `OPTIMAL` renders green status banner and KPI stats. Named sub-step: `FEASIBLE` renders blue status banner with distinct status label. Both assert `hasUsableSchedule === true`. |
| **TC-E2E-23** | 1-Based Periodic Gantt Timeline | Mocked UI | Inspect timeline grid element with valid result | Scheduled projects render across exact 1-based column coordinates without off-by-one shifts. |
| **TC-E2E-24** | Unselected Projects Registry | Mocked UI | Inspect unscheduled projects registry table | Unselected candidate projects render with neutral status "Not selected". |
| **TC-E2E-25** | Dual-Ledger Solvency Separation | Mocked UI | Inspect Financial Solvency Matrix | Separate CCU and INR ledgers render correctly; displays `is_solvent` badge. |
| **TC-E2E-26** | INFEASIBLE 4-Tier Diagnostics | Mocked UI | Intercept POST $\rightarrow$ return `INFEASIBLE` | Amber diagnostic banner displays; 4-tier diagnostics view renders assumption core metadata; `hasUsableSchedule === false`. |
| **TC-E2E-27** | Reconciliation Failure Rejection | Mocked UI | Intercept POST $\rightarrow$ `POST_SOLVE_RECONCILIATION_FAILED` | Red rejection banner displays; warns that schedule is mathematically rejected and unusable (`hasUsableSchedule === false`). |
| **TC-E2E-28** | MODEL_INVALID & UNKNOWN Error Panels | Mocked UI | Intercept POST $\rightarrow$ `MODEL_INVALID` / `UNKNOWN` | Primary: `MODEL_INVALID` renders red banner and lists invalid constraints. Named sub-step: `UNKNOWN` renders slate banner with schedule suppressed, with zero invented causes or timeout explanations. Both assert `hasUsableSchedule === false`. |

### 3.4 Stage 5: Operational Quality, Error Resilience & Harness (10 Tests)
**File:** `frontend/tests/e2e/recoveryOperationalQuality.spec.ts`

| Test ID | Test Scenario Name | Execution Type | Target Route / Interaction | Primary Assertion & Verification |
| :--- | :--- | :---: | :--- | :--- |
| **TC-E2E-29** | HTTP 401 Session Expiry Handling | Mocked UI | Intercept POST $\rightarrow$ return HTTP 401 | Clears `dirs_token` from `localStorage`; redirects user to `/login`. |
| **TC-E2E-30** | HTTP 422 Contract Validation Error | Mocked UI | Intercept POST $\rightarrow$ return HTTP 422 | Displays structured validation failure banner with diagnostic field errors. |
| **TC-E2E-31** | HTTP 500 Sanitized Error Alert | Mocked UI | Intercept POST $\rightarrow$ return HTTP 500 | Displays sanitized error alert preserving correlation ID where provided. |
| **TC-E2E-32** | Solver Request Timeout (130s) | Mocked UI | Simulate 130,000ms frontend request timeout | Displays `SOLVER_TIMEOUT` error alert matching 130s client timeout contract. |
| **TC-E2E-33** | Browser Refresh Session Health | Browser E2E | Reload `/admin/recovery-optimization` via `page.reload()` | Preserves user session and authentication state without unexpected logout. |
| **TC-E2E-34** | Browser Back/Forward Health | Browser E2E | Navigate back and forward across routes | Navigation history operates cleanly without React state crashes or desynchronization. |
| **TC-E2E-35** | Zero Unhandled Console Errors | Browser E2E | Monitor `page.on('console')` across workflows | Zero unhandled JavaScript console exceptions or uncaught runtime errors. |
| **TC-E2E-36** | HTTP 403 Forbidden Handling | Mocked UI | Intercept POST $\rightarrow$ return HTTP 403 | Displays operation not permitted error; does NOT clear session or redirect to login. |
| **TC-E2E-37** | Malformed JSON Response Recovery | Mocked UI | Intercept POST $\rightarrow$ return unparseable non-JSON text | Normalized syntax error handled gracefully; displays error banner without unhandled exceptions. |
| **TC-E2E-39** | Network Transport Disconnection | Mocked UI | Abruptly drop network connection during dispatch | Displays connection failure toast/alert; overlay dismisses; UI remains interactive. |

---

## 4. APPROVED STATUS SEMANTICS & ASSERTIONS

To avoid false equating of statuses that share visual themes, all solver status assertions must verify the exact mathematical and operational semantics specified below:

```
┌───────────────────────────────────┬──────────────────────┬────────────────────┬──────────────────────────────────────────────────┐
│ Solver Status                     │ hasUsableSchedule    │ Status Banner      │ Required Verifications                           │
├───────────────────────────────────┼──────────────────────┼────────────────────┼──────────────────────────────────────────────────┤
│ OPTIMAL                           │ TRUE                 │ Green theme        │ • Status label displays "OPTIMAL"                │
│                                   │                      │                    │ • Objective value and solve time rendered        │
│                                   │                      │                    │ • Gantt timeline & solvency matrix rendered      │
├───────────────────────────────────┼──────────────────────┼────────────────────┼──────────────────────────────────────────────────┤
│ FEASIBLE                          │ TRUE                 │ Blue theme         │ • Status label displays "FEASIBLE" (distinct)    │
│                                   │                      │                    │ • Objective value and solve time rendered        │
│                                   │                      │                    │ • Gantt timeline & solvency matrix rendered      │
├───────────────────────────────────┼──────────────────────┼────────────────────┼──────────────────────────────────────────────────┤
│ INFEASIBLE                        │ FALSE                │ Amber theme        │ • Status label displays "INFEASIBLE"             │
│                                   │                      │                    │ • 4-tier diagnostics view mounted                │
│                                   │                      │                    │ • Assumption core minimality metadata displayed  │
│                                   │                      │                    │ • Gantt timeline suppressed                      │
├───────────────────────────────────┼──────────────────────┼────────────────────┼──────────────────────────────────────────────────┤
│ UNKNOWN                           │ FALSE                │ Slate theme        │ • Status label displays "UNKNOWN"                │
│                                   │                      │                    │ • Non-usable outcome advisory notice displayed   │
│                                   │                      │                    │ • NO invented causes or timeout explanations     │
│                                   │                      │                    │ • Gantt timeline suppressed                      │
├───────────────────────────────────┼──────────────────────┼────────────────────┼──────────────────────────────────────────────────┤
│ MODEL_INVALID                     │ FALSE                │ Red theme          │ • Status label displays "MODEL_INVALID"          │
│                                   │                      │                    │ • Invalid constraints / model errors listed      │
│                                   │                      │                    │ • Gantt timeline suppressed                      │
├───────────────────────────────────┼──────────────────────┼────────────────────┼──────────────────────────────────────────────────┤
│ POST_SOLVE_RECONCILIATION_FAILED  │ FALSE                │ Red theme          │ • Status label displays "RECONCILIATION_FAILED"  │
│                                   │                      │                    │ • Rejection warning: schedule mathematically     │
│                                   │                      │                    │   rejected and unusable                          │
│                                   │                      │                    │ • Mismatch details table displayed               │
│                                   │                      │                    │ • Gantt timeline suppressed                      │
└───────────────────────────────────┴──────────────────────┴────────────────────┴──────────────────────────────────────────────────┘
```

---

## 5. RECONCILED REQUIREMENTS TRACEABILITY MATRIX (17 REQUIREMENTS)

The seventeen (17) approved architectural requirements from the Gate 3 Phase B specification are mapped across the 39 tests as follows:

| # | Architectural Requirement | Target Test ID(s) | Implementation Stage | Planned Coverage Status | Primary Objective Preserved |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | `OPTIMAL` Outcome Rendering | `TC-E2E-22` | Stage 4 | **Planned Coverage Mapped** | Yes — Green banner, objective KPI stats, usable schedule. |
| **2** | `FEASIBLE` Outcome Rendering | `TC-E2E-22` (sub-step) | Stage 4 | **Planned Coverage Mapped** | Yes — Blue banner, distinct status label, usable schedule. |
| **3** | `INFEASIBLE` Diagnostics | `TC-E2E-26` | Stage 4 | **Planned Coverage Mapped** | Yes — Amber banner, 4-tier diagnostics, assumption core metadata. |
| **4** | `UNKNOWN` Outcome Handling | `TC-E2E-28` (sub-step) | Stage 4 | **Planned Coverage Mapped** | Yes — Slate banner, schedule suppressed, zero invented causes. |
| **5** | `MODEL_INVALID` Error Panel | `TC-E2E-28` | Stage 4 | **Planned Coverage Mapped** | Yes — Red banner, invalid constraints listed, schedule suppressed. |
| **6** | `POST_SOLVE_RECONCILIATION_FAILED` | `TC-E2E-27` | Stage 4 | **Planned Coverage Mapped** | Yes — Rejection banner, unusable schedule notice. |
| **7** | HTTP 401 Session Expiry | `TC-E2E-29` | Stage 5 | **Planned Coverage Mapped** | Yes — Token removed from `localStorage`, redirect to `/login`. |
| **8** | HTTP 403 Forbidden Response | `TC-E2E-36` | Stage 5 | **Planned Coverage Mapped** | Yes — Independent top-level test; error shown, session preserved. |
| **9** | HTTP 422 Validation Error | `TC-E2E-30` | Stage 5 | **Planned Coverage Mapped** | Yes — Structured validation failures displayed with field details. |
| **10** | HTTP 500 Sanitized Alert | `TC-E2E-31` | Stage 5 | **Planned Coverage Mapped** | Yes — Sanitized error message and correlation ID where supported. |
| **11** | Network Transport Failure | `TC-E2E-39` | Stage 5 | **Planned Coverage Mapped** | Yes — Independent top-level test; transport drop alert displayed. |
| **12** | Client Request Timeout (130s) | `TC-E2E-32` | Stage 5 | **Planned Coverage Mapped** | Yes — `SOLVER_TIMEOUT` alert matching 130s frontend timeout. |
| **13** | Malformed JSON Recovery | `TC-E2E-37` | Stage 5 | **Planned Coverage Mapped** | Yes — Independent top-level test; syntax error handled cleanly. |
| **14** | CITIZEN Route Denial | `TC-E2E-38` | Stage 2 | **Planned Coverage Mapped** | Yes — 3/3 admin routes (`/admin`, `/admin/simulation`, `/admin/recovery-optimization`) denied; redirected to `/citizen`. |
| **15** | VOLUNTEER Route Denial | `TC-E2E-38` | Stage 2 | **Planned Coverage Mapped** | Yes — 3/3 admin routes (`/admin`, `/admin/simulation`, `/admin/recovery-optimization`) denied; redirected to `/citizen`. |
| **16** | NGO Route Denial | `TC-E2E-38` | Stage 2 | **Planned Coverage Mapped** | Yes — 3/3 admin routes (`/admin`, `/admin/simulation`, `/admin/recovery-optimization`) denied; redirected to `/citizen`. |
| **17** | Isolated Live Backend Smoke Test | **Decoupled Activity** | Stage 5 | **Planned Coverage Mapped** | Yes — Separate post-mocking integration activity outside 39 tests. |

---

## 6. DECOUPLED LIVE BACKEND SMOKE TEST PROTOCOL

The live backend smoke test is strictly excluded from the 39 browser E2E test inventory. It operates as a conditional, post-mocking integration activity subject to separate Project Owner authorization.

### 6.1 Nine Mandatory Database Isolation Prerequisites

Before any live backend smoke test command may be executed, the following nine (9) conditions must be proven:

1. **Explicit SQLite Configuration:** `settings.DATABASE_URL` must resolve to an explicit SQLite database URL (`sqlite:///...`).
2. **Absolute Database Path Resolution:** The SQLite file path must resolve within a temporary or isolated test directory, strictly separate from any development or production SQLite store.
3. **Runtime Dialect Verification:** Verification that `engine.dialect.name == 'sqlite'` must execute at startup.
4. **Zero Production Credentials:** No production PostgreSQL or external database environment variables may be set or accessible.
5. **Synthetic Test Identities Only:** User authentication must use ephemeral test seeds with synthetic roles.
6. **Zero External Integrations:** External alert sinks, notification dispatchers, or third-party webhooks must remain disabled.
7. **Zero Database Mutation Invariant:** Pre-test and post-test row count queries across all tables (`users`, `disasters`, `resources`, etc.) must demonstrate **zero net row changes**.
8. **Stateless Solver Verification:** The solver evaluation endpoint `POST /api/v1/recovery/optimization/evaluate` must be proven to execute entirely in-memory with zero database sessions injected.
9. **Deterministic Teardown:** The temporary test database and server process must terminate and unmount deterministically upon test completion.

If any of these nine prerequisites fails verification, the live smoke test is **BLOCKED**.

---

## 7. FIVE-STAGE IMPLEMENTATION LIFECYCLE & FILE MANIFEST

Gate 3 implementation is organized into five sequential stages with strict entry and exit criteria:

```
┌────────────────────────────────────────────────────────┐
│ STAGE 1: E2E Test Harness & Environment Setup          │
│ • playwright.e2e.config.ts                             │
│ • recoveryMockFixtures.ts                              │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ STAGE 2: Auth, Route Guards & Least Privilege (8 Tests)│
│ • recoveryAuthRoutes.spec.ts (TC-E2E-01..07, 38)       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ STAGE 3: Scenario Config & Candidate Projects (8 Tests)│
│ • recoveryScenarioConfig.spec.ts (TC-E2E-08..15)       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ STAGE 4: Solver Dispatch & Visualizations (13 Tests)   │
│ • recoverySolverOutcomes.spec.ts (TC-E2E-16..28)       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ STAGE 5: Operational Quality, Errors & Closure (10)    │
│ • recoveryOperationalQuality.spec.ts (29..35, 36,37,39)│
│ • Live Smoke Test (Separately authorized)              │
│ • DIRS_MILESTONE_4_GATE3_COMPLETION_REPORT.md          │
└────────────────────────────────────────────────────────┘
```

### Seven-File Implementation Manifest

| Stage | Implementation Target File Path | Purpose | State on Disk |
| :---: | :--- | :--- | :---: |
| **Stage 1** | `frontend/playwright.e2e.config.ts` | Dedicated Playwright E2E configuration (Chromium only, port 5173) | Not created (unauthorized) |
| **Stage 1** | `frontend/tests/e2e/fixtures/recoveryMockFixtures.ts` | Synthetic scenario and solver outcome route fixtures | Not created (unauthorized) |
| **Stage 2** | `frontend/tests/e2e/recoveryAuthRoutes.spec.ts` | 8 tests covering auth routing, session, least privilege, and the 9-combination non-admin route-denial matrix (TC-E2E-01..07, 38) | Not created (unauthorized) |
| **Stage 3** | `frontend/tests/e2e/recoveryScenarioConfig.spec.ts` | 8 tests covering presets, horizon/budget validation, and candidate grid | Not created (unauthorized) |
| **Stage 4** | `frontend/tests/e2e/recoverySolverOutcomes.spec.ts` | 13 tests covering dispatch dialog, stopwatch overlay, and all 6 solver statuses | Not created (unauthorized) |
| **Stage 5** | `frontend/tests/e2e/recoveryOperationalQuality.spec.ts` | 10 tests covering 401, 422, 500, 403, malformed JSON, 130s timeout, transport disconnect, session refresh, navigation, and console exceptions | Not created (unauthorized) |
| **Stage 5** | `DIRS_MILESTONE_4_GATE3_COMPLETION_REPORT.md` | Formal Gate 3 completion report and certification | Not created (unauthorized) |

---

## 8. FROZEN BASELINE & REGRESSION PROTECTION

To guarantee that Gate 3 introduces zero code drift or regression:
1. **Pre- and Post-Stage Baseline Checks:** Prior to and immediately following each stage, all 23 baseline files will be re-verified via SHA-256. If any baseline file differs by even 1 byte, execution will halt immediately.
2. **Contract Suite Retention:** `npx playwright test --config=playwright.contract.config.ts` (76 tests) must execute and pass on every stage transition.
3. **Backend Suite Retention:** `pytest tests/ -q` (590 tests) must execute and pass during Stage 5.
4. **Configuration Isolation:** `playwright.e2e.config.ts` operates as an independent configuration file and does not modify or overwrite `playwright.contract.config.ts` or `playwright.config.ts`.
5. **Task Tracking Protection:** `task.md` remains strictly read-only and unmodified.

---

## 9. PROJECT OWNER AUTHORIZATION REQUIREMENTS

Implementation of Gate 3 cannot proceed without separate, explicit Project Owner authorization.

The required authorization string to begin Stage 1 is:

```
AUTHORIZE GATE 3 STAGE 1: E2E TEST HARNESS & ENVIRONMENT SETUP
```

Approval of this specification document does **NOT** constitute authorization to begin Stage 1 implementation.

---

## 10. FINAL SPECIFICATION RECOMMENDATION

### **READY FOR PROJECT OWNER STAGE 1 AUTHORIZATION**

This formal specification resolves all test inventory ambiguities, preserves all 35 canonical test assignments, establishes the 4 approved independent additions, enforces accurate status and timeout semantics, and maps planned coverage for all 17 approved requirements. Gate 3 is ready for immediate Stage 1 implementation upon explicit Project Owner instruction.
