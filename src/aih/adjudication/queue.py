"""The human review queue.

Where escalations land. Deterministic and infra-free: an in-memory list, optionally mirrored
to JSONL. This is the safety net — anything the pipeline will not auto-decide ends up here for a
person to resolve.
"""

from __future__ import annotations

import time
from pathlib import Path

from pydantic import BaseModel, Field

from aih.adjudication.models import Disposition, EvidenceSpan, Finding, JudgeProposal


class QueueItem(BaseModel):
    """One item awaiting human review."""

    finding: Finding
    proposal: JudgeProposal | None
    disposition: Disposition
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    enqueued_at: float = Field(default_factory=time.time)


class HumanQueue:
    """In-memory queue of escalated findings, optionally persisted to JSONL."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path else None
        self._items: list[QueueItem] = []

    def __len__(self) -> int:
        return len(self._items)

    @property
    def items(self) -> list[QueueItem]:
        return list(self._items)

    def enqueue(
        self,
        finding: Finding,
        proposal: JudgeProposal | None,
        disposition: Disposition,
        evidence: list[EvidenceSpan],
    ) -> QueueItem:
        item = QueueItem(
            finding=finding,
            proposal=proposal,
            disposition=disposition,
            evidence=evidence,
        )
        self._items.append(item)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(item.model_dump_json() + "\n")
        return item
