"""Pagination strategies abstracted behind async iterators.

Both cursor- and offset-style pagination are reduced to "yield raw item dicts",
so connectors don't repeat paging logic.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

FetchFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


async def cursor_paginate(
    fetch: FetchFn,
    *,
    items_key: str,
    next_cursor_key: str,
    page_size: int = 50,
    cursor_param: str = "cursor",
    limit_param: str = "limit",
    max_pages: int = 1000,
) -> AsyncIterator[dict[str, Any]]:
    """Iterate a cursor-paginated resource until the cursor is exhausted."""
    cursor: str | None = None
    for _ in range(max_pages):
        params: dict[str, Any] = {limit_param: page_size}
        if cursor:
            params[cursor_param] = cursor
        body = await fetch(params)
        items = body.get(items_key) or []
        for item in items:
            yield item
        next_cursor = body.get(next_cursor_key)
        if not next_cursor:
            return
        cursor = str(next_cursor)


async def offset_paginate(
    fetch: FetchFn,
    *,
    items_key: str,
    total_key: str | None = None,
    page_size: int = 50,
    offset_param: str = "offset",
    limit_param: str = "limit",
    max_pages: int = 1000,
) -> AsyncIterator[dict[str, Any]]:
    """Iterate an offset/limit-paginated resource until items run out."""
    offset = 0
    for _ in range(max_pages):
        params: dict[str, Any] = {offset_param: offset, limit_param: page_size}
        body = await fetch(params)
        items = body.get(items_key) or []
        count = 0
        for item in items:
            yield item
            count += 1
        if count == 0:
            return
        offset += count
        if total_key is not None:
            total = body.get(total_key)
            if isinstance(total, int) and offset >= total:
                return
