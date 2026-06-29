"""FastAPI dependencies and application state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx

from aih.a2a.server import A2AServer, A2AState
from aih.agent.approval import APIApprover
from aih.agent.models import RunTrace
from aih.agent.orchestrator import Agent
from aih.agui.bridge import AguiBridge
from aih.config import get_settings
from aih.llm import get_embedder, get_llm
from aih.memory.manager import MemoryManager, build_memory_manager
from aih.observability.ledger import InMemoryLedger, RunLedger
from aih.observability.sqlite_ledger import SQLiteLedger
from aih.rag.retriever import HybridRetriever
from aih.skills.base import SkillContext
from aih.skills.registry import SKILLS, SkillRegistry


@dataclass
class AppState:
    """Shared application state wired into FastAPI routes."""

    ledger: RunLedger
    approver: APIApprover
    skills: SkillRegistry = SKILLS
    httpx_transport: httpx.AsyncBaseTransport | None = None
    memory: MemoryManager | None = None
    a2a_state: A2AState = field(default_factory=A2AState)
    a2a_server: A2AServer | None = None
    agui_bridge: AguiBridge = field(default_factory=AguiBridge)
    _agui_subscribers: dict[str, list[asyncio.Queue[dict[str, object]]]] = field(
        default_factory=dict
    )
    _subscribers: dict[str, list[asyncio.Queue[RunTrace]]] = field(default_factory=dict)

    def subscribe(self, run_id: str) -> asyncio.Queue[RunTrace]:
        q: asyncio.Queue[RunTrace] = asyncio.Queue()
        self._subscribers.setdefault(run_id, []).append(q)
        return q

    def notify(self, trace: RunTrace) -> None:
        for q in self._subscribers.get(trace.run_id, []):
            q.put_nowait(trace)
        for event in self.agui_bridge.diff(trace):
            for aq in self._agui_subscribers.get(trace.run_id, []):
                aq.put_nowait(event.model_dump())

    def subscribe_agui(self, run_id: str) -> asyncio.Queue[dict[str, object]]:
        q: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self._agui_subscribers.setdefault(run_id, []).append(q)
        return q

    def build_agent(self) -> Agent:
        ctx = SkillContext(
            llm=get_llm(),
            embedder=get_embedder(),
            retriever=HybridRetriever(embedder=get_embedder()),
            httpx_transport=self.httpx_transport,
        )
        agent = Agent(
            approver=self.approver,
            ledger=self.ledger,
            ctx=ctx,
            skills=self.skills,
            memory=self.memory,
        )
        return agent

    def build_retriever(self) -> HybridRetriever:
        return HybridRetriever(embedder=get_embedder())

    def skill_context(self) -> SkillContext:
        return SkillContext(
            llm=get_llm(),
            embedder=get_embedder(),
            retriever=HybridRetriever(embedder=get_embedder()),
            httpx_transport=self.httpx_transport,
        )

    def metrics(self) -> dict[str, Any]:
        if isinstance(self.ledger, SQLiteLedger):
            return self.ledger.aggregate_metrics()
        runs = self.ledger.list_runs()
        if not runs:
            return {
                "total_runs": 0,
                "success_rate": 0.0,
                "records_synced": 0,
                "creatives_pushed": 0,
                "estimated_value_usd": 0.0,
                "avg_duration_sec": 0.0,
            }
        completed = [r for r in runs if r.status == "completed"]
        durations = [max(0.0, r.updated_at - r.created_at) for r in runs]
        records = sum(int(r.value_summary.get("records_synced", 0)) for r in runs)
        creatives = sum(int(r.value_summary.get("creatives_pushed", 0)) for r in runs)
        value = sum(float(r.value_summary.get("estimated_value_usd", 0)) for r in runs)
        return {
            "total_runs": len(runs),
            "success_rate": len(completed) / len(runs),
            "records_synced": records,
            "creatives_pushed": creatives,
            "estimated_value_usd": value,
            "avg_duration_sec": sum(durations) / len(durations),
        }


def build_state(
    *,
    ledger: RunLedger | None = None,
    approver: APIApprover | None = None,
    httpx_transport: httpx.AsyncBaseTransport | None = None,
    memory: MemoryManager | None = None,
) -> AppState:
    settings = get_settings()
    if ledger is None:
        ledger = (
            InMemoryLedger() if settings.env == "ci" else SQLiteLedger(settings.run_ledger_path)
        )
    if memory is None and settings.agent_enable_memory:
        memory = build_memory_manager(ledger=ledger, embedder=get_embedder())

    return AppState(
        ledger=ledger,
        approver=approver or APIApprover(),
        httpx_transport=httpx_transport,
        memory=memory,
    )
