"""TODO: implement exponential backoff with jitter retry decorator."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 0.1,
    jitter: float = 0.1,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Retry an async callable — NOT IMPLEMENTED (kata)."""

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return await fn(*args, **kwargs)

        return wrapper

    return decorator
