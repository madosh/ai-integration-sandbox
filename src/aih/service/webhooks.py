"""Inbound partner webhook event store (async callbacks)."""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from collections import deque
from typing import Any

MAX_EVENTS = 1000

_events: deque[dict[str, Any]] = deque(maxlen=MAX_EVENTS)


def verify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    """Check an HMAC-SHA256 hex signature over the raw request body."""
    if not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def receive(partner: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Record a webhook payload from a partner."""
    event = {
        "id": uuid.uuid4().hex[:12],
        "partner": partner,
        "payload": payload,
        "received_at": time.time(),
        "processed": False,
    }
    _events.append(event)
    return event


def list_events(partner: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    items = list(_events) if partner is None else [e for e in _events if e["partner"] == partner]
    return items[-limit:]


def clear() -> None:
    _events.clear()
