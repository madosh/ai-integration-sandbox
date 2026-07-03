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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_updated ON runs(updated_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)")
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

    def list_runs(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> list[RunTrace]:
        """Page through runs newest-first without deserializing the whole table."""
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        with self._connect() as conn:
            if cursor is not None:
                anchor = conn.execute(
                    "SELECT updated_at, run_id FROM runs WHERE run_id = ?", (cursor,)
                ).fetchone()
                if anchor is None:
                    raise KeyError(f"unknown cursor: {cursor}")
                clauses.append("(updated_at, run_id) < (?, ?)")
                params.extend([anchor["updated_at"], anchor["run_id"]])
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            sql = f"SELECT trace_json FROM runs {where} ORDER BY updated_at DESC, run_id DESC"
            if limit is not None:
                sql += " LIMIT ?"
                params.append(limit)
            rows = conn.execute(sql, params).fetchall()
        return [RunTrace.model_validate_json(r["trace_json"]) for r in rows]

    def count_runs(self, *, status: str | None = None) -> int:
        with self._connect() as conn:
            if status is None:
                row = conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM runs WHERE status = ?", (status,)
                ).fetchone()
        return int(row["n"])

    def aggregate_metrics(self) -> dict[str, Any]:
        """Compute dashboard metrics in SQL (falls back to Python without JSON1)."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT
                        COUNT(*) AS total,
                        SUM(status = 'completed') AS completed,
                        SUM(MAX(0.0, updated_at - created_at)) AS total_duration,
                        SUM(COALESCE(json_extract(trace_json,
                            '$.value_summary.records_synced'), 0)) AS records,
                        SUM(COALESCE(json_extract(trace_json,
                            '$.value_summary.creatives_pushed'), 0)) AS creatives,
                        SUM(COALESCE(json_extract(trace_json,
                            '$.value_summary.estimated_value_usd'), 0)) AS value
                    FROM runs
                    """
                ).fetchone()
        except sqlite3.OperationalError:
            return self._aggregate_metrics_python()
        total = int(row["total"] or 0)
        if total == 0:
            return _empty_metrics()
        return {
            "total_runs": total,
            "success_rate": int(row["completed"] or 0) / total,
            "records_synced": int(row["records"] or 0),
            "creatives_pushed": int(row["creatives"] or 0),
            "estimated_value_usd": float(row["value"] or 0.0),
            "avg_duration_sec": float(row["total_duration"] or 0.0) / total,
        }

    def _aggregate_metrics_python(self) -> dict[str, Any]:
        runs = self.list_runs()
        if not runs:
            return _empty_metrics()
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


def _empty_metrics() -> dict[str, Any]:
    return {
        "total_runs": 0,
        "success_rate": 0.0,
        "records_synced": 0,
        "creatives_pushed": 0,
        "estimated_value_usd": 0.0,
        "avg_duration_sec": 0.0,
    }
