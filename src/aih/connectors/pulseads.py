"""PulseAds connector: Bearer auth, cursor pagination, rate-limited (429)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from aih.connectors.base import Connector, ConnectorConfig
from aih.connectors.models import Campaign, CampaignStatus
from aih.connectors.paginate import cursor_paginate

_STATUS_MAP: dict[str, CampaignStatus] = {
    "running": "active",
    "paused": "paused",
    "stopped": "archived",
}


class PulseAdsConnector(Connector):
    """Connector for the PulseAds partner API."""

    name = "pulseads"

    def get_records(
        self, resource: str = "campaigns", *, filters: dict[str, object] | None = None
    ) -> AsyncIterator[Campaign]:
        async def fetch(params: dict[str, Any]) -> dict[str, Any]:
            merged = {**(filters or {}), **params}
            resp = await self.transport.request("GET", f"/pulseads/{resource}", params=merged)
            data: dict[str, Any] = resp.json()
            return data

        pages = cursor_paginate(
            fetch, items_key="items", next_cursor_key="next_cursor", page_size=2
        )

        async def _iter() -> AsyncIterator[Campaign]:
            async for raw in pages:
                yield self._normalize(raw)

        return _iter()

    def _normalize(self, raw: dict[str, Any]) -> Campaign:
        return Campaign(
            id=str(raw.get("campaign_id", "")),
            partner=self.name,
            name=str(raw.get("label", "")),
            status=_STATUS_MAP.get(str(raw.get("state", "")), "unknown"),
            spend=round(int(raw.get("spend_cents", 0)) / 100, 2),
            metric=int(raw.get("clicks", 0)),
            raw=raw,
        )


def build(config: ConnectorConfig) -> PulseAdsConnector:
    """Registry factory."""
    return PulseAdsConnector(config)
