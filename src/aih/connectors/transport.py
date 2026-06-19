"""Shared async HTTP transport.

Wraps ``httpx.AsyncClient`` with the cross-cutting concerns every connector needs:
retries (exponential backoff + jitter), ``Retry-After`` handling on 429, timeouts,
a circuit breaker, and structured request/response logging.

Connector modules MUST go through this; they never touch ``httpx`` directly.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

from aih.connectors.errors import (
    AuthError,
    CircuitOpenError,
    NotFoundError,
    RateLimitedError,
    UpstreamError,
)
from aih.observability.logging import get_logger, log_context

SleepFn = Callable[[float], Awaitable[None]]

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass
class RetryPolicy:
    """Bounded retry/backoff configuration."""

    max_attempts: int = 4
    base_delay: float = 0.02
    max_delay: float = 0.2
    jitter: float = 0.5  # fraction of delay added as random jitter

    def backoff(self, attempt: int, rng: random.Random) -> float:
        """Exponential backoff with jitter for a 0-indexed attempt number."""
        delay = min(self.max_delay, self.base_delay * (2**attempt))
        return float(delay + rng.random() * self.jitter * delay)


@dataclass
class CircuitBreaker:
    """Trip after ``threshold`` consecutive failures; cool down before retrying."""

    threshold: int = 5
    cooldown: float = 5.0
    _failures: int = field(default=0, init=False)
    _opened_at: float | None = field(default=None, init=False)
    _now: Callable[[], float] = time.monotonic

    def allow(self) -> bool:
        if self._opened_at is None:
            return True
        if self._now() - self._opened_at >= self.cooldown:
            # half-open: allow a trial request
            self._opened_at = None
            self._failures = 0
            return True
        return False

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = self._now()

    @property
    def is_open(self) -> bool:
        return self._opened_at is not None


class Transport:
    """An async HTTP transport shared by all connectors."""

    def __init__(
        self,
        *,
        base_url: str,
        name: str = "transport",
        default_headers: dict[str, str] | None = None,
        timeout: float = 10.0,
        retry: RetryPolicy | None = None,
        breaker: CircuitBreaker | None = None,
        sleep: SleepFn = asyncio.sleep,
        httpx_transport: httpx.AsyncBaseTransport | None = None,
        rng_seed: int | None = 1234,
    ) -> None:
        self.name = name
        self._base_url = base_url
        self._default_headers = default_headers or {}
        self._retry = retry or RetryPolicy()
        self._breaker = breaker or CircuitBreaker()
        self._sleep = sleep
        self._rng = random.Random(rng_seed)
        self._log: logging.Logger = get_logger(f"aih.connectors.{name}")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=httpx_transport,
        )

    async def __aenter__(self) -> Transport:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: Any = None,
        json: Any = None,
        files: Any = None,
        data: Any = None,
    ) -> httpx.Response:
        """Perform a request with retries, backoff, and circuit breaking."""
        if not self._breaker.allow():
            raise CircuitOpenError("circuit open; failing fast", connector=self.name)

        merged = {**self._default_headers, **(headers or {})}
        last_exc: Exception | None = None

        for attempt in range(self._retry.max_attempts):
            started = time.monotonic()
            try:
                resp = await self._client.request(
                    method,
                    path,
                    headers=merged,
                    params=params,
                    json=json,
                    files=files,
                    data=data,
                )
            except httpx.TransportError as exc:
                last_exc = exc
                self._breaker.record_failure()
                log_context(
                    self._log,
                    logging.WARNING,
                    "request.transport_error",
                    connector=self.name,
                    method=method,
                    path=path,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt + 1 < self._retry.max_attempts:
                    await self._sleep(self._retry.backoff(attempt, self._rng))
                    continue
                raise UpstreamError(str(exc), connector=self.name) from exc

            elapsed_ms = round((time.monotonic() - started) * 1000, 2)
            log_context(
                self._log,
                logging.INFO,
                "request.response",
                connector=self.name,
                method=method,
                path=path,
                status=resp.status_code,
                attempt=attempt,
                elapsed_ms=elapsed_ms,
            )

            if resp.status_code in _RETRYABLE_STATUS:
                self._breaker.record_failure()
                if attempt + 1 < self._retry.max_attempts:
                    delay = self._retry_delay(resp, attempt)
                    await self._sleep(delay)
                    continue
                return self._raise_for_exhausted(resp)

            self._breaker.record_success()
            return self._raise_for_status(resp)

        # Should be unreachable, but keep the type checker happy.
        raise UpstreamError(str(last_exc) if last_exc else "unknown", connector=self.name)

    def _retry_delay(self, resp: httpx.Response, attempt: int) -> float:
        """Honor Retry-After on 429, else exponential backoff + jitter."""
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    return max(0.0, float(retry_after))
                except ValueError:
                    pass
        return self._retry.backoff(attempt, self._rng)

    def _raise_for_status(self, resp: httpx.Response) -> httpx.Response:
        if resp.status_code in (401, 403):
            raise AuthError(f"auth failed ({resp.status_code})", connector=self.name)
        if resp.status_code == 404:
            raise NotFoundError("not found", connector=self.name)
        if resp.status_code >= 400:
            raise UpstreamError(f"unexpected status {resp.status_code}", connector=self.name)
        return resp

    def _raise_for_exhausted(self, resp: httpx.Response) -> httpx.Response:
        if resp.status_code == 429:
            raise RateLimitedError("rate limited; retries exhausted", connector=self.name)
        raise UpstreamError(f"upstream {resp.status_code}; retries exhausted", connector=self.name)
