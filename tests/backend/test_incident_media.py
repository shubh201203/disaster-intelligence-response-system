import os
import io
import base64
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.incident import Incident, IncidentMedia
from app.config import settings

client = TestClient(app)

@pytest.fixture
def auth_citizen():
    """Register and authenticate a citizen user."""
    email = "citizen_media_tester@dirs.org"
    password = "TestPassword123!"
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Citizen Media Tester",
        "phone": "+919876543210",
        "role": "CITIZEN"
    })
    login_res = client.post("/api/v1/auth/login", data={
        "username": email,
        "password": password
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_admin():
    """Register and authenticate a government admin reviewer."""
    email = "admin_media_reviewer@dirs.gov"
    password = "AdminPassword123!"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Govt Reviewer",
        "phone": "+919876543211",
        "role": "GOVT"
    })
    login_res = client.post("/api/v1/auth/login", data={
        "username": email,
        "password": password
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# Tiny 1x1 valid PNG image bytes
TINY_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

# 1. Incident submission without an image
def test_incident_submission_without_image(auth_citizen):
    res = client.post("/api/v1/incidents", json={
        "title": "Flooding near Canal Road",
        "disaster_type": "FLOOD",
        "description": "High water levels observed without damage photos.",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "people_affected": 5
    }, headers=auth_citizen)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["media_urls"] == []

# 2. Incident submission with one image
def test_incident_submission_with_one_image(auth_citizen):
    # Create incident
    res = client.post("/api/v1/incidents", json={
        "title": "Submerged Junction Photo Report",
        "disaster_type": "FLOOD",
        "description": "Submerged street with photographic evidence.",
        "latitude": 13.0850,
        "longitude": 80.2750,
        "people_affected": 8
    }, headers=auth_citizen)
    assert res.status_code == 201
    inc_id = res.json()["id"]

    # Upload single image
    upload_res = client.post(
        f"/api/v1/incidents/{inc_id}/media",
        files={"file": ("flooded_road.png", io.BytesIO(TINY_PNG_BYTES), "image/png")},
        headers=auth_citizen
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["file_path"].startswith("/static/uploads/")
    assert upload_data["file_name"] == "flooded_road.png"

    # Verify incident retrieval returns the media URL
    get_res = client.get(f"/api/v1/incidents/{inc_id}", headers=auth_citizen)
    assert get_res.status_code == 200
    assert upload_data["file_path"] in get_res.json()["media_urls"]

# 3. Incident submission with multiple images
def test_incident_submission_with_multiple_images(auth_citizen):
    res = client.post("/api/v1/incidents", json={
        "title": "Multi-Image Structural Collapse",
        "disaster_type": "EARTHQUAKE",
        "description": "Two angle photos submitted for verification.",
        "latitude": 13.0900,
        "longitude": 80.2800,
        "people_affected": 15
    }, headers=auth_citizen)
    assert res.status_code == 201
    inc_id = res.json()["id"]

    # Upload image 1
    up1 = client.post(
        f"/api/v1/incidents/{inc_id}/media",
        files={"file": ("angle_north.png", io.BytesIO(TINY_PNG_BYTES), "image/png")},
        headers=auth_citizen
    )
    assert up1.status_code == 200
    path1 = up1.json()["file_path"]

    # Upload image 2
    up2 = client.post(
        f"/api/v1/incidents/{inc_id}/media",
        files={"file": ("angle_south.jpg", io.BytesIO(TINY_PNG_BYTES), "image/jpeg")},
        headers=auth_citizen
    )
    assert up2.status_code == 200
    path2 = up2.json()["file_path"]

    # Check incident detail has both
    detail = client.get(f"/api/v1/incidents/{inc_id}", headers=auth_citizen).json()
    assert len(detail["media_urls"]) == 2
    assert path1 in detail["media_urls"]
    assert path2 in detail["media_urls"]

# 4. Media association with the correct incident
def test_media_isolation_between_incidents(auth_citizen):
    # Incident A
    inc_a = client.post("/api/v1/incidents", json={
        "title": "Incident A Sector 1",
        "disaster_type": "FIRE",
        "description": "Incident A description",
        "latitude": 13.081,
        "longitude": 80.271
    }, headers=auth_citizen).json()["id"]

    # Incident B
    inc_b = client.post("/api/v1/incidents", json={
        "title": "Incident B Sector 2",
        "disaster_type": "FLOOD",
        "description": "Incident B description",
        "latitude": 13.082,
        "longitude": 80.272
    }, headers=auth_citizen).json()["id"]

    # Upload image ONLY to A
    up = client.post(
        f"/api/v1/incidents/{inc_a}/media",
        files={"file": ("only_for_a.png", io.BytesIO(TINY_PNG_BYTES), "image/png")},
        headers=auth_citizen
    ).json()

    # Verify A has it, B does NOT
    media_a = client.get(f"/api/v1/incidents/{inc_a}", headers=auth_citizen).json()["media_urls"]
    media_b = client.get(f"/api/v1/incidents/{inc_b}", headers=auth_citizen).json()["media_urls"]
    assert up["file_path"] in media_a
    assert up["file_path"] not in media_b
    assert media_b == []

# 5. Incident retrieval returning media references
def test_incident_list_returns_media_urls(auth_citizen):
    # Create incident with image
    inc = client.post("/api/v1/incidents", json={
        "title": "List Query Verification Incident",
        "disaster_type": "CYCLONE",
        "description": "Testing list query serialisation with media.",
        "latitude": 13.083,
        "longitude": 80.273
    }, headers=auth_citizen).json()
    inc_id = inc["id"]

    up = client.post(
        f"/api/v1/incidents/{inc_id}/media",
        files={"file": ("cyclone_tree.png", io.BytesIO(TINY_PNG_BYTES), "image/png")},
        headers=auth_citizen
    ).json()

    # Query list
    all_incidents = client.get("/api/v1/incidents", headers=auth_citizen).json()
    matched = [i for i in all_incidents if i["id"] == inc_id]
    assert len(matched) == 1
    assert up["file_path"] in matched[0]["media_urls"]

# 6. Government/Admin inspection endpoint displaying uploaded images
def test_admin_inspection_media_endpoint(auth_citizen, auth_admin):
    inc_id = client.post("/api/v1/incidents", json={
        "title": "Admin Review Photo Target",
        "disaster_type": "FLOOD",
        "description": "For Command Center inspection review.",
        "latitude": 13.084,
        "longitude": 80.274
    }, headers=auth_citizen).json()["id"]

    client.post(
        f"/api/v1/incidents/{inc_id}/media",
        files={"file": ("evidence_inspection.png", io.BytesIO(TINY_PNG_BYTES), "image/png")},
        headers=auth_citizen
    )

    # Admin calls detail endpoint
    admin_detail = client.get(f"/api/v1/incidents/{inc_id}", headers=auth_admin)
    assert admin_detail.status_code == 200
    assert len(admin_detail.json()["media_urls"]) == 1

    # Admin calls media list endpoint
    admin_media = client.get(f"/api/v1/incidents/{inc_id}/media", headers=auth_admin)
    assert admin_media.status_code == 200
    media_records = admin_media.json()
    assert len(media_records) == 1
    assert media_records[0]["file_name"] == "evidence_inspection.png"
    assert media_records[0]["media_type"] == "IMAGE"
    assert media_records[0]["mime_type"] == "image/png"

# 7. Image availability via static mount (serves real image bytes)
def test_image_static_mount_serves_bytes(auth_citizen):
    inc_id = client.post("/api/v1/incidents", json={
        "title": "Static File Serve Test",
        "disaster_type": "FLOOD",
        "description": "Checking static route accessibility.",
        "latitude": 13.085,
        "longitude": 80.275
    }, headers=auth_citizen).json()["id"]

    up = client.post(
        f"/api/v1/incidents/{inc_id}/media",
        files={"file": ("served_file.png", io.BytesIO(TINY_PNG_BYTES), "image/png")},
        headers=auth_citizen
    ).json()

    static_url = up["file_path"]  # e.g. /static/uploads/xxxx.png
    static_res = client.get(static_url)
    assert static_res.status_code == 200
    assert static_res.headers["content-type"] == "image/png"
    assert static_res.content == TINY_PNG_BYTES

# 8. Disk persistence verification (survives process / disk inspect)
def test_image_disk_storage_persistence(auth_citizen):
    inc_id = client.post("/api/v1/incidents", json={
        "title": "Disk Persistence Verification",
        "disaster_type": "FIRE",
        "description": "Checking file on host storage.",
        "latitude": 13.086,
        "longitude": 80.276
    }, headers=auth_citizen).json()["id"]

    up = client.post(
        f"/api/v1/incidents/{inc_id}/media",
        files={"file": ("disk_check.png", io.BytesIO(TINY_PNG_BYTES), "image/png")},
        headers=auth_citizen
    ).json()

    filename = os.path.basename(up["file_path"])
    disk_file = os.path.join(settings.MEDIA_UPLOAD_DIR, filename)
    assert os.path.exists(disk_file)
    with open(disk_file, "rb") as f:
        stored_bytes = f.read()
    assert stored_bytes == TINY_PNG_BYTES

# 9. Invalid MIME type rejection
def test_invalid_mime_type_rejected(auth_citizen):
    inc_id = client.post("/api/v1/incidents", json={
        "title": "MIME Check Incident",
        "disaster_type": "FLOOD",
        "description": "Checking MIME security validator.",
        "latitude": 13.087,
        "longitude": 80.277
    }, headers=auth_citizen).json()["id"]

    # Attempt to upload executable
    bad_upload = client.post(
        f"/api/v1/incidents/{inc_id}/media",
        files={"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-msdownload")},
        headers=auth_citizen
    )
    assert bad_upload.status_code == 400
    assert "Unsupported file type" in bad_upload.json()["detail"]

# 10. File-size limit enforcement (>10MB)
def test_file_size_limit_enforced(auth_citizen):
    inc_id = client.post("/api/v1/incidents", json={
        "title": "Oversized File Check",
        "disaster_type": "FLOOD",
        "description": "Checking 10MB limit enforcement.",
        "latitude": 13.088,
        "longitude": 80.278
    }, headers=auth_citizen).json()["id"]

    # 10.5 MB payload
    oversized_bytes = b"0" * (10 * 1024 * 1024 + 512 * 1024)
    res = client.post(
        f"/api/v1/incidents/{inc_id}/media",
        files={"file": ("too_big.png", io.BytesIO(oversized_bytes), "image/png")},
        headers=auth_citizen
    )
    # Rejection by router or middleware (400 or 413)
    assert res.status_code in (400, 413)

# 11. Unauthorized media access rejection
def test_unauthorized_media_access_rejected():
    # Calling media upload without auth
    no_auth_up = client.post(
        "/api/v1/incidents/some-incident-id/media",
        files={"file": ("test.png", io.BytesIO(TINY_PNG_BYTES), "image/png")}
    )
    assert no_auth_up.status_code == 401

    # Calling media list without auth
    no_auth_list = client.get("/api/v1/incidents/some-incident-id/media")
    assert no_auth_list.status_code == 401

# 12. Offline draft behavior and base64 upload auto-persistence
def test_offline_draft_base64_auto_persistence(auth_citizen):
    # Simulated offline draft payload syncing via POST /incidents with base64 data URL
    b64_data_url = "data:image/png;base64," + base64.b64encode(TINY_PNG_BYTES).decode("utf-8")

    sync_res = client.post("/api/v1/incidents", json={
        "title": "Offline Synced Incident with Evidence",
        "disaster_type": "FLOOD",
        "description": "Incident drafted offline and synchronized when connection restored.",
        "latitude": 13.089,
        "longitude": 80.279,
        "people_affected": 3,
        "media_urls": [b64_data_url]
    }, headers=auth_citizen)

    assert sync_res.status_code == 201
    synced_data = sync_res.json()
    inc_id = synced_data["id"]

    # Verify backend converted base64 into a real persistent file path
    assert len(synced_data["media_urls"]) == 1
    persisted_path = synced_data["media_urls"][0]
    assert persisted_path.startswith("/static/uploads/")
    assert persisted_path.endswith(".png")

    # Verify static file serves the real image bytes
    static_res = client.get(persisted_path)
    assert static_res.status_code == 200
    assert static_res.content == TINY_PNG_BYTES
