# DIRS — Verification Fix Log

Last Updated: 2026-09-10

This log tracks bug fixes applied during the Phase 1 & Phase 2 Forensic Verification process.

---

## Logged Fixes

### Fix #1: WebSocket Manager Broadcast Method Interface
- **Bug:** `AttributeError: 'WebSocketManager' object has no attribute 'broadcast'` when emergency alert router triggered alerts broadcast.
- **Root Cause:** `WebSocketManager` had defined `broadcast_event(...)` but `alerts.py` invoked `ws_manager.broadcast(...)`.
- **Fix:** Added `broadcast(self, message: Dict[str, Any])` method to [`backend/app/core/websocket_manager.py`](file:///C:/Users/shubh/Downloads/DIRS/backend/app/core/websocket_manager.py#L21-L30) supporting direct dictionary payload broadcasting.
- **Test Added:** `tests/backend/test_alerts.py::test_government_alert_creation`
- **Verification Result:** Passed cleanly (37/37 backend tests passed).

---

### Fix #2: Pytest GeoAlchemy Spatial DDL Listener Bypass on SQLite
- **Bug:** Pytest test runs threw `sqlite3.OperationalError: no such function: AddGeometryColumn` when `Base.metadata.create_all` attempted to execute SpatiaLite DDL on SQLite test database.
- **Root Cause:** GeoAlchemy2 attached DDL listeners to table metadata upon model import, which fired on SQLite engines during test suite runs.
- **Fix:** Monkeypatched `geoalchemy2.admin.dialects.sqlite.after_create` and `before_drop` in [`tests/backend/conftest.py`](file:///C:/Users/shubh/Downloads/DIRS/tests/backend/conftest.py#L1-L25).
- **Test Added:** Session-wide DB fixture initialization in `conftest.py`.
- **Verification Result:** Passed cleanly (37/37 backend tests passed).

---

### Fix #3: NGO Stock Dispatch UI Wiring
- **Bug:** "Dispatch Stock" button on `NGODashboard.tsx` had no `onClick` handler and operated purely as a static visual element.
- **Root Cause:** Event listener missing on frontend button component.
- **Fix:** Added `handleDispatch(resId: string)` in [`frontend/src/pages/ngo/NGODashboard.tsx`](file:///C:/Users/shubh/Downloads/DIRS/frontend/src/pages/ngo/NGODashboard.tsx#L35-L48) invoking `POST /resources/{id}/dispatch?dispatch_quantity=...`.
- **Test Added:** Interactive E2E stock dispatch step in Playwright spec.
- **Verification Result:** Verified via frontend production build and E2E spec.

---

### Fix #4: Volunteer Dashboard Task Status State Machine Wiring
- **Bug:** `VolunteerDashboard.tsx` used static React state sequence for task status transitions without sending backend API updates.
- **Root Cause:** `handleNextStatus` mutated local `useState` array index instead of calling API.
- **Fix:** Updated `handleNextStatus` in [`frontend/src/pages/volunteer/VolunteerDashboard.tsx`](file:///C:/Users/shubh/Downloads/DIRS/frontend/src/pages/volunteer/VolunteerDashboard.tsx#L25-L40) to issue `POST /volunteers/tasks/{id}/status?target_status=...` requests.
- **Test Added:** `tests/backend/test_volunteers.py::test_task_state_transition_sequence`
- **Verification Result:** Verified backend state machine synchronization.
