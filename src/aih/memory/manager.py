"""MemoryManager — unifies all memory types."""

from __future__ import annotations

from typing import Any

from aih.agent.models import RunTrace
from aih.config import get_settings
from aih.llm.base import Embedder, LLMClient
from aih.memory.episodic import EpisodicMemory
from aih.memory.external import ExternalMemory
from aih.memory.models import (
    AssembledContext,
    ConsolidationReport,
    MemoryItem,
    MemoryType,
    ProspectiveIntention,
    RecallResult,
)
from aih.memory.procedural import ProceduralMemory
from aih.memory.prospective import ProspectiveMemory
from aih.memory.semantic import SemanticMemory
from aih.memory.store import MemoryStore
from aih.memory.working import ContextAssembler
from aih.observability.ledger import RunLedger
from aih.rag.retriever import HybridRetriever
from aih.skills.registry import SKILLS, SkillRegistry


class MemoryManager:
    """Single entry point for remember / recall / assemble / consolidate / reflect."""

    def __init__(
        self,
        *,
        store: MemoryStore,
        ledger: RunLedger,
        embedder: Embedder,
        retriever: HybridRetriever,
        skills: SkillRegistry | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self._store = store
        self._ledger = ledger
        self._assembler = ContextAssembler()
        self.semantic = SemanticMemory(store, embedder)
        self.episodic = EpisodicMemory(store, ledger, embedder)
        self.procedural = ProceduralMemory(store, skills or SKILLS, embedder)
        self.external = ExternalMemory(retriever)
        self.prospective = ProspectiveMemory(store)
        self._llm = llm

    def remember(self, item: MemoryItem) -> str:
        if item.type == "semantic":
            return self.semantic.upsert(item)
        if item.type == "prospective":
            intention = ProspectiveIntention(
                id=item.id,
                tenant_id=item.tenant_id,
                subject_id=item.subject_id,
                goal=str(item.value),
                trigger_type="time",
                trigger_at=float(item.key) if item.key else None,
            )
            return self.prospective.schedule(intention)
        if item.type == "procedural":
            return self.procedural.add_heuristic(
                item.tenant_id, item.key or "heuristic", str(item.value)
            )
        raise ValueError(f"remember() does not persist type={item.type}")

    def recall(
        self,
        query: str,
        types: list[MemoryType],
        *,
        tenant_id: str = "default",
        k: int = 5,
    ) -> list[RecallResult]:
        results: list[RecallResult] = []
        if "semantic" in types:
            results.extend(self.semantic.recall_similar(tenant_id, query, k=k))
        if "episodic" in types:
            results.extend(self.episodic.recall_similar(query, tenant_id=tenant_id, k=k))
        if "procedural" in types:
            results.extend(self.procedural.recall_applicable(query, tenant_id, k=k))
        if "prospective" in types:
            results.extend(self.prospective.due(tenant_id))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]

    async def assemble_working_memory(
        self,
        goal: str,
        budget: int,
        *,
        tenant_id: str = "default",
        include_external: bool = True,
    ) -> AssembledContext:
        candidates = self.recall(
            goal,
            ["semantic", "episodic", "procedural", "prospective"],
            tenant_id=tenant_id,
            k=12,
        )
        if include_external:
            candidates.extend(await self.external.recall(goal, k=3))
        return self._assembler.build(goal, budget, candidates)

    def reflect(
        self,
        trace: RunTrace,
        *,
        tenant_id: str = "default",
        subject_id: str | None = None,
    ) -> None:
        self.episodic.record(trace, tenant_id=tenant_id, subject_id=subject_id)
        if trace.status == "completed":
            skills = [s.skill for s in trace.steps if s.kind == "skill"]
            if skills:
                self.semantic.upsert(
                    MemoryItem(
                        type="semantic",
                        tenant_id=tenant_id,
                        subject_id=subject_id,
                        namespace="runs",
                        key=trace.goal[:80],
                        value={"skills": skills, "run_id": trace.run_id},
                        confidence=0.7,
                        source="reflect",
                    )
                )

    def consolidate(self, *, tenant_id: str = "default") -> ConsolidationReport:
        episodes = [
            e
            for e in self._store.list_episodes(tenant_id)
            if e["outcome"] == "completed"
        ]
        report = ConsolidationReport()
        report.evicted = self._store.evict_stale(tenant_id)

        # Group by dominant skill pattern in lesson text.
        buckets: dict[str, list[dict[str, Any]]] = {}
        for ep in episodes:
            key = "general"
            lesson = ep.get("lesson") or ""
            goal = ep["goal"].lower()
            if "novareach" in goal:
                key = "novareach"
            elif "sync_campaign_data" in lesson:
                key = "sync"
            elif "publish_creative" in lesson:
                key = "publish"
            buckets.setdefault(key, []).append(ep)

        for name, group in buckets.items():
            if len(group) < 2:
                continue
            heuristic = _distill_heuristic(name, group)
            self.procedural.add_heuristic(tenant_id, name, heuristic)
            report.heuristics_created += 1
            report.episodes_processed += len(group)
        return report

    def delete_subject(self, subject_id: str) -> int:
        return self._store.delete_subject(subject_id)


def _distill_heuristic(name: str, episodes: list[dict[str, Any]]) -> str:
    """Deterministic consolidation (FakeLLM-style) from successful episodes."""
    templates = {
        "novareach": "NovaReach: offset pagination; on 429 back off 2s before retry.",
        "sync": "Sync: prefer sync_campaign_data; cache second reads within TTL.",
        "publish": "Publish: delegate creative review before HITL gate.",
        "general": "Reuse prior successful tool sequence when goal repeats.",
    }
    base = templates.get(name, templates["general"])
    return f"{base} (distilled from {len(episodes)} episodes)"


def build_memory_manager(
    *,
    ledger: RunLedger,
    embedder: Embedder,
    retriever: HybridRetriever | None = None,
    db_path: str | None = None,
) -> MemoryManager:
    settings = get_settings()
    path = db_path or settings.memory_db_path
    store = MemoryStore(path)
    ret = retriever or HybridRetriever(embedder=embedder)
    return MemoryManager(store=store, ledger=ledger, embedder=embedder, retriever=ret)
