# DIRS — MILESTONE 4, GATE 3
## PHASE A: READ-ONLY PREFLIGHT & E2E TEST ARCHITECTURE DISCOVERY

**Project:** Disaster Intelligence and Response System (DIRS)  
**Phase:** 6D-B — Mathematical Recovery Portfolio Optimization  
**Milestone:** 4 — Frontend UI Integration & Decision Support  
**Gate:** Gate 3 — End-to-End Workflow & Acceptance Testing  
**Phase:** Phase A — Read-Only Preflight & E2E Test Architecture Discovery  
**Document Type:** Formal Read-Only Architecture Inspection & Test Strategy Preflight  
**Status:** READY FOR PROJECT OWNER GATE 3 SPECIFICATION REVIEW  
**Timestamp:** 2026-11-17T17:25:00+05:30  
**Project Root:** `C:\Users\shubh\Downloads\DIRS`  

---

## 1. EXECUTIVE SUMMARY

Following the formal completion and closure of **Milestone 4, Gate 2** (`DIRS_MILESTONE_4_GATE2_COMPLETION_REPORT.md`), this document executes **Milestone 4, Gate 3, Phase A: Read-Only Preflight & E2E Test Architecture Discovery**.

The objective of Gate 3 is to provide rigorous, automated End-to-End (E2E) workflow and acceptance testing covering the entire user journey of the Recovery Optimization system across multiple authentication roles, route guards, scenario configuration parameters, candidate project manipulations, synchronous solver submissions with indeterminate state feedback, dual-ledger financial displays, and diagnostic reporting.

This preflight conducts an exhaustive, read-only architectural inspection of the repository. It inventories the actual frontend routing and component architecture, backend REST endpoints and authorization dependencies, installed test runners, browser runtimes, and existing contract/E2E suites. It defines an isolated test execution strategy using Playwright network interception and isolated backend fixtures to ensure zero corruption of persistent data or production databases. Finally, it proposes a 5-stage implementation plan for Gate 3.

**Crucial Discovery Findings:**
1. **Frontend Authentication & Routing (VERIFIED FROM SOURCE):** React Router v6 enforces least privilege via `ProtectedRoute`. The `ADMIN` role is strictly restricted to `/admin/recovery-optimization`; attempts to access `/admin` or `/admin/simulation` trigger an automatic fallback redirect to `/admin/recovery-optimization`. `GOVT` users retain super-access across all administrative routes.
2. **Stateless Solver Route (VERIFIED FROM SOURCE):** The backend endpoint `POST /api/v1/recovery/optimization/evaluate` is completely stateless and in-memory. It receives no SQLAlchemy database session, writes no database records, and persists no schedules.
3. **Playwright & Browser Environment (VERIFIED FROM CONFIGURATION):** `@playwright/test` v1.63.0 is installed locally in `frontend/node_modules`. The local machine has Chromium (`chromium-1243`, `chromium_headless_shell-1243`) installed in `ms-playwright`. Firefox and WebKit are **not installed**. Therefore, Gate 3 browser testing must be configured for Chromium desktop environments.
4. **Frozen Baseline (VERIFIED FROM SOURCE):** All 23 files comprising the Gate 2 baseline were inspected and verified bit-for-bit intact with **zero cryptographic drift**.

The preflight verdict is **`READY FOR PROJECT OWNER GATE 3 SPECIFICATION REVIEW`**.

---

## 2. GOVERNANCE AND AUTHORIZATION STATUS

This preflight was conducted under strict read-only governance:
- **Authorization:** Project Owner prompt `# DIRS — MILESTONE 4, GATE 3 / PHASE A: READ-ONLY PREFLIGHT & E2E TEST ARCHITECTURE DISCOVERY`.
- **Implementation Status:** No source code, tests, configuration, dependencies, or database records were modified or created, with the sole authorized exception of this document (`DIRS_MILESTONE_4_GATE3_PHASE_A_PREFLIGHT.md`).
- **Gate 3 Implementation:** Strictly **NOT AUTHORIZED**. No test files have been written.
- **Milestone 5:** Strictly **NOT AUTHORIZED**.

---

## 3. GATE 2 CLOSURE REFERENCE & BASELINE INTEGRITY

Gate 2 is formally closed and locked. Supporting governance documentation on disk includes:
* **Closure Report:** `DIRS_MILESTONE_4_GATE2_COMPLETION_REPORT.md`  
  * SHA-256: `49D1C79CF8BB6ABBE4C89CB8B3C4812CA5E62481AE7EC15FCC01DA21B398E6A7`  
  * Size: 21,739 bytes
* **Closure Preflight:** `DIRS_MILESTONE_4_GATE2_FORMAL_CLOSURE_PREFLIGHT.md`  
  * SHA-256: `54C36C96DAA82B0C1B27A92A9A96A9038EFA05A3E1E533793CEAA77A409B4C48`  
  * Size: 26,803 bytes

### Frozen 23-File Baseline Integrity Check
All 23 baseline files were cryptographically re-evaluated against their certified hashes. **Zero files drifted (100% bit-for-bit match)**:

