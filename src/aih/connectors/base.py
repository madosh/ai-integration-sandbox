"""Connector base classes.

A :class:`Connector` owns a :class:`ConnectorConfig` and a shared
:class:`~aih.connectors.transport.Transport`. Subclasses implement the
partner-specific extraction (GET) and publishing (PUSH) plus the mapping from raw
payloads to normalized domain models.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx

from aih.connectors.auth import AuthStrategy, NoAuth
from aih.connectors.models import Campaign, Creative, PushResult
from aih.connectors.transport import CircuitBreaker, RetryPolicy, SleepFn, Transport


@dataclass
class ConnectorConfig:
    """Everything a connector needs to talk to its partner.

    ``httpx_transport`` lets tests mount the mock app in-process (offline) via
    ``httpx.ASGITransport`` while production uses a real socket transport.
    """

    base_url: str
    auth: AuthStrategy = field(default_factory=NoAuth)
    timeout: float = 10.0
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    breaker: CircuitBreaker = field(default_factory=CircuitBreaker)
    httpx_transport: httpx.AsyncBaseTransport | None = None
    sleep: SleepFn | None = None


def idempotency_key(payload: object) -> str:
    """Deterministic key derived from payload content (for safe re-pushes)."""
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:32]


class Connector:
    """Base class for all partner connectors.

    Subclasses override the operations their partner supports (``get_records`` for
    extraction, ``push_record`` / ``push_creative`` / ``get_creative`` for publishing).
    Unsupported operations raise ``NotImplementedError`` with a clear message.
    """

    #: Stable partner name used by the registry and normalized models.
    name: str = "connector"

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        sleep_kwargs = {} if config.sleep is None else {"sleep": config.sleep}
        self.transport = Transport(
            base_url=config.base_url,
            name=self.name,
            default_headers=config.auth.headers(),
            timeout=config.timeout,
            retry=config.retry,
            breaker=config.breaker,
            httpx_transport=config.httpx_transport,
            **sleep_kwargs,  # type: ignore[arg-type]
        )

    async def aclose(self) -> None:
        await self.transport.aclose()

    async def __aenter__(self) -> Connector:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # --- extraction (GET) ---------------------------------------------------
    def get_records(
        self, resource: str = "campaigns", *, filters: dict[str, object] | None = None
    ) -> AsyncIterator[Campaign]:
        """Yield normalized records, paginating transparently. Override where supported."""
        raise NotImplementedError(f"{self.name} does not support get_records")

    # --- publishing (PUSH) --------------------------------------------------
    async def push_record(self, record: Campaign) -> PushResult:
        """Publish a record back to the partner. Override where supported."""
        raise NotImplementedError(f"{self.name} does not support push_record")

    async def push_creative(
        self, *, name: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> PushResult:
        """Upload a creative asset. Override where supported (multipart PUSH)."""
        raise NotImplementedError(f"{self.name} does not support push_creative")

    async def get_creative(self, creative_id: str) -> tuple[Creative, bytes]:
        """Download a previously uploaded creative. Override where supported."""
        raise NotImplementedError(f"{self.name} does not support get_creative")
