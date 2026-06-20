"""Run-scoped memory for multi-turn agent context."""

from __future__ import annotations

from collections import defaultdict


class RunMemory:
    """Key-value memory per run id (process-local)."""

    def __init__(self) -> None:
        self._store: dict[str, list[str]] = defaultdict(list)

    def remember(self, run_id: str, note: str) -> None:
        self._store[run_id].append(note)

    def recall(self, run_id: str) -> list[str]:
        return list(self._store.get(run_id, []))

    def clear(self, run_id: str) -> None:
        self._store.pop(run_id, None)


#: Process-wide run memory.
MEMORY = RunMemory()