| # | File Path | Baseline SHA-256 | Current SHA-256 | Size (Bytes) | Integrity Status |
| :---: | :--- | :--- | :--- | :---: | :---: |
| 1 | `frontend/src/components/recovery/SolverStatusBanner.tsx` | `74FC4C3743387EFE55E9969929626D1AE014E44198A1268961564883DE39D21D` | `74FC4C3743387EFE55E9969929626D1AE014E44198A1268961564883DE39D21D` | 9,878 | VERIFIED FROM SOURCE |
| 2 | `frontend/src/components/recovery/OptimizationKPIStats.tsx` | `8A785AD21A003673695A8002FFA4DA8A12AFE0B52137D234CBD9B75BFA051365` | `8A785AD21A003673695A8002FFA4DA8A12AFE0B52137D234CBD9B75BFA051365` | 5,823 | VERIFIED FROM SOURCE |
| 3 | `frontend/src/components/recovery/ProjectScheduleTimeline.tsx` | `6C5CC6D9D913EF79467534111162065541B08189CFBC599EF852F5F1FE6F6457` | `6C5CC6D9D913EF79467534111162065541B08189CFBC599EF852F5F1FE6F6457` | 15,475 | VERIFIED FROM SOURCE |
| 4 | `frontend/src/components/recovery/FinancialSolvencyMatrix.tsx` | `42ED942D6A4877AC99C0ED79C615FAE27E9261FEB4DFC61ACD2972C584FC5FC9` | `42ED942D6A4877AC99C0ED79C615FAE27E9261FEB4DFC61ACD2972C584FC5FC9` | 14,099 | VERIFIED FROM SOURCE |
| 5 | `frontend/src/components/recovery/InfeasibilityDiagnosticsView.tsx` | `7465BB846F6349BED6F0689B021356EEA99BBB6CA9F5B7027F81425F6EA1CD7C` | `7465BB846F6349BED6F0689B021356EEA99BBB6CA9F5B7027F81425F6EA1CD7C` | 14,791 | VERIFIED FROM SOURCE |
| 6 | `frontend/tests/contract/stage4Visualizations.spec.ts` | `1DE66E53042820E46A17E82AF214C385AD2966A61B330FBFB88AA5BA8B0D2170` | `1DE66E53042820E46A17E82AF214C385AD2966A61B330FBFB88AA5BA8B0D2170` | 15,325 | VERIFIED FROM SOURCE |
| 7 | `frontend/src/pages/admin/RecoveryOptimizationView.tsx` | `84272F5FD7114211739BE8812C5143A9258750981CA22D62375AE65979A36765` | `84272F5FD7114211739BE8812C5143A9258750981CA22D62375AE65979A36765` | 17,222 | VERIFIED FROM SOURCE |
| 8 | `frontend/src/hooks/useRecoveryOptimization.ts` | `5CBB48DA478BD7D9F0261B882B27252D0E54F5559BDC8AA5E0D23D279961E748` | `5CBB48DA478BD7D9F0261B882B27252D0E54F5559BDC8AA5E0D23D279961E748` | 2,894 | VERIFIED FROM SOURCE |
| 9 | `frontend/src/components/recovery/SolverControlBar.tsx` | `88526F47B2D3FF50A8191167E233865EC9A2E4C0DC7D70A6C121A41BDC8574A8` | `88526F47B2D3FF50A8191167E233865EC9A2E4C0DC7D70A6C121A41BDC8574A8` | 12,533 | VERIFIED FROM SOURCE |
| 10 | `frontend/src/components/recovery/IndeterminateSolverOverlay.tsx` | `11FF542BCFC9DC0C358C45AE6180529568977B33D5566E6EED27BD0EFBC6A534` | `11FF542BCFC9DC0C358C45AE6180529568977B33D5566E6EED27BD0EFBC6A534` | 5,811 | VERIFIED FROM SOURCE |
| 11 | `frontend/src/components/recovery/ScenarioParametersCard.tsx` | `09A2F32145E95A37C6C38445DF6CA3ACEDE217FEE25D99FB48246D57233FFDE8` | `09A2F32145E95A37C6C38445DF6CA3ACEDE217FEE25D99FB48246D57233FFDE8` | 10,470 | VERIFIED FROM SOURCE |
| 12 | `frontend/src/components/recovery/PeriodicBudgetsEditor.tsx` | `CE14A27AC3398A3BE3E38131EFAA278B90F35529CB22D3E291C91C6ED8618860` | `CE14A27AC3398A3BE3E38131EFAA278B90F35529CB22D3E291C91C6ED8618860` | 9,683 | VERIFIED FROM SOURCE |
| 13 | `frontend/src/components/recovery/CandidateProjectsGrid.tsx` | `F8D70713C2A43AFC9F42762F53E86DD951C7E223F7DB45289BE1537E1DA0D2E1` | `F8D70713C2A43AFC9F42762F53E86DD951C7E223F7DB45289BE1537E1DA0D2E1` | 30,153 | VERIFIED FROM SOURCE |
| 14 | `frontend/src/components/layout/Sidebar.tsx` | `9FFB6387843681D2FBF3C3595E98090ABE2575B54CF7C02657784182F1FA5D4A` | `9FFB6387843681D2FBF3C3595E98090ABE2575B54CF7C02657784182F1FA5D4A` | 6,171 | VERIFIED FROM SOURCE |
| 15 | `frontend/src/App.tsx` | `B7B54FB30ADB628B2C5DDA89B8C5F8C1A2D29E4E6A5B212F169D2BE4EF44F404` | `B7B54FB30ADB628B2C5DDA89B8C5F8C1A2D29E4E6A5B212F169D2BE4EF44F404` | 3,649 | VERIFIED FROM SOURCE |
| 16 | `frontend/src/types/recoveryOptimization.ts` | `A357559AF61BB48E97F3657D6389EAC3EA622369BD5BDC3D04D1E2A0548F77C9` | `A357559AF61BB48E97F3657D6389EAC3EA622369BD5BDC3D04D1E2A0548F77C9` | 11,147 | VERIFIED FROM SOURCE |
| 17 | `frontend/src/api/recoveryOptimization.ts` | `8CD51571D2319A8A1458695465598CD439C7423AE2E890FAF2E068BA0BBDC404` | `8CD51571D2319A8A1458695465598CD439C7423AE2E890FAF2E068BA0BBDC404` | 17,640 | VERIFIED FROM SOURCE |
| 18 | `frontend/src/fixtures/recoveryOptimizationFixtures.ts` | `F7DBC0FC9C250EF4F35FA1167D834FBAC2EDF6D376E9C4C9EA2DB1F46CE28BC7` | `F7DBC0FC9C250EF4F35FA1167D834FBAC2EDF6D376E9C4C9EA2DB1F46CE28BC7` | 6,846 | VERIFIED FROM SOURCE |
| 19 | `frontend/src/context/AuthContext.tsx` | `9B08EA97E4A8B37C1B3BD84E8FED19471F864C30634F0CD86ECB2376C90596BE` | `9B08EA97E4A8B37C1B3BD84E8FED19471F864C30634F0CD86ECB2376C90596BE` | 2,252 | VERIFIED FROM SOURCE |
| 20 | `frontend/playwright.contract.config.ts` | `0AA3127FBC05E82C74799614CA4A84AA83B69CACEFD54BE09A3BC6401F4A578D` | `0AA3127FBC05E82C74799614CA4A84AA83B69CACEFD54BE09A3BC6401F4A578D` | 555 | VERIFIED FROM SOURCE |
| 21 | `frontend/tests/contract/losslessParser.spec.ts` | `979F498B1D1D04C47BD743CF343A249D582EB2C152B94623391106D8FDE8DEE9` | `979F498B1D1D04C47BD743CF343A249D582EB2C152B94623391106D8FDE8DEE9` | 17,971 | VERIFIED FROM SOURCE |
| 22 | `frontend/tests/contract/dtoContracts.spec.ts` | `463E1F6965217D7DBC79FC7DA9B85BEE7C8923921A6FAB1A0D7FD93156397CC4` | `463E1F6965217D7DBC79FC7DA9B85BEE7C8923921A6FAB1A0D7FD93156397CC4` | 9,963 | VERIFIED FROM SOURCE |
| 23 | `frontend/tests/contract/apiClient.spec.ts` | `3EF54394709E5FCC583DD1890A57485473679B1C733489E63C12739F47564FBB` | `3EF54394709E5FCC583DD1890A57485473679B1C733489E63C12739F47564FBB` | 12,646 | VERIFIED FROM SOURCE |

