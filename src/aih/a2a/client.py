"""A2A client — discover Agent Card and delegate tasks."""

from __future__ import annotations

from typing import Any

import httpx

from aih.a2a.models import AgentCard, Artifact, JsonRpcRequest, JsonRpcResponse, Message, TextPart
from aih.a2a.server import sanitize_artifact


class A2AClient:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def fetch_agent_card(self, url: str) -> AgentCard:
        async with httpx.AsyncClient(transport=self._transport) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return AgentCard.model_validate(resp.json())

    async def send_task(
        self,
        endpoint: str,
        goal: str,
        *,
        webhook_url: str | None = None,
        rpc_id: str = "1",
    ) -> dict[str, Any]:
        req = JsonRpcRequest(
            method="message/send",
            id=rpc_id,
            params={
                "message": Message(parts=[TextPart(text=goal)]).model_dump(),
                "webhook_url": webhook_url,
            },
        )
        async with httpx.AsyncClient(transport=self._transport) as client:
            resp = await client.post(endpoint, json=req.model_dump())
            resp.raise_for_status()
            data = JsonRpcResponse.model_validate(resp.json())
            if data.error:
                raise RuntimeError(data.error.get("message", "rpc error"))
            return data.result or {}

    def parse_peer_artifact(self, artifact: Artifact) -> Artifact:
        return sanitize_artifact(artifact)
