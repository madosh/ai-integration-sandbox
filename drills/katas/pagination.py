"""TODO: async iterators for offset and cursor pagination."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any


async def iterate_offset(
    fetch: Callable[[int, int], Any],
    *,
    limit: int = 100,
) -> AsyncIterator[int]:
    """Yield all items across offset/limit pages — NOT IMPLEMENTED."""
    if False:
        yield 0


async def iterate_cursor(
    fetch: Callable[[str | None], Any],
) -> AsyncIterator[str]:
    """Yield all items across cursor pages — NOT IMPLEMENTED."""
    if False:
        yield ""
