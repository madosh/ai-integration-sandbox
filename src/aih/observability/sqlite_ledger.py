"""SQLite-backed run ledger (persistent across process restarts)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from aih.agent.models import RunTrace


class SQLiteLedger:
    """Persist agent run traces in SQLite."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    trace_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """)
            conn.commit()

    def save(self, trace: RunTrace) -> None:
        payload = trace.model_dump_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, goal, status, trace_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status=excluded.status,
                    trace_json=excluded.trace_json,
                    updated_at=excluded.updated_at
                """,
                (
                    trace.run_id,
                    trace.goal,
                    trace.status,
                    payload,
                    trace.created_at,
                    trace.updated_at,
                ),
            )
            conn.commit()

    def get(self, run_id: str) -> RunTrace | None:
        with self._connect() as conn:
            row = conn.execute("SELECT trace_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return RunTrace.model_validate_json(row["trace_json"])

    def list_runs(self) -> list[RunTrace]:
        with self._connect() as conn:
            rows = conn.execute("SELECT trace_json FROM runs ORDER BY updated_at DESC").fetchall()
        return [RunTrace.model_validate_json(r["trace_json"]) for r in rows]

    def aggregate_metrics(self) -> dict[str, Any]:
        """Compute dashboard metrics from stored runs."""
        runs = self.list_runs()
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
