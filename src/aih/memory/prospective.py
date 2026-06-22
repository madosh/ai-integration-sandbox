"""Prospective memory — future intentions and agenda."""

from __future__ import annotations

import time

from aih.memory.models import ProspectiveIntention, RecallResult
from aih.memory.store import MemoryStore


class ProspectiveMemory:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def schedule(self, intention: ProspectiveIntention) -> str:
        return self._store.add_intention(intention)

    def due(self, tenant_id: str, *, now: float | None = None) -> list[RecallResult]:
        intentions = self._store.due_intentions(tenant_id, now=now)
        out: list[RecallResult] = []
        for it in intentions:
            out.append(
                RecallResult(
                    type="prospective",
                    id=it.id,
                    text=f"DUE INTENTION: {it.goal}",
                    score=2.0,
                    source=f"prospective:{it.id}",
                    metadata={"trigger_at": it.trigger_at},
                )
            )
            self._store.mark_intention(it.id, "surfaced")
        return out

    def remember_later(
        self,
        goal: str,
        *,
        tenant_id: str = "default",
        subject_id: str | None = None,
        delay_sec: float = 0.0,
    ) -> str:
        intention = ProspectiveIntention(
            tenant_id=tenant_id,
            subject_id=subject_id,
            goal=goal,
            trigger_type="time",
            trigger_at=time.time() + delay_sec,
        )
        return self.schedule(intention)
