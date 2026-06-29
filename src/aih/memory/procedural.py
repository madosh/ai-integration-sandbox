"""Procedural memory — declared skills + learned heuristics."""

from __future__ import annotations

from aih.llm.base import Embedder
from aih.memory.models import RecallResult
from aih.memory.store import MemoryStore
from aih.skills.registry import SkillRegistry


class ProceduralMemory:
    def __init__(self, store: MemoryStore, skills: SkillRegistry, embedder: Embedder) -> None:
        self._store = store
        self._skills = skills
        self._embedder = embedder

    def declared(self) -> list[RecallResult]:
        out: list[RecallResult] = []
        for desc in self._skills.describe():
            out.append(
                RecallResult(
                    type="procedural",
                    id=f"skill:{desc['name']}",
                    text=f"DECLARED {desc['name']}: {desc.get('description', '')}",
                    score=1.0,
                    source="skills_registry",
                    metadata={"declared": True},
                )
            )
        return out

    def learned(self, tenant_id: str) -> list[RecallResult]:
        out: list[RecallResult] = []
        for row in self._store.list_procedural(tenant_id):
            out.append(
                RecallResult(
                    type="procedural",
                    id=row["id"],
                    text=f"LEARNED {row['name']} v{row['version']}: {row['content']}",
                    score=float(row["confidence"]),
                    source=f"procedural:{row['id']}",
                    metadata={"version": row["version"]},
                )
            )
        return out

    def recall_applicable(self, query: str, tenant_id: str, k: int = 4) -> list[RecallResult]:
        candidates = self.declared() + self.learned(tenant_id)
        if not candidates:
            return []
        qv = self._embedder.embed([query])[0]
        texts = [c.text for c in candidates]
        evs = self._embedder.embed(texts)
        scored = [
            (sum(a * b for a, b in zip(qv, ev, strict=False)), c)
            for ev, c in zip(evs, candidates, strict=False)
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:k]]

    def add_heuristic(self, tenant_id: str, name: str, content: str) -> str:
        emb = self._embedder.embed([content])[0]
        return self._store.add_procedural(tenant_id, name, content, embedding=emb)