---

## 4. EXISTING GATE 3 SCOPE EVIDENCE

Inspection of historical governance and tracking records reveals the evolution of Gate 3:
1. **Initial Conception (`DIRS_MILESTONE_4_GATE0_FRONTEND_ARCHITECTURE_INSPECTION.md`):** Initially designated as "Results, Gantt Timeline & Charts".
2. **Scope Acceleration (`DIRS_MILESTONE_4_GATE2_PHASE_A_PREFLIGHT.md`):** During Gate 2 planning, all visual results components (Gantt, KPIs, solvency matrices, diagnostic tiers) were moved forward into Gate 2 Stage 4 so that the full frontend application could be developed as a cohesive unit.
3. **Current Authoritative Scope (`task.md` & `DIRS_MILESTONE_4_GATE2_COMPLETION_REPORT.md`):**  
   Gate 3 is officially defined as:  
   **`Milestone 4 Gate 3: End-to-End Workflow & Acceptance Testing`**  
   The primary objective is end-to-end integration and acceptance verification across live and mocked browser environments, verifying role authentication, UI workflows, API communication, and operational resilience.

---

## 5. FRONTEND ARCHITECTURE INVENTORY

### A. Routing and Access Policies (`frontend/src/App.tsx`)
* **Framework:** React 18.2 with `react-router-dom` v6.22.3.
* **Security Guard:** `ProtectedRoute` component wrapping routes.
  * Checks authentication status: redirects unauthenticated users to `/login`.
  * Enforces least-privilege role boundaries:
    ```typescript
    if (allowedRoles && !allowedRoles.includes(user.role) && user.role !== 'GOVT') {
      const fallbackPath = user.role === 'ADMIN' ? '/admin/recovery-optimization' : '/citizen';
      return <Navigate to={fallbackPath} replace />;
    }
    ```
* **Discovered Application Routes:**
  * `/login` (Public) — User login with credential form and demo quick-access triggers.
  * `/register` (Public) — User registration.
  * `/citizen` (`CITIZEN`, `GOVT`) — Citizen emergency dashboard.
  * `/citizen/report` (`CITIZEN`, `VOLUNTEER`, `GOVT`) — Incident reporting wizard.
  * `/citizen/shelters` (Authenticated) — Shelter finder.
  * `/volunteer` (`VOLUNTEER`, `GOVT`) — Volunteer coordination.
  * `/ngo` (`NGO`, `GOVT`) — NGO supply and inventory relief.
  * `/admin` (`GOVT` ONLY) — Government Command Center. (Redirects `ADMIN` to `/admin/recovery-optimization`).
  * `/admin/simulation` (`GOVT` ONLY) — Predictive simulation sandbox. (Redirects `ADMIN` to `/admin/recovery-optimization`).
  * `/admin/recovery-optimization` (`GOVT`, `ADMIN`) — Recovery Portfolio Optimization UI.
  * `*` — Catch-all redirecting to `/login`.

