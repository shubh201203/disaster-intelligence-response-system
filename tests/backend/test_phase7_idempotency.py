"""
DIRS Phase 7 Test Suite: Idempotency, Security Headers, Request Limits, and Secret Validation
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.idempotency import idempotency_service, IdempotencyService
from app.config import Settings


@pytest.fixture(autouse=True)
def reset_idempotency_store():
    idempotency_service.clear()
    yield
    idempotency_service.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_security_headers_present(client):
    """Verify standard enterprise security headers and CSP are injected into HTTP responses."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    # Modern OWASP standard: disable legacy X-XSS-Protection in favor of modern CSP
    assert headers.get("x-xss-protection") == "0"
    assert "strict-origin" in headers.get("referrer-policy", "")
    # Content-Security-Policy presence and key directives
    csp = headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


def test_cors_headers_explicit(client):
    """Verify CORS configuration allows explicitly allowed frontend origins."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_payload_size_limiter(client):
    """Verify requests exceeding the configured payload limit are rejected with HTTP 413."""
    # TestClient content-length header simulation
    large_payload_headers = {
        "Content-Length": str(15 * 1024 * 1024),  # 15MB exceeds 10MB limit
        "Content-Type": "application/json"
    }
    response = client.post(
        "/api/v1/auth/login",
        headers=large_payload_headers,
        json={"email": "test@example.com", "password": "password"}
    )
    assert response.status_code == 413
    assert "Payload too large" in response.json()["detail"]


def test_chunked_streaming_payload_size_limiter(client):
    """Verify chunked streaming requests exceeding the configured payload limit are rejected with HTTP 413."""
    # Temporarily set MAX_REQUEST_BODY_BYTES lower for streaming test verification
    from app.config import settings
    orig_limit = settings.MAX_REQUEST_BODY_BYTES
    try:
        settings.MAX_REQUEST_BODY_BYTES = 500  # 500 bytes

        # Streaming generator emitting chunks
        def stream_chunks():
            for _ in range(20):
                yield b"A" * 50  # 1,000 bytes total, exceeds 500 byte limit

        response = client.post(
            "/api/v1/incidents",
            content=stream_chunks(),
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 413
        assert "Payload too large" in response.json()["detail"]
    finally:
        settings.MAX_REQUEST_BODY_BYTES = orig_limit


def test_production_environment_secret_key_validation():
    """Verify settings raise RuntimeError if weak or default secret is used in production/staging."""
    # Default secret in production must fail
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="dirs_jwt_secret_key_super_secure_change_me_in_production",
            BENEFICIARY_HASH_SALT="valid_salt_12345678"
        )
    assert "SECRET_KEY must be explicitly configured" in str(exc_info.value)

    # Short secret (<32 chars) in production must fail
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="too_short_key",
            BENEFICIARY_HASH_SALT="valid_salt_12345678"
        )
    assert "SECRET_KEY must be explicitly configured" in str(exc_info.value)

    # Empty salt in production must fail
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            BENEFICIARY_HASH_SALT=""
        )
    assert "BENEFICIARY_HASH_SALT must be configured" in str(exc_info.value)

    # Valid secret and salt in production must succeed
    valid_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="valid_high_entropy_secret_key_32_bytes_long!!",
        BENEFICIARY_HASH_SALT="valid_salt_of_adequate_entropy_length"
    )
    assert valid_settings.ENVIRONMENT == "production"


def test_idempotency_service_core_unit():
    """Unit test for IdempotencyService locking, replay, and collision detection."""
    svc = IdempotencyService()
    user_id = "user-123"
    endpoint = "/api/v1/incidents"
    key = "idem-uuid-001"
    payload_1 = {"title": "Flash Flood", "latitude": 28.61, "longitude": 77.23}
    payload_2 = {"title": "Different Incident", "latitude": 28.61, "longitude": 77.23}

    fp1 = svc.compute_fingerprint(payload_1)
    fp2 = svc.compute_fingerprint(payload_2)
    assert fp1 != fp2

    # First check: acquires lock
    is_cached, cached_res = svc.check_or_lock(key, user_id, endpoint, fp1)
    assert is_cached is False
    assert cached_res is None

    # Concurrent request with same key and fp while IN_PROGRESS -> 409
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        svc.check_or_lock(key, user_id, endpoint, fp1)
    assert exc_info.value.status_code == 409
    assert "currently being processed" in exc_info.value.detail

    # Collision: same key with different payload -> 409
    with pytest.raises(HTTPException) as exc_info:
        svc.check_or_lock(key, user_id, endpoint, fp2)
    assert exc_info.value.status_code == 409
    assert "collision" in exc_info.value.detail

    # Complete the request
    simulated_response = {"id": "inc-999", "title": "Flash Flood", "status": "REPORTED"}
    svc.store_result(key, user_id, endpoint, simulated_response, status_code=201)

    # Subsequent request with same key and fp -> returns cached
    is_cached_2, cached_res_2 = svc.check_or_lock(key, user_id, endpoint, fp1)
    assert is_cached_2 is True
    assert cached_res_2 == simulated_response

    # User isolation: Different user with same key -> acquires lock independently
    user_b = "user-456"
    is_cached_b, _ = svc.check_or_lock(key, user_b, endpoint, fp1)
    assert is_cached_b is False


def test_idempotency_service_release_lock_on_failure():
    """Verify lock release allows retry after an exception."""
    svc = IdempotencyService()
    user_id = "user-789"
    endpoint = "/api/v1/incidents"
    key = "idem-retry-key"
    fp = svc.compute_fingerprint({"data": "test"})

    # Lock acquired
    is_cached, _ = svc.check_or_lock(key, user_id, endpoint, fp)
    assert is_cached is False

    # Simulate failure and release
    svc.release_lock(key, user_id, endpoint)

    # Client can now retry
    is_cached_retry, _ = svc.check_or_lock(key, user_id, endpoint, fp)
    assert is_cached_retry is False
