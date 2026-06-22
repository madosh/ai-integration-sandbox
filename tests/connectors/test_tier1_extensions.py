"""Tier-1 extension tests: health, webhooks, cache, mapping, sync-all."""

from __future__ import annotations

import httpx
import pytest
from mock_apis.app import app as mock_app
from mock_apis.app import reset_state

from aih.connectors.cache import CONNECTOR_CACHE, TTLCache
from aih.connectors.health import check_connector_health
from aih.connectors.mapping import map_raw
from aih.llm import FakeLLM, HashEmbedder
from aih.rag.retriever import HybridRetriever
from aih.skills.base import SkillContext
from aih.skills.sync_all_connectors import SyncAllConnectors, SyncAllInput
from aih.skills.sync_campaign_data import SyncCampaignData, SyncCampaignInput


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_state()
    CONNECTOR_CACHE.clear()
    yield
    reset_state()
    CONNECTOR_CACHE.clear()


def test_map_raw_pulseads_cents() -> None:
    raw = {"campaign_id": "pa-1", "spend_cents": 1500, "label": "x", "state": "running"}
    mapped = map_raw("pulseads", "campaigns", raw)
    assert mapped["spend"] == 15.0
    assert mapped["id"] == "pa-1"


def test_ttl_cache_expires() -> None:
    cache = TTLCache[float](ttl_seconds=0.01)
    cache.set("k", 1.0)
    assert cache.get("k") == 1.0
    import time

    time.sleep(0.02)
    assert cache.get("k") is None


async def test_connector_health() -> None:
    transport = httpx.ASGITransport(app=mock_app)
    health = await check_connector_health("pulseads", httpx_transport=transport)
    assert health["status"] in ("healthy", "degraded")
    assert "circuit" in health


async def test_sync_all_connectors() -> None:
    ctx = SkillContext(
        llm=FakeLLM(),
        embedder=HashEmbedder(dim=256),
        retriever=HybridRetriever(embedder=HashEmbedder(dim=256)),
        httpx_transport=httpx.ASGITransport(app=mock_app),
    )
    out = await SyncAllConnectors().run(SyncAllInput(limit_per_connector=2), ctx)
    assert out.total_records >= 2
    assert len(out.connectors) >= 2


async def test_sync_campaign_cache() -> None:
    ctx = SkillContext(
        llm=FakeLLM(),
        embedder=HashEmbedder(dim=256),
        retriever=HybridRetriever(embedder=HashEmbedder(dim=256)),
        httpx_transport=httpx.ASGITransport(app=mock_app),
    )
    skill = SyncCampaignData()
    first = await skill.run(SyncCampaignInput(connector="novareach", limit=2), ctx)
    second = await skill.run(SyncCampaignInput(connector="novareach", limit=2), ctx)
    assert first.cached is False
    assert second.cached is True
