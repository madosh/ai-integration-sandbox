"""Kata 5: idempotent push with dedupe."""

from __future__ import annotations

import pytest

from drills.katas.idempotent_push import IdempotentPusher


async def test_dedupe_by_key() -> None:
    store: list[str] = []
    pusher = IdempotentPusher(store)

    async def push(payload: dict) -> None:
        store.append(payload["id"])

    r1 = await pusher.push_once("key-1", push, {"id": "creative-1"})
    r2 = await pusher.push_once("key-1", push, {"id": "creative-1"})
    assert r1 == "pushed"
    assert r2 == "duplicate"
    assert store == ["creative-1"]
