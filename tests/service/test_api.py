"""HTTP integration tests for the FastAPI service."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import httpx
import pytest
from mock_apis.app import STATE as MOCK_STATE
from mock_apis.app import app as mock_app
from mock_apis.app import reset_state

from aih.agent.approval import APIApprover
from aih.observability.ledger import InMemoryLedger
from aih.service.app import create_app
from aih.service.deps import build_state

GOAL = "publish the new creative to creativebox"


@pytest.fixture(autouse=True)
def _reset() -> Iterator[None]:
    reset_state()
    yield
    reset_state()


@pytest.fixture
def client() -> httpx.AsyncClient:
    approver = APIApprover()
    state = build_state(
        ledger=InMemoryLedger(),
        approver=approver,
        httpx_transport=httpx.ASGITransport(app=mock_app),
    )
    app = create_app(state)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_healthz(client: httpx.AsyncClient) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_registries(client: httpx.AsyncClient) -> None:
    connectors = await client.get("/connectors")
    skills = await client.get("/skills")
    assert connectors.status_code == 200
    assert len(connectors.json()) >= 3
    assert skills.status_code == 200
    assert len(skills.json()) >= 3


async def test_search(client: httpx.AsyncClient) -> None:
    r = await client.post("/search", json={"query": "Retry-After rate limit", "k": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["chunks"]
    assert body["confidence"] in ("high", "medium", "low")


async def test_connector_health(client: httpx.AsyncClient) -> None:
    r = await client.get("/connectors/pulseads/health")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "pulseads"
    assert "circuit" in body


async def test_webhook_and_chat(client: httpx.AsyncClient) -> None:
    wh = await client.post("/webhooks/pulseads", json={"payload": {"event": "campaign.updated"}})
    assert wh.status_code == 200
    assert wh.json()["status"] == "received"
    listed = await client.get("/webhooks?partner=pulseads")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    chat = await client.post(
        "/chat",
        json={"thread_id": "t1", "message": "HTTP 429 Retry-After backoff"},
    )
    assert chat.status_code == 200
    assert chat.json()["answer"]


async def test_full_run_with_approval(client: httpx.AsyncClient) -> None:
    start = await client.post("/runs", json={"goal": GOAL})
    assert start.status_code == 200
    run_id = start.json()["run_id"]

    # Poll until approval is pending or run completes
    for _ in range(200):
        detail = await client.get(f"/runs/{run_id}")
        body = detail.json()
        if body.get("pending_approval"):
            approve = await client.post(f"/runs/{run_id}/approve", json={"approved": True})
            assert approve.status_code == 200
            break
        if body["status"] != "running":
            break
        await asyncio.sleep(0.02)

    for _ in range(200):
        detail = await client.get(f"/runs/{run_id}")
        if detail.json()["status"] != "running":
            break
        await asyncio.sleep(0.02)

    final = (await client.get(f"/runs/{run_id}")).json()
    assert final["status"] == "completed"
    assert len(MOCK_STATE.creatives) == 1

    metrics = await client.get("/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["total_runs"] >= 1
