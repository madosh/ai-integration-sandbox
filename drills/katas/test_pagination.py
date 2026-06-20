"""Kata 2: pagination iterator — implement in pagination.py."""

from __future__ import annotations

import pytest

from drills.katas.pagination import iterate_offset, iterate_cursor


async def test_offset_pagination() -> None:
    pages = [
        {"items": [1, 2], "total": 5},
        {"items": [3, 4], "total": 5},
        {"items": [5], "total": 5},
    ]
    calls = 0

    async def fetch(offset: int, limit: int) -> dict:
        nonlocal calls
        calls += 1
        idx = offset // limit
        return pages[idx]

    items = []
    async for item in iterate_offset(fetch, limit=2):
        items.append(item)
    assert items == [1, 2, 3, 4, 5]
    assert calls == 3


async def test_cursor_pagination() -> None:
    async def fetch(cursor: str | None) -> tuple[list[str], str | None]:
        if cursor is None:
            return ["a", "b"], "c1"
        if cursor == "c1":
            return ["c"], None
        return [], None

    items = []
    async for item in iterate_cursor(fetch):
        items.append(item)
    assert items == ["a", "b", "c"]
