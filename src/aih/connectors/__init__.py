"""REST integration layer.

Reusable connectors that consume (GET) and publish (PUSH) data/files/creatives
across multiple partner APIs with differing auth and pagination conventions.
See ``specs/connectors.md``.
"""

from __future__ import annotations

from aih.connectors.base import Connector, ConnectorConfig, idempotency_key
from aih.connectors.errors import (
    AuthError,
    CircuitOpenError,
    ConnectorError,
    NotFoundError,
    RateLimitedError,
    UpstreamError,
)
from aih.connectors.models import Campaign, Creative, PushResult
from aih.connectors.registry import REGISTRY, ConnectorRegistry, default_config, default_registry

__all__ = [
    "REGISTRY",
    "AuthError",
    "Campaign",
    "CircuitOpenError",
    "Connector",
    "ConnectorConfig",
    "ConnectorError",
    "ConnectorRegistry",
    "Creative",
    "NotFoundError",
    "PushResult",
    "RateLimitedError",
    "UpstreamError",
    "default_config",
    "default_registry",
    "idempotency_key",
]
