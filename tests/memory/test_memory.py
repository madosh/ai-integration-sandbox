"""Acceptance tests for the unified memory subsystem."""

from __future__ import annotations

import time

import pytest

from aih.agent.models import RunStep, RunTrace
from aih.llm.fake import HashEmbedder
from aih.memory.manager import MemoryManager
from aih.memory.models import MemoryItem, ProspectiveIntention
from aih.memory.store import MemoryStore
from aih.observability.ledger import InMemoryLedger
from aih.rag.retriever import HybridRetriever


@pytest.fixture
def memory(tmp_path) -> MemoryManager:
    store = MemoryStore(tmp_path / "mem.sqlite3")
    ledger = InMemoryLedger()
    embedder = HashEmbedder(dim=64)
    retriever = HybridRetriever(embedder=embedder)
    return MemoryManager(store=store, ledger=ledger, embedder=embedder, retriever=retriever)


def test_semantic_fact_cross_run_persistence(memory: MemoryManager) -> None:
    memory.remember(
        MemoryItem(
            type="semantic",
            tenant_id="t1",
            namespace="prefs",
            key="timezone",
            value="Europe/Madrid",
            confidence=0.9,
        )
    )
    recalled = memory.semantic.recall_by_key("t1", "prefs", "timezone")
    assert recalled is not None
    assert "Europe/Madrid" in recalled.text


def test_episodic_flags_failed_approach(memory: MemoryManager) -> None:
    failed = RunTrace(run_id="r1", goal="publish creative to creativebox", status="denied")
    failed.add(RunStep(index=0, kind="approval", skill="publish_creative", message="denied"))
    memory.reflect(failed, tenant_id="t1")

    similar = memory.episodic.recall_similar("publish creative to creativebox", tenant_id="t1")
    assert similar
    assert "FAILED BEFORE" in similar[0].text or similar[0].metadata.get("outcome") == "denied"


@pytest.mark.asyncio
async def test_prospective_intention_surfaces_when_due(memory: MemoryManager) -> None:
    memory.prospective.schedule(
        ProspectiveIntention(
            tenant_id="t1",
            goal="sync pulseads campaigns",
            trigger_type="time",
            trigger_at=time.time() - 1,
        )
    )
    assembled = await memory.assemble_working_memory("any goal", budget=2000, tenant_id="t1")
    assert any("DUE INTENTION" in f.text for f in assembled.fragments)


@pytest.mark.asyncio
async def test_assemble_respects_budget_and_provenance(memory: MemoryManager) -> None:
    for i in range(20):
        memory.remember(
            MemoryItem(
                type="semantic",
                tenant_id="t1",
                namespace="facts",
                key=f"k{i}",
                value=f"long fact value number {i} " * 5,
                confidence=0.5 + i * 0.01,
            )
        )
    assembled = await memory.assemble_working_memory("facts", budget=80, tenant_id="t1")
    assert assembled.total_tokens <= 80
    assert assembled.fragments
    assert all(f.provenance for f in assembled.fragments)


def test_consolidate_creates_procedural_heuristic(memory: MemoryManager) -> None:
    for i in range(3):
        trace = RunTrace(run_id=f"ok{i}", goal="sync novareach campaigns", status="completed")
        trace.add(
            RunStep(index=0, kind="skill", skill="sync_campaign_data", message="ok", result={"count": 1})
        )
        memory.reflect(trace, tenant_id="t1")
    report = memory.consolidate(tenant_id="t1")
    assert report.heuristics_created >= 1
    learned = memory.procedural.learned("t1")
    assert any("NovaReach" in h.text or "novareach" in h.text.lower() for h in learned)


def test_tenant_isolation_and_delete_subject(memory: MemoryManager) -> None:
    memory.remember(
        MemoryItem(
            type="semantic",
            tenant_id="tenant-a",
            subject_id="user-1",
            namespace="n",
            key="k",
            value="a",
        )
    )
    memory.remember(
        MemoryItem(
            type="semantic",
            tenant_id="tenant-b",
            subject_id="user-2",
            namespace="n",
            key="k",
            value="b",
        )
    )
    assert memory.semantic.recall_by_key("tenant-a", "n", "k") is not None
    assert memory.semantic.recall_by_key("tenant-b", "n", "k") is not None
    deleted = memory.delete_subject("user-1")
    assert deleted >= 1
    assert memory.semantic.recall_by_key("tenant-a", "n", "k") is None
