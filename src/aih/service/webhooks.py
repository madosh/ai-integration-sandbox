"""Inbound partner webhook event store (async callbacks)."""

from __future__ import annotations

import time
import uuid
from typing import Any

_events: list[dict[str, Any]] = []


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
    items = _events if partner is None else [e for e in _events if e["partner"] == partner]
    return items[-limit:]


def clear() -> None:
    _events.clear()
