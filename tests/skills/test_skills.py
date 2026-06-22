"""Each skill is testable in isolation (mock APIs + FakeLLM, fully offline)."""

from __future__ import annotations

import base64
from collections.abc import Iterator

import httpx
import pytest
from mock_apis.app import app as mock_app
from mock_apis.app import reset_state

from aih.llm import FakeLLM, HashEmbedder
from aih.rag.retriever import HybridRetriever
from aih.skills.answer_from_docs import AnswerFromDocs, AnswerInput
from aih.skills.base import SkillContext
from aih.skills.publish_creative import PublishCreative, PublishCreativeInput
from aih.skills.registry import SKILLS, default_registry
from aih.skills.sync_campaign_data import SyncCampaignData, SyncCampaignInput


@pytest.fixture(autouse=True)
def _reset() -> Iterator[None]:
    reset_state()
    yield
    reset_state()


@pytest.fixture
def ctx() -> SkillContext:
    return SkillContext(
        llm=FakeLLM(),
        retriever=HybridRetriever(embedder=HashEmbedder(dim=256)),
        embedder=HashEmbedder(dim=256),
        httpx_transport=httpx.ASGITransport(app=mock_app),
    )


def test_registry_lists_skills_with_side_effect_flags() -> None:
    described = {d["name"]: d for d in default_registry().describe()}
    assert set(described) == {
        "sync_campaign_data",
        "sync_all_connectors",
        "publish_creative",
        "answer_from_docs",
    }
    assert described["publish_creative"]["side_effect"] is True
    assert described["sync_campaign_data"]["side_effect"] is False
    # tool specs carry real input schemas for the planner
    specs = {s.name: s for s in SKILLS.tool_specs()}
    assert "properties" in specs["publish_creative"].parameters


async def test_sync_campaign_data(ctx: SkillContext) -> None:
    out = await SyncCampaignData().run(SyncCampaignInput(connector="novareach"), ctx)
    assert out.count == 4
    assert out.total_spend == pytest.approx(1670.0)
    assert out.summary  # FakeLLM produced a deterministic summary


async def test_publish_creative_uploads(ctx: SkillContext) -> None:
    content = base64.b64encode(b"banner-bytes").decode("ascii")
    out = await PublishCreative().run(
        PublishCreativeInput(connector="creativebox", name="banner.png", content_b64=content),
        ctx,
    )
    assert out.partner == "creativebox"
    assert out.status == "created"
    assert out.id.startswith("cb-")


async def test_answer_from_docs_cites_sources(ctx: SkillContext) -> None:
    out = await AnswerFromDocs().run(
        AnswerInput(question="how do I handle a 429 rate limit", k=3), ctx
    )
    assert out.answer
    assert out.citations
    assert out.citations[0].source.startswith("doc:")
