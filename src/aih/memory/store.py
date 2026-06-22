"""SQLite persistence for semantic, procedural, prospective, and episode index."""

from __future__ import annotations

import json
import sqlite3
import struct
import time
from pathlib import Path
from typing import Any

from aih.memory.models import MemoryItem, ProspectiveIntention


def _pack_vec(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack_vec(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


class MemoryStore:
    """SQLite store shared by semantic, procedural, prospective, and episode index."""

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
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS semantic_facts (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT,
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT,
                    learned_at REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    salience REAL NOT NULL,
                    contradiction INTEGER NOT NULL DEFAULT 0,
                    expires_at REAL,
                    embedding BLOB
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_semantic_key
                    ON semantic_facts(tenant_id, namespace, key);

                CREATE TABLE IF NOT EXISTS procedural_heuristics (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    source TEXT,
                    learned_at REAL NOT NULL,
                    confidence REAL NOT NULL,
                    embedding BLOB
                );

                CREATE TABLE IF NOT EXISTS prospective_intentions (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT,
                    goal TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_at REAL,
                    trigger_condition TEXT,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS episode_index (
                    run_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT,
                    goal TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    lesson TEXT,
                    salience REAL NOT NULL,
                    embedding BLOB,
                    created_at REAL NOT NULL
                );
                """)
            conn.commit()

    def upsert_semantic(
        self,
        item: MemoryItem,
        embedding: list[float] | None = None,
        *,
        contradiction: bool = False,
    ) -> str:
        now = time.time()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, confidence, value FROM semantic_facts
                WHERE tenant_id=? AND namespace=? AND key=?
                """,
                (item.tenant_id, item.namespace, item.key),
            ).fetchone()
            if row is not None:
                existing_conf = float(row["confidence"])
                if str(item.value) != row["value"]:
                    contradiction = True
                if item.confidence < existing_conf:
                    return str(row["id"])
                item_id = str(row["id"])
            else:
                item_id = item.id
            conn.execute(
                """
                INSERT INTO semantic_facts
                (id, tenant_id, subject_id, namespace, key, value, confidence, source,
                 learned_at, last_seen, salience, contradiction, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    value=excluded.value,
                    confidence=excluded.confidence,
                    last_seen=excluded.last_seen,
                    salience=excluded.salience,
                    contradiction=excluded.contradiction,
                    embedding=excluded.embedding
                """,
                (
                    item_id,
                    item.tenant_id,
                    item.subject_id,
                    item.namespace,
                    item.key,
                    json.dumps(item.value),
                    item.confidence,
                    item.source,
                    now,
                    now,
                    item.salience,
                    1 if contradiction else 0,
                    _pack_vec(embedding) if embedding else None,
                ),
            )
            conn.commit()
        return item_id

    def list_semantic(self, tenant_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM semantic_facts WHERE tenant_id=? ORDER BY last_seen DESC",
                (tenant_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_procedural(
        self,
        tenant_id: str,
        name: str,
        content: str,
        *,
        source: str = "consolidation",
        confidence: float = 0.85,
        embedding: list[float] | None = None,
    ) -> str:
        import uuid

        pid = uuid.uuid4().hex[:12]
        with self._connect() as conn:
            ver = conn.execute(
                "SELECT COALESCE(MAX(version), 0) FROM procedural_heuristics WHERE tenant_id=? AND name=?",
                (tenant_id, name),
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO procedural_heuristics
                (id, tenant_id, name, content, version, source, learned_at, confidence, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pid,
                    tenant_id,
                    name,
                    content,
                    int(ver) + 1,
                    source,
                    time.time(),
                    confidence,
                    _pack_vec(embedding) if embedding else None,
                ),
            )
            conn.commit()
        return pid

    def list_procedural(self, tenant_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM procedural_heuristics WHERE tenant_id=? ORDER BY learned_at DESC",
                (tenant_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_intention(self, intention: ProspectiveIntention) -> str:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO prospective_intentions
                (id, tenant_id, subject_id, goal, trigger_type, trigger_at,
                 trigger_condition, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intention.id,
                    intention.tenant_id,
                    intention.subject_id,
                    intention.goal,
                    intention.trigger_type,
                    intention.trigger_at,
                    intention.trigger_condition,
                    intention.status,
                    intention.created_at,
                ),
            )
            conn.commit()
        return intention.id

    def due_intentions(self, tenant_id: str, *, now: float | None = None) -> list[ProspectiveIntention]:
        ts = now if now is not None else time.time()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM prospective_intentions
                WHERE tenant_id=? AND status='pending'
                  AND trigger_type='time' AND trigger_at <= ?
                ORDER BY trigger_at ASC
                """,
                (tenant_id, ts),
            ).fetchall()
        return [
            ProspectiveIntention(
                id=r["id"],
                tenant_id=r["tenant_id"],
                subject_id=r["subject_id"],
                goal=r["goal"],
                trigger_type=r["trigger_type"],
                trigger_at=r["trigger_at"],
                trigger_condition=r["trigger_condition"],
                status=r["status"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def mark_intention(self, intention_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE prospective_intentions SET status=? WHERE id=?",
                (status, intention_id),
            )
            conn.commit()

    def index_episode(
        self,
        *,
        run_id: str,
        tenant_id: str,
        subject_id: str | None,
        goal: str,
        outcome: str,
        lesson: str | None,
        embedding: list[float] | None,
        salience: float = 1.0,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO episode_index
                (run_id, tenant_id, subject_id, goal, outcome, lesson, salience, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    outcome=excluded.outcome,
                    lesson=excluded.lesson,
                    salience=excluded.salience,
                    embedding=excluded.embedding
                """,
                (
                    run_id,
                    tenant_id,
                    subject_id,
                    goal,
                    outcome,
                    lesson,
                    salience,
                    _pack_vec(embedding) if embedding else None,
                    time.time(),
                ),
            )
            conn.commit()

    def list_episodes(self, tenant_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM episode_index WHERE tenant_id=? ORDER BY created_at DESC",
                (tenant_id,),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            if d.get("embedding"):
                d["embedding"] = _unpack_vec(d["embedding"])
            out.append(d)
        return out

    def delete_subject(self, subject_id: str) -> int:
        with self._connect() as conn:
            n = 0
            for table in ("semantic_facts", "prospective_intentions", "episode_index"):
                cur = conn.execute(f"DELETE FROM {table} WHERE subject_id=?", (subject_id,))
                n += cur.rowcount
            conn.commit()
        return n

    def evict_stale(self, tenant_id: str, *, max_age_sec: float = 86400 * 30) -> int:
        cutoff = time.time() - max_age_sec
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM semantic_facts WHERE tenant_id=? AND last_seen < ? AND salience < 0.3",
                (tenant_id, cutoff),
            )
            n = cur.rowcount
            conn.commit()
        return n
