"""A2A protocol acceptance tests."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from httpx import ASGITransport
from mock_agents.creative_review import create_creative_review_app

from aih.a2a.client import A2AClient
from aih.a2a.models import JsonRpcRequest
from aih.agent.approval import APIApprover
from aih.observability.ledger import InMemoryLedger
from aih.service.app import create_app
from aih.service.deps import build_state


@pytest.fixture
def app_state():
    ledger = InMemoryLedger()
    approver = APIApprover()
    return build_state(ledger=ledger, approver=approver, memory=None)


@pytest.fixture
def app(app_state):
    return create_app(app_state)


@pytest.mark.asyncio
async def test_agent_card_served(app) -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/.well-known/agent-card.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "ai-integration-hub"
        assert any(s["id"] == "publish_creative" for s in data["skills"])


@pytest.mark.asyncio
async def test_a2a_jsonrpc_accepts_message_send(app, app_state) -> None:
    transport = ASGITransport(app=app)
    req = JsonRpcRequest(
        method="message/send",
        id="1",
        params={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "publish creative to creativebox"}],
            },
        },
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/a2a", json=req.model_dump())
        assert resp.status_code == 200
        body = resp.json()
        assert body["result"]["task"]["state"] in {"submitted", "working"}
        task_id = body["result"]["task"]["id"]

    for _ in range(80):
        await asyncio.sleep(0.05)
        trace = app_state.ledger.get(task_id)
        if trace and (trace.pending_approval() or trace.status != "running"):
            break
    assert trace is not None


@pytest.mark.asyncio
async def test_creative_review_peer_agent() -> None:
    peer = create_creative_review_app()
    transport = ASGITransport(app=peer)
    client = A2AClient(transport=transport)
    card = await client.fetch_agent_card("http://test/.well-known/agent-card.json")
    assert card.name == "creative-review-agent"
