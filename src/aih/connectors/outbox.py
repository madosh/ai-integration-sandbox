"""Transactional outbox for reliable idempotent PUSH."""

from __future__ import annotations

import hashlib
import json
from typing import Any


class Outbox:
    """In-memory outbox: dedupe by idempotency key before side effects."""

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._entries: list[dict[str, Any]] = []

    def idempotency_key(self, connector: str, action: str, payload: dict[str, Any]) -> str:
        raw = json.dumps({"c": connector, "a": action, "p": payload}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def enqueue(self, key: str, entry: dict[str, Any]) -> bool:
        """Return False if duplicate (already processed)."""
        if key in self._seen:
            return False
        self._seen.add(key)
        self._entries.append({"key": key, **entry})
        return True

    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)
