"""NovaReach connector: API-key header auth, offset/limit pagination."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from aih.connectors.base import Connector, ConnectorConfig, idempotency_key
from aih.connectors.models import Campaign, CampaignStatus, PushResult
from aih.connectors.paginate import offset_paginate

_STATUS_MAP: dict[str, CampaignStatus] = {
    "active": "active",
    "paused": "paused",
    "archived": "archived",
}


class NovaReachConnector(Connector):
    """Connector for the NovaReach partner API."""

    name = "novareach"

    def get_records(
        self, resource: str = "campaigns", *, filters: dict[str, object] | None = None
    ) -> AsyncIterator[Campaign]:
        async def fetch(params: dict[str, Any]) -> dict[str, Any]:
            merged = {**(filters or {}), **params}
            resp = await self.transport.request("GET", f"/novareach/{resource}", params=merged)
            data: dict[str, Any] = resp.json()
            return data

        pages = offset_paginate(fetch, items_key="records", total_key="total", page_size=2)

        async def _iter() -> AsyncIterator[Campaign]:
            async for raw in pages:
                yield self._normalize(raw)

        return _iter()

    async def push_record(self, record: Campaign) -> PushResult:
        payload = {
            "id": record.id,
            "title": record.name,
            "status": record.status,
            "budget": record.spend,
        }
        resp = await self.transport.request(
            "POST",
            "/novareach/campaigns",
            json=payload,
            headers={"Idempotency-Key": idempotency_key(payload)},
        )
        body = resp.json()
        return PushResult(
            id=str(body.get("id", record.id)),
            partner=self.name,
            status="duplicate" if body.get("duplicate") else "created",
            idempotent_hit=bool(body.get("duplicate")),
        )

    def _normalize(self, raw: dict[str, Any]) -> Campaign:
        return Campaign(
            id=str(raw.get("id", "")),
            partner=self.name,
            name=str(raw.get("title", "")),
            status=_STATUS_MAP.get(str(raw.get("status", "")), "unknown"),
            spend=float(raw.get("budget", 0.0)),
            metric=int(raw.get("impressions", 0)),
            raw=raw,
        )


def build(config: ConnectorConfig) -> NovaReachConnector:
    """Registry factory."""
    return NovaReachConnector(config)
