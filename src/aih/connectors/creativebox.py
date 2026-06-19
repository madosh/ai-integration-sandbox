"""CreativeBox connector: basic auth, multipart creative upload + download."""

from __future__ import annotations

import hashlib

from aih.connectors.base import Connector, ConnectorConfig, idempotency_key
from aih.connectors.models import Creative, PushResult


class CreativeBoxConnector(Connector):
    """Connector for the CreativeBox asset store (PUSH/GET of creatives)."""

    name = "creativebox"

    async def push_creative(
        self, *, name: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> PushResult:
        checksum = hashlib.sha256(content).hexdigest()
        key = idempotency_key({"name": name, "checksum": checksum})
        resp = await self.transport.request(
            "POST",
            "/creativebox/creatives",
            files={"file": (name, content, content_type)},
            data={"name": name},
            headers={"Idempotency-Key": key},
        )
        body = resp.json()
        return PushResult(
            id=str(body["id"]),
            partner=self.name,
            status="duplicate" if body.get("duplicate") else "created",
            idempotent_hit=bool(body.get("duplicate")),
            detail=f"checksum={checksum[:12]}",
        )

    async def get_creative(self, creative_id: str) -> tuple[Creative, bytes]:
        resp = await self.transport.request("GET", f"/creativebox/creatives/{creative_id}")
        content = resp.content
        meta = Creative(
            id=creative_id,
            partner=self.name,
            name=resp.headers.get("X-Creative-Name", creative_id),
            content_type=resp.headers.get("Content-Type", "application/octet-stream"),
            size_bytes=len(content),
            checksum=resp.headers.get("X-Creative-Checksum"),
        )
        return meta, content


def build(config: ConnectorConfig) -> CreativeBoxConnector:
    """Registry factory."""
    return CreativeBoxConnector(config)
