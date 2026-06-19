"""Connector base classes (skeleton).

TODO (Phase 1): Connector ABC + ConnectorConfig (Pydantic), pluggable AuthStrategy
(Bearer / ApiKey / Basic), and a shared async httpx transport with retries
(exponential backoff + jitter), Retry-After handling on 429, timeouts, a circuit
breaker, and structured request/response logging.
"""

from __future__ import annotations

__all__: list[str] = []