### B. Authentication and State Management (`frontend/src/context/AuthContext.tsx`)
* **Role Types:** `'CITIZEN' | 'VOLUNTEER' | 'NGO' | 'GOVT' | 'ADMIN'`.
* **Storage:** JWT stored in `localStorage` under key `dirs_token`.
* **Session Restoration:** On mount, if `dirs_token` exists, calls `GET /api/v1/auth/me`. If token is invalid or expired, automatically invokes `logout()` (clears token, resets state, redirects).
* **Login Flow:** Submits URL-encoded form data (`username`, `password`) to `POST /api/v1/auth/login`. Returns `access_token` and `user` object.

### C. Recovery Optimization Workflow Components
* `RecoveryOptimizationView.tsx`: Tab orchestrator between "Scenario Configuration" and "Optimization Results"; holds scenario form state, template loader, and evaluation handler.
* `ScenarioParametersCard.tsx`: Planning horizon ($T \in [1, 120]$), period duration in days ($[1.0, 365.0]$), initial cash, currency selection (`INR` vs `CCU`), Tier-1 maximum start period, and discount rate.
* `PeriodicBudgetsEditor.tsx`: 1-based period columns $[1, T]$, integer-cent input fields, BigInt summation, uniform allocation helper.
* `CandidateProjectsGrid.tsx`: 500-candidate pagination (10/25/50/100 items), search by title/ID/district, multi-column exact string sorting, modal addition, inline edit, and project deletion (`handleDelete`).
* `SolverControlBar.tsx`: "Evaluate Scenario" button, validation error count badge, error alert banner, and human confirmation modal trigger.
* `IndeterminateSolverOverlay.tsx`: Monotonic stopwatch (`performance.now()`), pulsing progress indicator, interaction blocking backdrop.
* `SolverStatusBanner.tsx`: Visual banners for all 6 solver outcomes (`OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `MODEL_INVALID`, `POST_SOLVE_RECONCILIATION_FAILED`, `UNKNOWN`).
* `OptimizationKPIStats.tsx`: Exact integer/decimal strings for objective score, optimality gap, solve time, and district equity allocation.
* `ProjectScheduleTimeline.tsx`: 1-based periodic Gantt timeline with CSS Grid spanning, and unselected projects registry with non-blaming outcome status: "Not selected".
* `FinancialSolvencyMatrix.tsx`: Dual-ledger breakdown (CCU integer balances vs. INR cashflow); solvency status driven strictly by backend `is_solvent` authority.
* `InfeasibilityDiagnosticsView.tsx`: 4 diagnostic tiers (Summary, Conflict, Assumptions, Recommendations) with assumption core minimality and sufficiency metadata.

---

## 6. BACKEND AND API ARCHITECTURE INVENTORY

### A. Server Configuration & Endpoints
* **Framework:** FastAPI with Python 3.11.9 (`backend/app/main.py`).
* **API Prefix:** `/api/v1` (`settings.API_V1_STR = "/api/v1"`).
* **CORS Middleware:** Enabled for `localhost:5173`, `localhost:5174`, `localhost:3000`, `*`.
* **Primary Optimization Route:** `POST /api/v1/recovery/optimization/evaluate`.
  * **Router:** `backend/app/routers/recovery_optimization.py`.
  * **Security Dependency:** `Depends(require_any_role(["GOVT", "ADMIN"]))`.
  * **Statelessness Guarantee:** Does not declare or inject a SQLAlchemy `Session`. Runs purely in-memory via Google OR-Tools CP-SAT.
  * **Telemetry:** Emits a unique `X-Correlation-ID` UUID header on every response.
  * **Execution Timeout:** Enforced by backend service (default 120s, configurable via `DIRS_OPTIMIZATION_API_TIMEOUT_CAP_SECONDS`). Frontend client enforces 130s timeout.

### B. Authentication Middleware (`backend/app/core/deps.py`)
* `get_current_user`: Decodes JWT using `SECRET_KEY` and `HS256`, queries `users` table. Returns `User` object.
* `require_any_role(allowed_roles)`: Validates `current_user.role in allowed_roles` or `current_user.role == "GOVT"`. Throws HTTP 403 Forbidden on mismatch.

---

## 7. AUTHENTICATION AND AUTHORIZATION MAP

| User Role | Access to `/admin` | Access to `/admin/simulation` | Access to `/admin/recovery-optimization` | Backend Solver Route Access | Client Routing Behavior |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **Unauthenticated** | DENIED (401) | DENIED (401) | DENIED (401) | DENIED (401) | Redirected to `/login` |
| **CITIZEN** | DENIED (403) | DENIED (403) | DENIED (403) | DENIED (403) | Fallback redirected to `/citizen` |
| **VOLUNTEER** | DENIED (403) | DENIED (403) | DENIED (403) | DENIED (403) | Fallback redirected to `/citizen` |
| **NGO** | DENIED (403) | DENIED (403) | DENIED (403) | DENIED (403) | Fallback redirected to `/citizen` |
| **ADMIN** | **DENIED** | **DENIED** | **ALLOWED** | **ALLOWED** | Fallback redirected to `/admin/recovery-optimization` |
| **GOVT** | **ALLOWED** | **ALLOWED** | **ALLOWED** | **ALLOWED** | Full access to all administrative routes |

---

## 8. RECOVERY OPTIMIZATION COMPLETE USER JOURNEY

The actual user journey discovered from source inspection consists of 16 distinct operational phases:

```
[1. User Login] ──> [2. Role Validation] ──> [3. Navigation to Recovery Optimization]
       │
       ▼
[4. Scenario Configuration] ──> [5. Candidate Projects Management (Add/Edit/Delete)]
       │
       ▼
[6. Periodic Budget Allocation & Cent Validation]
       │
       ▼
[7. "Evaluate Scenario" Click] ──> [8. Human Confirmation Modal (ConfirmDialog)]
       │
       ├─ Cancel ──> Returns to Config
       │
       ▼ Confirm
[9. Synchronous API Dispatch (130s Timeout)] ──> [10. Indeterminate Overlay & Monotonic Stopwatch]
       │
       ├─────────────────────────┬─────────────────────────┬─────────────────────────┐
       ▼                         ▼                         ▼                         ▼
[11. OPTIMAL/FEASIBLE]    [12. INFEASIBLE]        [13. MODEL_INVALID]    [14. RECONCILIATION_FAILED]
  - Results Tab Activated   - Infeasibility View    - Error Banner         - Rejection Warning Banner
  - Status Banner (Green)   - 4-Tier Diagnostics    - Model Errors Alert   - Timeline Disabled/Red
  - KPI Cards Preserved     - Assumption Core Meta  - No Schedule Drawn    - Unusable Status
  - 1-Based Gantt Timeline
  - Dual-Ledger Solvency
       │
       ▼
[15. Tab Switching & Parameter Iteration]
       │
       ▼
[16. User Logout / Session Termination]
```

---

## 9. API AND DTO CONTRACT INVENTORY

All DTOs are fully defined in `frontend/src/types/recoveryOptimization.ts` and mirrored in `backend/app/schemas/recovery_optimization.py`:

* **`RecoveryOptimizationScenarioRequest`:**
  * `scenario_name`: string
  * `planning_horizon_periods`: integer $\in [1, 120]$
  * `period_duration_days`: Decimal string $\in [1.0, 365.0]$
  * `initial_cash_balance`: Decimal string $\ge 0$
  * `currency_unit`: `'INR' | 'CCU'`
  * `candidate_projects`: array of `CandidateProjectDTO` ($\le 500$ items)
  * `periodic_budgets`: array of `PeriodicBudgetDTO` (length = $T$)
  * `objective_weights`: `ObjectiveWeightsDTO`
  * `tier1_max_safety_start_period`: optional integer
* **`RecoveryOptimizationScenarioResponse`:**
  * `scenario_name`: string
  * `outcome_status`: `'OPTIMAL' | 'FEASIBLE' | 'INFEASIBLE' | 'UNKNOWN' | 'MODEL_INVALID' | 'POST_SOLVE_RECONCILIATION_FAILED'`
  * `objective_value`: optional Decimal string
  * `optimality_gap`: optional Decimal string
  * `solve_time_seconds`: Decimal string
  * `scheduled_projects`: array of `ScheduledProjectResultDTO`
  * `period_solvency`: array of `PeriodSolvencyResultDTO`
  * `district_equity_allocations`: optional dictionary
  * `infeasibility_diagnostics`: optional `InfeasibilityDiagnosticReportDTO`
* **`OptimizationErrorDetailDTO` (FastAPI 422/500 structured errors):**
  * `error_type`: `'VALIDATION_ERROR' | 'SOLVER_TIMEOUT' | 'INSUFFICIENT_RESOURCE_BOUND' | 'CONFLICTING_DEPENDENCY' | 'INTERNAL_EXECUTION_FAILURE'`
  * `message`: string
  * `diagnostic_code`: string
  * `validation_failures`: array of field failure strings
  * `input_fingerprint_sha256`: optional string

---

## 10. TEST INFRASTRUCTURE INVENTORY

Detailed discovery of the local execution environment:

| Runtime / Tool | Version | Installation Location | Status |
| :--- | :---: | :--- | :---: |
| **Node.js** | `v24.14.1` | Host System | VERIFIED FROM SOURCE / CLI |
| **npm** | `11.11.0` | Host System | VERIFIED FROM SOURCE / CLI |
| **Python** | `3.11.9` | Host System | VERIFIED FROM SOURCE / CLI |
| **@playwright/test** | `^1.63.0` | `frontend/node_modules/@playwright/test` | VERIFIED FROM CONFIGURATION |
| **Chromium Browser** | `1243` | `C:\Users\shubh\AppData\Local\ms-playwright` | VERIFIED FROM CONFIGURATION |
| **Chromium Headless Shell** | `1243` | `C:\Users\shubh\AppData\Local\ms-playwright` | VERIFIED FROM CONFIGURATION |
| **Firefox Browser** | N/A | None installed in `ms-playwright` | **NOT INSTALLED** |
| **WebKit Browser** | N/A | None installed in `ms-playwright` | **NOT INSTALLED** |
| **Existing Playwright Config** | `playwright.config.ts` | `frontend/playwright.config.ts` (points to `../tests/e2e`) | VERIFIED FROM CONFIGURATION |
| **Contract Playwright Config** | `playwright.contract.config.ts` | `frontend/playwright.contract.config.ts` (Node-mode) | VERIFIED FROM CONFIGURATION |
| **pytest** | `8.x` | Global / venv Python environment | VERIFIED FROM SOURCE (590 tests passing) |
| **Backend SQLite Test DB** | SQLite | `test_dirs.db` fixture override in `conftest.py` | VERIFIED FROM SOURCE |

### Critical Environment Insight: Browser Support
Because only Chromium is installed in `ms-playwright`, all Gate 3 Playwright browser E2E test projects must target Chromium (`Desktop Chrome` or `chromium-headless`). No package installation or browser download (`npx playwright install`) is permitted under current read-only governance.

---

## 11. EXISTING TEST COVERAGE AND GAPS

### Current Automated Test Coverage (Gate 1 & Gate 2)
1. **Frontend Contract Tests (76 Tests):**
   * `losslessParser.spec.ts` (44 tests) — BigInt precision, string preservation, float truncation prevention.
   * `dtoContracts.spec.ts` (8 tests) — Invariants, union types, decimal string schemas.
   * `apiClient.spec.ts` (8 tests) — 130s timeout, responseType text, correlation ID extraction, error normalizer.
   * `stage4Visualizations.spec.ts` (16 tests) — Dual-ledger solvency separation, 1-based period math, diagnostic tiers.
2. **Backend Pytest Suite (590 Tests):**
   * `test_phase6d_api_route.py` (27 tests) — Solver outcomes, 500 candidate cap, 120s timeout cap, HTTP status codes, correlation ID emission.
   * 563 additional unit and regression tests across incidents, alerts, resources, GIS, and AI models.

### Identified Test Gaps (Gate 3 Scope)
1. **No Live Browser E2E Tests for Recovery Optimization:**  
   Existing E2E tests in `tests/e2e/` (`playwright_disaster_workflow.spec.ts`, `playwright_phase3b_workflow.spec.ts`, `playwright_phase3c_workflow.spec.ts`) cover older milestones. There are **zero browser-level E2E tests** covering the Recovery Optimization UI (`RecoveryOptimizationView.tsx`).
2. **No Interactive Authentication Route-Guard Browser Verification:**  
   No E2E test asserts in a real browser that `ADMIN` users logging in via the UI form are permitted into `/admin/recovery-optimization` but automatically blocked and redirected away from `/admin` and `/admin/simulation`.
3. **No Browser-Level Solver Lifecycle & State Verification:**  
   No test verifies that clicking "Evaluate Scenario" triggers `ConfirmDialog`, that confirming mounts `IndeterminateSolverOverlay` with an incrementing stopwatch, or that receiving a solver payload switches tabs to "Optimization Results" without full page reloads.

---

## 12. PROPOSED E2E TEST COVERAGE MATRIX

To comprehensively close the test gaps without mutating application state, the following 5 test suites are proposed:

### Suite 1: Authentication & Least-Privilege Route Guards (`e2e-auth-routes`)
* **TC-E2E-01:** Unauthenticated user directly visiting `/admin/recovery-optimization` is redirected to `/login`.
* **TC-E2E-02:** User with role `ADMIN` logging in via login form successfully navigates to `/admin/recovery-optimization`.
* **TC-E2E-03:** User with role `ADMIN` attempting direct browser navigation to `/admin` is intercepted by `ProtectedRoute` and redirected to `/admin/recovery-optimization`.
* **TC-E2E-04:** User with role `ADMIN` attempting direct browser navigation to `/admin/simulation` is intercepted and redirected to `/admin/recovery-optimization`.
* **TC-E2E-05:** User with role `GOVT` logging in has full access to `/admin`, `/admin/simulation`, and `/admin/recovery-optimization`.
* **TC-E2E-06:** Sidebar navigation renders the amber "ADMIN" badge and only displays the "Recovery Optimization" link for `ADMIN` users.
* **TC-E2E-07:** User logout clears `dirs_token` from `localStorage` and redirects to `/login`.

### Suite 2: Scenario Configuration & Project Grid Workflows (`e2e-scenario-config`)
* **TC-E2E-08:** Scenario templates catalog loading (e.g. clicking "Multi-Quarter Recovery Plan (T=12)" populates horizon, period duration, and budgets).
* **TC-E2E-09:** Planning horizon boundary validation (entering $T=0$ or $T=121$ displays inline validation error and disables evaluation).
* **TC-E2E-10:** Periodic budget editor integer-cent validation (invalid decimal input shows validation error; auto-sum computes exact sum).
* **TC-E2E-11:** Candidate project addition via `AddCandidateModal` (form inputs add project to grid; verifies immediate reactivity).
* **TC-E2E-12:** Candidate project inline editing (modifying estimated cost or duration updates project row).
* **TC-E2E-13:** Candidate project deletion (`handleDelete` removes candidate row from grid).
* **TC-E2E-14:** Candidate grid pagination (page switching across 10, 25, 50, 100 rows per page).
* **TC-E2E-15:** Candidate grid multi-column sorting (sorting by estimated cost preserves exact string order).

### Suite 3: Solver Dispatch & Indeterminate State (`e2e-solver-dispatch`)
* **TC-E2E-16:** "Evaluate Scenario" button is disabled when active validation errors exist.
* **TC-E2E-17:** Clicking "Evaluate Scenario" with valid configuration opens `ConfirmDialog` modal displaying scenario summary.
* **TC-E2E-18:** Clicking "Cancel" in `ConfirmDialog` closes modal without dispatching API request.
* **TC-E2E-19:** Clicking "Confirm & Execute" in `ConfirmDialog` displays `IndeterminateSolverOverlay`.
* **TC-E2E-20:** Stopwatch in `IndeterminateSolverOverlay` visibly increments seconds monotonically.
* **TC-E2E-21:** Background UI interactions are disabled while indeterminate overlay is visible.

### Suite 4: Solver Outcome & Visualization Workflows (`e2e-visualizations`)
*(Utilizing Playwright network route interception for deterministic testing)*
* **TC-E2E-22:** `OPTIMAL` response activates "Optimization Results" tab, renders green `SolverStatusBanner`, and renders all KPI cards.
* **TC-E2E-23:** 1-based periodic Gantt timeline renders scheduled projects spanning exact column coordinates.
* **TC-E2E-24:** Unscheduled projects appear in the registry table with neutral status "Not selected".
* **TC-E2E-25:** Financial Solvency Matrix renders separate CCU and INR ledgers; displays `is_solvent` badge.
* **TC-E2E-26:** `INFEASIBLE` response renders diagnostic banner and 4-tier diagnostic view with assumption core minimality metadata.
* **TC-E2E-27:** `POST_SOLVE_RECONCILIATION_FAILED` response renders red rejection banner, warning that schedule is rejected and unusable.
* **TC-E2E-28:** `MODEL_INVALID` response displays error banner with invalid constraints listed.

### Suite 5: Error Handling & Operational Quality (`e2e-operational-quality`)
* **TC-E2E-29:** HTTP 401 Unauthorized response from backend clears token and redirects to `/login`.
* **TC-E2E-30:** HTTP 422 Unprocessable Entity response displays structured error message and diagnostic code.
* **TC-E2E-31:** HTTP 500 Internal Server Error displays sanitized error alert with correlation ID.
* **TC-E2E-32:** Network disconnection / timeout (>130s) displays `SOLVER_TIMEOUT` error alert.
* **TC-E2E-33:** Browser refresh on `/admin/recovery-optimization` maintains user session without unexpected logout.
* **TC-E2E-34:** Browser back/forward navigation operates cleanly without crashing React state.
* **TC-E2E-35:** Zero unhandled JavaScript console exceptions during the full workflow.

---

## 13. TEST ISOLATION AND SAFETY DESIGN

Automated E2E tests must never risk corrupting production records, exhausting server resources, or persisting unauthorized schedules. Gate 3 enforces a two-tier safety design:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   GATE 3 TEST ISOLATION STRATEGY                       │
├───────────────────────────────────┬────────────────────────────────────┤
│ TIER 1: DETERMINISTIC MOCK ROUTE  │ TIER 2: LOCAL TEST BACKEND SMOKE   │
│ (Playwright page.route() Intercept│ (FastAPI TestClient / SQLite DB)   │
├───────────────────────────────────┼────────────────────────────────────┤
│ • Simulates all 6 solver statuses │ • Live HTTP POST to test server    │
│ • Zero backend solver CPU load    │ • Isolated SQLite test database    │
│ • Instant response (no timeouts)  │ • Zero production DB connections   │
│ • Simulates 401, 403, 422, 500    │ • Zero data persistence in solver  │
│ • Deterministic test runs         │ • Smoke test verifies real wiring  │
└───────────────────────────────────┴────────────────────────────────────┘
```

1. **Playwright Network Route Interception (`page.route`):**
   * For the vast majority of UI and outcome visualization tests, Playwright intercepts `POST **/api/v1/recovery/optimization/evaluate`.
   * Returns exact, type-safe synthetic fixtures matching the backend contract (`OPTIMAL`, `INFEASIBLE`, `MODEL_INVALID`, etc.).
   * Guarantees 100% deterministic test behavior, instant sub-second test execution, and zero backend compute overhead.
2. **Stateless Solver Safety:**
   * The actual solver route `evaluate_recovery_optimization_scenario` has been verified as 100% stateless and in-memory. Even if executed against a live backend, it creates zero database records and applies no optimization schedules.
3. **Authentication Safety:**
   * Uses programmatic mock tokens or dedicated test accounts created in the local SQLite test database (`test_dirs.db`).
   * No production credentials or external services are ever called.

---

## 14. PROPOSED GATE 3 IMPLEMENTATION STAGE PLAN

To maintain strict governance, Gate 3 is recommended to proceed across five structured, sequential stages:

```
[Phase A: Read-Only Preflight] (Current)
       │
       ▼ (Awaiting Owner Review & Authorization)
[Stage 1: E2E Test Harness & Environment Setup]
       │
       ▼
[Stage 2: Authentication, Role-Based Route Guards & Least-Privilege E2E Tests]
       │
       ▼
[Stage 3: Scenario Configuration & Candidate Project Grid Workflow Tests]
       │
       ▼
[Stage 4: Solver Dispatch, Indeterminate State & Visualizations E2E Tests]
       │
       ▼
[Stage 5: Operational Quality, Regression Suite & Formal Gate 3 Closure]
```

### Stage 1: E2E Test Harness & Environment Setup
* **Objective:** Establish the Playwright E2E configuration, test fixtures, synthetic mock payloads, and test runner scripts without modifying application source code.
* **Scope:** `frontend/playwright.e2e.config.ts`, test fixtures, test utilities.
* **Entry Criteria:** Formal Project Owner authorization of Gate 3 Stage 1.
* **Exit Criteria:** Playwright launches headless Chromium and executes a baseline smoke test cleanly.

### Stage 2: Authentication, Role-Based Route Guards & Least-Privilege E2E Tests
* **Objective:** Verify role-based navigation, `ADMIN` route restrictions, `GOVT` super-access, unauthenticated redirects, and session logout.
* **Scope:** `tests/e2e/recovery_optimization_auth.spec.ts`.
* **Exit Criteria:** All 7 authentication test cases pass (TC-E2E-01 to TC-E2E-07).

### Stage 3: Scenario Configuration & Candidate Project Grid Workflow Tests
* **Objective:** Verify template loading, horizon boundaries, budget editor arithmetic, candidate project CRUD operations, sorting, and pagination in a real browser.
* **Scope:** `tests/e2e/recovery_optimization_config.spec.ts`.
* **Exit Criteria:** All 8 configuration test cases pass (TC-E2E-08 to TC-E2E-15).

### Stage 4: Solver Dispatch, Indeterminate State & Visualizations E2E Tests
* **Objective:** Verify human confirmation modal, monotonic stopwatch overlay, tab switching, Gantt chart, dual-ledger solvency, and 4-tier diagnostic reports across all 6 solver outcomes.
* **Scope:** `tests/e2e/recovery_optimization_outcomes.spec.ts`.
* **Exit Criteria:** All 13 solver and visualization test cases pass (TC-E2E-16 to TC-E2E-28).

### Stage 5: Operational Quality, Regression Suite & Formal Gate 3 Closure
* **Objective:** Verify browser refresh, error recovery (401, 422, 500, timeout), back/forward navigation, console log cleanliness, and full regression pass across all 76 contract tests + new E2E tests.
* **Scope:** `tests/e2e/recovery_optimization_operational.spec.ts`, `DIRS_MILESTONE_4_GATE3_COMPLETION_REPORT.md`.
* **Exit Criteria:** 100% passing automated suites; formal independent audit and Project Owner acceptance.

---

## 15. PROPOSED FILE SCOPE BY STAGE

All Gate 3 development will be strictly restricted to new test files and configurations, preserving all 23 application baseline files:

| Stage | Proposed Files to Create / Configure | Nature of Change |
| :---: | :--- | :--- |
| **Stage 1** | `frontend/playwright.e2e.config.ts`<br>`frontend/tests/e2e/fixtures/recoveryMockFixtures.ts` | Test configuration and fixtures ONLY |
| **Stage 2** | `frontend/tests/e2e/recoveryAuthRoutes.spec.ts` | Test specification ONLY |
| **Stage 3** | `frontend/tests/e2e/recoveryScenarioConfig.spec.ts` | Test specification ONLY |
| **Stage 4** | `frontend/tests/e2e/recoverySolverOutcomes.spec.ts` | Test specification ONLY |
| **Stage 5** | `frontend/tests/e2e/recoveryOperationalQuality.spec.ts`<br>`DIRS_MILESTONE_4_GATE3_COMPLETION_REPORT.md` | Test specification & Closure report ONLY |

---

## 16. RISKS AND BLOCKERS

| Risk / Observation | Classification | Impact | Mitigation Strategy |
| :--- | :---: | :---: | :--- |
| **Firefox/WebKit Browsers Not Installed** | ACCEPTED LIMITATION | Multi-browser matrix cannot run without downloading external binaries | Target Chromium (`chromium-1243`) exclusively in `playwright.e2e.config.ts`. No package installations required. |
| **Real Solver Evaluation Runtime** | PERFORMANCE RISK | CP-SAT solver evaluation can take up to 120s, causing slow E2E test runs | Use Playwright route interception (`page.route`) for deterministic sub-second UI test execution; run single small live smoke test. |
| **Frontend Dev Server Dependency** | OPERATIONAL RISK | Live E2E tests require a running frontend HTTP server (e.g. `http://localhost:5173`) | Configure `webServer` block in `playwright.e2e.config.ts` to automatically launch `npm run preview` or Vite dev server during test execution. |
| **Vite Bundle Warning (>500kB)** | NON-BLOCKING | Vite emits standard bundle warning during build | Documented as accepted technical limitation from Gate 2; does not affect E2E functional verification. |

---

## 17. REQUIRED PROJECT OWNER DECISIONS

The Project Owner's decision is requested on the following strategic aspects before Stage 1 implementation begins:

1. **Browser Target Matrix:**  
   * *Option A (Recommended):* Test exclusively on installed Chromium (`Desktop Chrome`), requiring zero binary downloads or external network dependencies.  
   * *Option B:* Authorize installation of Firefox and WebKit runtimes for multi-browser matrix testing.
2. **Backend Server Interaction Strategy:**  
   * *Option A (Recommended):* Hybrid approach: Use Playwright `page.route()` interception for all deterministic UI, validation, and solver outcome visualization tests, combined with one live backend smoke test.  
   * *Option B:* Pure live backend testing: All tests invoke the live backend solver, accepting variable solver runtimes and test run durations.
3. **Approval of Proposed 5-Stage Plan:**  
   * Approve the 5-stage implementation structure for Gate 3.

---

## 18. EXPLICIT AUTHORIZATION REQUIRED

To advance Milestone 4, Gate 3, the Project Owner's explicit authorization is required:

`AUTHORIZE GATE 3 STAGE 1: E2E TEST HARNESS & ENVIRONMENT SETUP`

No implementation work will commence without this explicit authorization.

---

## 19. FINAL RECOMMENDATION

### **READY FOR PROJECT OWNER GATE 3 SPECIFICATION REVIEW**

The frontend and backend architectures, authentication guards, user journeys, and test runtimes have been thoroughly discovered and documented. An isolated, safe, high-coverage E2E test strategy is formulated. The 23-file Gate 2 baseline is cryptographically certified at 100% integrity. The project is fully prepared for Project Owner specification review.
