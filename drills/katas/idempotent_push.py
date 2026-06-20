"""TODO: idempotent push with dedupe by key."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


class IdempotentPusher:
    def __init__(self, store: list[str]) -> None:
        self._store = store
        self._seen: set[str] = set()

    async def push_once(
        self,
        idempotency_key: str,
        push_fn: Callable[[dict[str, Any]], Awaitable[None]],
        payload: dict[str, Any],
    ) -> str:
        """Return 'pushed' or 'duplicate' — NOT IMPLEMENTED."""
        await push_fn(payload)
        return "pushed"
