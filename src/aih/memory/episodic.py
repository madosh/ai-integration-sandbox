"""Episodic memory — extends the run ledger with searchable episodes."""

from __future__ import annotations

from aih.agent.models import RunTrace
from aih.llm.base import Embedder
from aih.memory.models import RecallResult
from aih.memory.store import MemoryStore
from aih.observability.ledger import RunLedger


class EpisodicMemory:
    def __init__(self, store: MemoryStore, ledger: RunLedger, embedder: Embedder) -> None:
        self._store = store
        self._ledger = ledger
        self._embedder = embedder

    def record(self, trace: RunTrace, *, tenant_id: str = "default", subject_id: str | None = None) -> None:
        outcome = trace.status
        skills = [s.skill for s in trace.steps if s.kind == "skill"]
        errors = [s.message for s in trace.steps if s.kind == "error"]
        lesson = None
        if outcome in {"denied", "failed", "max_steps"} or errors:
            lesson = f"Prior attempt {outcome}: avoid repeating {skills or errors[:1]}"
        elif outcome == "completed":
            lesson = f"Succeeded via {skills}"
        emb = self._embedder.embed([trace.goal])[0]
        salience = 1.5 if outcome in {"denied", "failed"} else 1.0
        self._store.index_episode(
            run_id=trace.run_id,
            tenant_id=tenant_id,
            subject_id=subject_id,
            goal=trace.goal,
            outcome=outcome,
            lesson=lesson,
            embedding=emb,
            salience=salience,
        )

    def recall_similar(self, goal: str, *, tenant_id: str = "default", k: int = 3) -> list[RecallResult]:
        episodes = self._store.list_episodes(tenant_id)
        if not episodes:
            return []
        qv = self._embedder.embed([goal])[0]
        scored: list[tuple[float, dict]] = []
        for ep in episodes:
            emb = ep.get("embedding")
            if not emb:
                continue
            score = sum(a * b for a, b in zip(qv, emb)) * float(ep.get("salience", 1.0))
            scored.append((score, ep))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[RecallResult] = []
        for score, ep in scored[:k]:
            warn = " ⚠ FAILED BEFORE" if ep["outcome"] in {"denied", "failed", "max_steps"} else ""
            text = f"Episode {ep['run_id']}: goal={ep['goal']} outcome={ep['outcome']}{warn}"
            if ep.get("lesson"):
                text += f" — {ep['lesson']}"
            out.append(
                RecallResult(
                    type="episodic",
                    id=ep["run_id"],
                    text=text,
                    score=score,
                    source=f"episodic:{ep['run_id']}",
                    metadata={"outcome": ep["outcome"]},
                )
            )
        return out
