"""Prove a 4th partner needs only a new module + a registry entry.

This is the "integrations framework" claim: extending the system does not require
touching the core. Here we define a tiny example connector inline and register it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from mock_apis.app import app as mock_app

from aih.connectors.auth import ApiKeyAuth
from aih.connectors.base import Connector, ConnectorConfig
from aih.connectors.models import Campaign
from aih.connectors.paginate import offset_paginate
from aih.connectors.registry import default_registry


class ExampleConnector(Connector):
    """A 4th partner added without modifying any core module."""

    name = "example"

    def get_records(
        self, resource: str = "campaigns", *, filters: dict[str, object] | None = None
    ) -> AsyncIterator[Campaign]:
        async def fetch(params: dict[str, object]) -> dict[str, object]:
            resp = await self.transport.request("GET", "/novareach/campaigns", params=params)
            return resp.json()

        pages = offset_paginate(fetch, items_key="records", total_key="total", page_size=2)

        async def _iter() -> AsyncIterator[Campaign]:
            async for raw in pages:
                yield Campaign(id=str(raw["id"]), partner=self.name, name=str(raw["title"]))

        return _iter()


def build(config: ConnectorConfig) -> ExampleConnector:
    return ExampleConnector(config)


async def test_register_and_use_new_connector() -> None:
    registry = default_registry()
    assert "example" not in registry.names()

    registry.register("example", build)  # the single line to add a partner
    assert registry.has("example")

    config = ConnectorConfig(
        base_url="http://test",
        auth=ApiKeyAuth("nova-demo-key"),
        httpx_transport=httpx.ASGITransport(app=mock_app),
    )
    connector = registry.build("example", config)
    records = [c async for c in connector.get_records()]
    await connector.aclose()

    assert len(records) == 4
    assert all(r.partner == "example" for r in records)


def test_unknown_connector_raises_keyerror() -> None:
    registry = default_registry()
    try:
        registry.build("does-not-exist", ConnectorConfig(base_url="http://test"))
    except KeyError as exc:
        assert "unknown connector" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected KeyError")
