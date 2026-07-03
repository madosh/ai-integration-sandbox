"""Run ledger: persist agent run traces for inspection.

Phase 4 ships an in-memory implementation behind a protocol; Phase 6 adds a
SQLite-backed implementation with the same interface.
"""

from __future__ import annotations

from collections.abc import Callable
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

    def list_runs(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> list[RunTrace]:
        """Return run traces (most recent first).

        ``status`` filters by run status; ``limit`` caps the page size;
        ``cursor`` is the ``run_id`` of the last item of the previous page.
        Raises ``KeyError`` for an unknown cursor.
        """
        ...

    def count_runs(self, *, status: str | None = None) -> int:
        """Return the number of stored runs (optionally filtered by status)."""
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

    def list_runs(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> list[RunTrace]:
        runs = [self._runs[rid] for rid in reversed(self._order)]
        if status is not None:
            runs = [t for t in runs if t.status == status]
        if cursor is not None:
            ids = [t.run_id for t in runs]
            try:
                runs = runs[ids.index(cursor) + 1 :]
            except ValueError:
                raise KeyError(f"unknown cursor: {cursor}") from None
        if limit is not None:
            runs = runs[:limit]
        return runs

    def count_runs(self, *, status: str | None = None) -> int:
        if status is None:
            return len(self._runs)
        return sum(1 for t in self._runs.values() if t.status == status)


class NotifyingLedger:
    """Per-run decorator that forwards every ``save`` to a notify callback.

    Used by the service so SSE subscribers see live updates without
    monkeypatching the shared ledger (which races under concurrent runs).
    """

    def __init__(self, inner: RunLedger, on_save: Callable[[RunTrace], None]) -> None:
        self._inner = inner
        self._on_save = on_save

    def save(self, trace: RunTrace) -> None:
        self._inner.save(trace)
        self._on_save(trace)

    def get(self, run_id: str) -> RunTrace | None:
        return self._inner.get(run_id)

    def list_runs(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> list[RunTrace]:
        return self._inner.list_runs(status=status, limit=limit, cursor=cursor)

    def count_runs(self, *, status: str | None = None) -> int:
        return self._inner.count_runs(status=status)
