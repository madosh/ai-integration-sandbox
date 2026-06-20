"""Kata 6: async token-bucket rate limiter."""

from __future__ import annotations

import asyncio
import time

import pytest

from drills.katas.rate_limiter import TokenBucket


async def test_rate_limits_burst() -> None:
    bucket = TokenBucket(rate=10, capacity=2)
    start = time.monotonic()
    await bucket.acquire()
    await bucket.acquire()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.08  # third token waits ~0.1s at 10/sec
