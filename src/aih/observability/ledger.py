"""Run ledger: persist agent run traces for inspection.

Phase 4 ships an in-memory implementation behind a protocol; Phase 6 adds a
SQLite-backed implementation with the same interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from aih.agent.models import RunTrace


@runtime_checkable
class RunLedger(Protocol):
    """Persistence interface for agent run traces."""

    def save(self, trace: RunTrace) -> None:
        """Insert or update a run trace."""
        ...

    def get(self, run_id: str) -> RunTrace | None:
        """Return a run trace by id, or None."""
        ...

    def list_runs(self) -> list[RunTrace]:
        """Return all run traces (most recent first)."""
        ...


class InMemoryLedger:
    """A simple dict-backed ledger (process-local)."""

    def __init__(self) -> None:
        self._runs: dict[str, RunTrace] = {}
        self._order: list[str] = []

    def save(self, trace: RunTrace) -> None:
        if trace.run_id not in self._runs:
            self._order.append(trace.run_id)
        self._runs[trace.run_id] = trace

    def get(self, run_id: str) -> RunTrace | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[RunTrace]:
        return [self._runs[rid] for rid in reversed(self._order)]
