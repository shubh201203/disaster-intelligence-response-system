"""
DIRS Phase 7 Server-Side Idempotency Service

Provides resilient, client-scoped idempotency caching for critical write operations
(e.g., Incident Creation, Field Inspection Damage Assessments).

Under harsh field conditions, cellular network packet drops often trigger client retries.
This service ensures that:
1. Replays of identical requests return the exact previous response without side-effects.
2. Concurrent duplicate requests are rejected with HTTP 409 Conflict (Lock Active).
3. Payload tampering / key collisions (same key, different payload) are rejected with HTTP 409 Conflict.
4. Expired keys are automatically pruned according to TTL (default 24h).
"""

import hashlib
import json
import threading
import time
from typing import Any, Dict, Optional, Tuple
from fastapi import Header, HTTPException, status
from pydantic import BaseModel


class IdempotencyRecord:
    """Represents a cached idempotency operation record."""

    def __init__(
        self,
        key: str,
        user_id: str,
        endpoint: str,
        fingerprint: str,
        ttl_seconds: int = 86400
    ):
        self.key = key
        self.user_id = user_id
        self.endpoint = endpoint
        self.fingerprint = fingerprint
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.status = "IN_PROGRESS"  # IN_PROGRESS | COMPLETED | FAILED
        self.response_data: Optional[Dict[str, Any]] = None
        self.status_code: int = 200

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class IdempotencyService:
    """
    Thread-safe idempotency manager.
    Operates in-memory by default for zero-dependency standalone execution,
    with an extensible store interface.
    """

    _instance = None
    _singleton_lock = threading.Lock()

    def __init__(self):
        self._store: Dict[Tuple[str, str, str], IdempotencyRecord] = {}
        self._store_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "IdempotencyService":
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @staticmethod
    def compute_fingerprint(payload: Any) -> str:
        """
        Computes deterministic SHA-256 fingerprint from request payload.
        Handles Pydantic models, dictionaries, and raw data.
        """
        if isinstance(payload, BaseModel):
            data = payload.model_dump(mode="json")
        elif isinstance(payload, dict):
            data = payload
        else:
            data = str(payload)
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def check_or_lock(
        self,
        key: str,
        user_id: str,
        endpoint: str,
        fingerprint: str,
        ttl_seconds: int = 86400
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Atomically inspects the store for an active or completed idempotency record.
        Returns:
            (True, cached_response_data) if already completed and valid.
            (False, None) if lock successfully acquired for execution.
        Raises:
            HTTPException 409: If payload mismatch collision or concurrent execution is detected.
        """
        composite_key = (str(user_id), str(endpoint), str(key))
        with self._store_lock:
            self._cleanup_expired()

            record = self._store.get(composite_key)
            if record is not None and not record.is_expired():
                # Payload collision check (same key used for different data)
                if record.fingerprint != fingerprint:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency key collision: provided request payload differs from previous request."
                    )
                # In-progress concurrent execution check
                if record.status == "IN_PROGRESS":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="A request with this idempotency key is currently being processed."
                    )
                # Completed replay
                if record.status == "COMPLETED":
                    return True, record.response_data

            # Acquire execution lock
            new_record = IdempotencyRecord(
                key=key,
                user_id=str(user_id),
                endpoint=endpoint,
                fingerprint=fingerprint,
                ttl_seconds=ttl_seconds
            )
            self._store[composite_key] = new_record
            return False, None

    def store_result(
        self,
        key: str,
        user_id: str,
        endpoint: str,
        response_data: Dict[str, Any],
        status_code: int = 200
    ):
        """Transitions record to COMPLETED and saves serializable response data."""
        composite_key = (str(user_id), str(endpoint), str(key))
        with self._store_lock:
            record = self._store.get(composite_key)
            if record is not None:
                record.status = "COMPLETED"
                record.response_data = response_data
                record.status_code = status_code

    def release_lock(self, key: str, user_id: str, endpoint: str):
        """Removes lock on exception or unexpected failure to allow retry."""
        composite_key = (str(user_id), str(endpoint), str(key))
        with self._store_lock:
            if composite_key in self._store and self._store[composite_key].status == "IN_PROGRESS":
                del self._store[composite_key]

    def _cleanup_expired(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if v.is_expired()]
        for k in expired:
            del self._store[k]

    def clear(self):
        """Testing helper to clear store."""
        with self._store_lock:
            self._store.clear()


# Default singleton instance
idempotency_service = IdempotencyService.get_instance()


def get_idempotency_key(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key")
) -> Optional[str]:
    """Dependency helper to extract optional idempotency key from headers."""
    return idempotency_key or x_idempotency_key
