"""TODO: async token bucket rate limiter."""

from __future__ import annotations


class TokenBucket:
    def __init__(self, rate: float, capacity: int) -> None:
        self.rate = rate
        self.capacity = capacity

    async def acquire(self) -> None:
        """Wait until a token is available — NOT IMPLEMENTED."""
        return None
