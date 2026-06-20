"""Kata 1: backoff + jitter retry decorator — implement in backoff.py."""

from __future__ import annotations

import pytest

from drills.katas.backoff import retry_with_backoff


class Flaky:
    def __init__(self) -> None:
        self.calls = 0

    @retry_with_backoff(max_attempts=4, base_delay=0.01, jitter=0.0)
    async def run(self) -> str:
        self.calls += 1
        if self.calls < 3:
            raise ConnectionError("transient")
        return "ok"


async def test_retries_until_success() -> None:
    f = Flaky()
    result = await f.run()
    assert result == "ok"
    assert f.calls == 3
