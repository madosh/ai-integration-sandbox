"""Typed connector errors.

These let callers (and the MCP/agent layers) react to failures structurally
instead of parsing stack traces.
"""

from __future__ import annotations


class ConnectorError(Exception):
    """Base class for all connector failures."""

    def __init__(self, message: str, *, connector: str | None = None) -> None:
        super().__init__(message)
        self.connector = connector


class AuthError(ConnectorError):
    """Authentication/authorization failed (HTTP 401/403). Not retried."""


class NotFoundError(ConnectorError):
    """Requested resource does not exist (HTTP 404)."""


class RateLimitedError(ConnectorError):
    """Rate limit exceeded and retry budget exhausted (HTTP 429)."""


class UpstreamError(ConnectorError):
    """Upstream/server or network error after retries (HTTP 5xx / transport)."""


class CircuitOpenError(ConnectorError):
    """The circuit breaker is open; calls fail fast until cooldown elapses."""
