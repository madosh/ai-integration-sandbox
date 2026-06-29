"""Semantic memory — structured facts with conflict resolution."""

from __future__ import annotations

import json
from typing import Any

from aih.llm.base import Embedder
from aih.memory.models import MemoryItem, RecallResult
from aih.memory.store import MemoryStore


class SemanticMemory:
    def __init__(self, store: MemoryStore, embedder: Embedder) -> None:
        self._store = store
        self._embedder = embedder

    def upsert(self, item: MemoryItem) -> str:
        emb = self._embedder.embed([f"{item.namespace}:{item.key} {item.value}"])[0]
        contradiction = False
        existing = self._store.list_semantic(item.tenant_id)
        for row in existing:
            if (
                row["namespace"] == item.namespace
                and row["key"] == item.key
                and json.loads(row["value"]) != item.value
            ):
                contradiction = True
        return self._store.upsert_semantic(item, emb, contradiction=contradiction)

    def recall_by_key(self, tenant_id: str, namespace: str, key: str) -> RecallResult | None:
        for row in self._store.list_semantic(tenant_id):
            if row["namespace"] == namespace and row["key"] == key:
                val = json.loads(row["value"])
                flag = " [CONTRADICTION]" if row["contradiction"] else ""
                return RecallResult(
                    type="semantic",
                    id=row["id"],
                    text=f"{namespace}/{key}={val}{flag}",
                    score=float(row["confidence"]),
                    source=f"semantic:{row['id']}",
                    metadata={"contradiction": bool(row["contradiction"])},
                )
        return None

    def recall_similar(self, tenant_id: str, query: str, k: int = 5) -> list[RecallResult]:
        rows = self._store.list_semantic(tenant_id)
        if not rows:
            return []
        qv = self._embedder.embed([query])[0]
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            if row.get("embedding"):
                from aih.memory.store import _unpack_vec

                ev = _unpack_vec(row["embedding"])
                score = sum(a * b for a, b in zip(qv, ev, strict=False))
            else:
                score = 0.1
            scored.append((score, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[RecallResult] = []
        for score, row in scored[:k]:
            val = json.loads(row["value"])
            flag = " [CONTRADICTION]" if row["contradiction"] else ""
            out.append(
                RecallResult(
                    type="semantic",
                    id=row["id"],
                    text=f"{row['namespace']}/{row['key']}={val}{flag}",
                    score=score,
                    source=f"semantic:{row['id']}",
                )
            )
        return out
