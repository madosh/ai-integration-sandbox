"""Connector registry — the discoverable "integrations framework".

Connectors are registered by name with a factory that builds them from a
:class:`ConnectorConfig`. Adding a partner is a new module + one ``register`` call.
Default configs wire each partner at the configured mock-API base URL with creds
sourced from settings.
"""

from __future__ import annotations

from collections.abc import Callable

from aih.config import get_settings
from aih.connectors.auth import ApiKeyAuth, AuthStrategy, BasicAuth, BearerAuth
from aih.connectors.base import Connector, ConnectorConfig
from aih.connectors.creativebox import build as build_creativebox
from aih.connectors.novareach import build as build_novareach
from aih.connectors.pulseads import build as build_pulseads

ConnectorFactory = Callable[[ConnectorConfig], Connector]


class ConnectorRegistry:
    """Registry of connector factories keyed by partner name."""

    def __init__(self) -> None:
        self._factories: dict[str, ConnectorFactory] = {}

    def register(self, name: str, factory: ConnectorFactory) -> None:
        self._factories[name] = factory

    def names(self) -> list[str]:
        return sorted(self._factories)

    def has(self, name: str) -> bool:
        return name in self._factories

    def build(self, name: str, config: ConnectorConfig) -> Connector:
        if name not in self._factories:
            raise KeyError(f"unknown connector: {name!r}; known: {self.names()}")
        return self._factories[name](config)

    def get(self, name: str) -> Connector:
        """Build a connector using its default (settings-derived) config."""
        return self.build(name, default_config(name))


def default_config(
    name: str,
    *,
    httpx_transport: object | None = None,
    sleep: object | None = None,
) -> ConnectorConfig:
    """Build a partner's default config from settings (points at the mock API)."""
    settings = get_settings()
    base = settings.mock_api_base_url
    auth_map: dict[str, Callable[[], AuthStrategy]] = {
        "pulseads": lambda: BearerAuth(settings.pulseads_token),
        "novareach": lambda: ApiKeyAuth(settings.novareach_api_key),
        "creativebox": lambda: BasicAuth(settings.creativebox_user, settings.creativebox_password),
    }
    auth_factory = auth_map.get(name)
    if auth_factory is None:
        raise KeyError(f"no default config for connector: {name!r}")
    return ConnectorConfig(
        base_url=base,
        auth=auth_factory(),
        httpx_transport=httpx_transport,  # type: ignore[arg-type]
        sleep=sleep,  # type: ignore[arg-type]
    )


def default_registry() -> ConnectorRegistry:
    """The built-in registry with the three partners pre-registered."""
    reg = ConnectorRegistry()
    reg.register("pulseads", build_pulseads)
    reg.register("novareach", build_novareach)
    reg.register("creativebox", build_creativebox)
    return reg


#: Process-wide default registry.
REGISTRY = default_registry()
