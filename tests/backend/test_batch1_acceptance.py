import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.incident import Incident
from app.models.rescue import RescueTask

client = TestClient(app)

def get_auth(role="CITIZEN"):
    email = f"{role.lower()}_{uuid.uuid4().hex[:6]}@dirs.gov.in"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": f"{role} Acceptance Tester",
        "role": role
    })
    token = client.post("/api/v1/auth/login", data={"username": email, "password": "Password123!"}).json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}

# ==============================================================================
# DEF-01: ConfirmDialog Stacking Context & Portal Verification
# ==============================================================================
def test_batch1_def01_confirm_dialog_portal_markup():
    from pathlib import Path
    file_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "design-system" / "ConfirmDialog.tsx"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "createPortal" in content, "ConfirmDialog must use createPortal to escape local stacking context"
    assert "z-[9999]" in content, "ConfirmDialog must use z-[9999] to appear above Leaflet map controls (z-1000)"
    assert 'role="dialog"' in content
    assert 'aria-modal="true"' in content

# ==============================================================================
# DEF-06: Citizen SOS Distress Workflow & Non-Hardcoded Coordinates
# ==============================================================================
def test_batch1_def06_sos_with_gps():
    _, headers = get_auth("CITIZEN")
    lat, lng = 13.0827, 80.2707
    res = client.post(f"/api/v1/incidents/sos?lat={lat}&lng={lng}&description=Trapped%20on%20roof", headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["priority_level"] == "CRITICAL"
    assert data["priority_score"] == 99.0
    assert data["latitude"] == lat
    assert data["longitude"] == lng

    # Verify database persistence
    db = SessionLocal()
    inc = db.query(Incident).filter(Incident.id == data["id"]).first()
    assert inc is not None
    assert inc.priority_score == 99.0
    assert inc.priority_level == "CRITICAL"
    db.close()

def test_batch1_def06_sos_without_gps_never_hardcodes_coordinates():
    _, headers = get_auth("CITIZEN")
    # Call SOS endpoint without GPS coordinates (user denied location)
    res = client.post(
        "/api/v1/incidents/sos?location_address=Near%20Sector%204%20Old%20Bridge&description=Rising%20water",
        headers=headers
    )
    assert res.status_code == 201
    data = res.json()
    assert data["priority_level"] == "CRITICAL"
    assert data["priority_score"] == 99.0
    assert "Near Sector 4 Old Bridge" in data["location_address"]

    # Verify DB record: geom is None, description contains [LOCATION_UNAVAILABLE]
    db = SessionLocal()
    inc = db.query(Incident).filter(Incident.id == data["id"]).first()
    assert inc is not None
    assert "[LOCATION_UNAVAILABLE]" in inc.description
    assert inc.geom is None, "When GPS is denied, geom must remain None, never silently hardcoded"
    db.close()

# ==============================================================================
# DEF-10: Persistent Volunteer Task Acceptance (Assigned Only) & RBAC
# ==============================================================================
def test_batch1_def10_volunteer_only_views_own_assigned_tasks():
    _, govt_headers = get_auth("GOVT")
    vol1_token, vol1_headers = get_auth("VOLUNTEER")
    vol2_token, vol2_headers = get_auth("VOLUNTEER")

    vol1_user = client.get("/api/v1/auth/me", headers=vol1_headers).json()

    # Create incident and assign specifically to Volunteer 1
    inc = client.post("/api/v1/incidents", json={
        "title": "Medical Extraction",
        "disaster_type": "FLOOD",
        "description": "Urgent extraction",
        "latitude": 13.05,
        "longitude": 80.25
    }, headers=govt_headers).json()

    assign_res = client.post(
        f"/api/v1/volunteers/assign?incident_id={inc['id']}&volunteer_id={vol1_user['id']}",
        headers=govt_headers
    )
    assert assign_res.status_code == 201
    task_id = assign_res.json()["task_id"]

    # Volunteer 1 checks my-tasks -> must see task
    vol1_tasks = client.get("/api/v1/volunteers/my-tasks", headers=vol1_headers).json()
    assert any(t["id"] == task_id for t in vol1_tasks)

    # Volunteer 2 checks my-tasks -> must NOT see task
    vol2_tasks = client.get("/api/v1/volunteers/my-tasks", headers=vol2_headers).json()
    assert not any(t["id"] == task_id for t in vol2_tasks)

def test_batch1_def10_volunteer_accept_assigned_task_via_post():
    _, govt_headers = get_auth("GOVT")
    vol_token, vol_headers = get_auth("VOLUNTEER")
    vol_user = client.get("/api/v1/auth/me", headers=vol_headers).json()

    inc = client.post("/api/v1/incidents", json={
        "title": "Evacuation Assistance",
        "disaster_type": "FLOOD",
        "description": "Elderly citizen trapped",
        "latitude": 13.06,
        "longitude": 80.26
    }, headers=govt_headers).json()

    task_id = client.post(
        f"/api/v1/volunteers/assign?incident_id={inc['id']}&volunteer_id={vol_user['id']}",
        headers=govt_headers
    ).json()["task_id"]

    # Volunteer accepts their assigned task via POST
    res = client.post(f"/api/v1/volunteers/tasks/{task_id}/status?target_status=ACCEPTED", headers=vol_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ACCEPTED"

    # Verify persistence in database
    db = SessionLocal()
    task = db.query(RescueTask).filter(RescueTask.id == task_id).first()
    assert task is not None
    assert task.status == "ACCEPTED"
    db.close()

def test_batch1_def10_volunteer_cannot_transition_other_volunteer_task():
    _, govt_headers = get_auth("GOVT")
    _, vol1_headers = get_auth("VOLUNTEER")
    _, vol2_headers = get_auth("VOLUNTEER")
    vol1_user = client.get("/api/v1/auth/me", headers=vol1_headers).json()

    inc = client.post("/api/v1/incidents", json={
        "title": "Perimeter Patrol",
        "disaster_type": "FLOOD",
        "description": "Monitor sector boundary",
        "latitude": 13.07,
        "longitude": 80.27
    }, headers=govt_headers).json()

    task_id = client.post(
        f"/api/v1/volunteers/assign?incident_id={inc['id']}&volunteer_id={vol1_user['id']}",
        headers=govt_headers
    ).json()["task_id"]

    # Volunteer 2 attempts to transition Volunteer 1's task -> must be rejected
    res = client.post(f"/api/v1/volunteers/tasks/{task_id}/status?target_status=ACCEPTED", headers=vol2_headers)
    assert res.status_code == 400
    assert "only update their own assigned" in res.json()["detail"].lower()

def test_batch1_def10_govt_can_list_all_tasks():
    _, govt_headers = get_auth("GOVT")
    res = client.get("/api/v1/volunteers/tasks", headers=govt_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
