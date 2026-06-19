"""Pluggable authentication strategies.

Each strategy knows how to attach its credentials to an outgoing request's
headers. Connectors stay agnostic about the auth scheme.
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod


class AuthStrategy(ABC):
    """Attach credentials to outgoing request headers."""

    @abstractmethod
    def headers(self) -> dict[str, str]:
        """Return headers to merge into each request."""


class NoAuth(AuthStrategy):
    """No authentication (used by trivial/example connectors)."""

    def headers(self) -> dict[str, str]:
        return {}


class BearerAuth(AuthStrategy):
    """``Authorization: Bearer <token>`` (PulseAds)."""

    def __init__(self, token: str) -> None:
        self._token = token

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}


class ApiKeyAuth(AuthStrategy):
    """A custom API-key header (NovaReach: ``X-API-Key``)."""

    def __init__(self, key: str, *, header: str = "X-API-Key") -> None:
        self._key = key
        self._header = header

    def headers(self) -> dict[str, str]:
        return {self._header: self._key}


class BasicAuth(AuthStrategy):
    """HTTP Basic auth (CreativeBox)."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    def headers(self) -> dict[str, str]:
        raw = f"{self._username}:{self._password}".encode()
        token = base64.b64encode(raw).decode("ascii")
        return {"Authorization": f"Basic {token}"}
