"""End-to-end agent runs exercising the human-in-the-loop approval gate.

NOTE: CreativeBox is the creative-capable partner in this sandbox (NovaReach handles
campaign records), so the publish goal targets CreativeBox. The gate behaviour is
connector-agnostic.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import httpx
import pytest
from mock_apis.app import STATE as MOCK_STATE
from mock_apis.app import app as mock_app
from mock_apis.app import reset_state

from aih.agent.approval import APIApprover, AutoApprover
from aih.agent.orchestrator import Agent
from aih.llm import FakeLLM, HashEmbedder
from aih.observability.ledger import InMemoryLedger
from aih.rag.retriever import HybridRetriever
from aih.skills.base import SkillContext
from aih.skills.registry import default_registry

GOAL = "publish the new creative to creativebox"


@pytest.fixture(autouse=True)
def _reset() -> Iterator[None]:
    reset_state()
    yield
    reset_state()


def _ctx() -> SkillContext:
    return SkillContext(
        llm=FakeLLM(),
        retriever=HybridRetriever(embedder=HashEmbedder(dim=256)),
        embedder=HashEmbedder(dim=256),
        httpx_transport=httpx.ASGITransport(app=mock_app),
    )


def _agent(approver) -> Agent:  # type: ignore[no-untyped-def]
    return Agent(
        llm=FakeLLM(),
        skills=default_registry(),
        approver=approver,
        ledger=InMemoryLedger(),
        ctx=_ctx(),
        max_steps=6,
    )


async def test_approved_run_uploads_creative() -> None:
    agent = _agent(AutoApprover(True))
    result = await agent.run(GOAL)

    kinds = [s.kind for s in result.trace.steps]
    assert "plan" in kinds
    assert "approval" in kinds
    assert "skill" in kinds  # the upload executed

    approval_step = next(s for s in result.trace.steps if s.kind == "approval")
    assert approval_step.decision is not None
    assert approval_step.decision.approved is True

    # A creative actually landed on the mock store.
    assert len(MOCK_STATE.creatives) == 1
    assert result.trace.value_summary["creatives_pushed"] == 1


async def test_denied_run_leaves_no_side_effects() -> None:
    agent = _agent(AutoApprover(False))
    result = await agent.run(GOAL)

    assert result.trace.status == "denied"
    approval_step = next(s for s in result.trace.steps if s.kind == "approval")
    assert approval_step.decision is not None
    assert approval_step.decision.approved is False
    # No skill step executed; nothing uploaded.
    assert all(s.kind != "skill" for s in result.trace.steps)
    assert MOCK_STATE.creatives == {}


async def test_api_approver_resolves_externally() -> None:
    approver = APIApprover()
    agent = _agent(approver)

    run_task = asyncio.create_task(agent.run(GOAL))

    # Wait for the agent to park a pending approval, then resolve it (as the API would).
    for _ in range(100):
        pending = approver.pending()
        if pending:
            break
        await asyncio.sleep(0.01)
    assert pending, "expected a pending approval"
    run_id = next(iter(pending))
    assert approver.resolve(run_id, approved=True)

    result = await run_task
    assert result.trace.status == "completed"
    assert len(MOCK_STATE.creatives) == 1


async def test_run_trace_persisted_to_ledger() -> None:
    ledger = InMemoryLedger()
    agent = Agent(
        llm=FakeLLM(),
        skills=default_registry(),
        approver=AutoApprover(True),
        ledger=ledger,
        ctx=_ctx(),
        max_steps=6,
    )
    result = await agent.run(GOAL)
    fetched = ledger.get(result.trace.run_id)
    assert fetched is not None
    assert fetched.goal == GOAL
    assert fetched.steps
