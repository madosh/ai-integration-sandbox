"""Pydantic models for the unified memory subsystem."""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

MemoryType = Literal[
    "working",
    "semantic",
    "episodic",
    "procedural",
    "external",
    "prospective",
]


class MemoryItem(BaseModel):
    """A storable memory fragment."""

    type: MemoryType
    tenant_id: str = "default"
    subject_id: str | None = None
    namespace: str = "default"
    key: str = ""
    value: Any = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    source: str = "agent"
    salience: float = Field(default=1.0, ge=0.0)
    contradiction: bool = False
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])


class RecallResult(BaseModel):
    """A recalled memory with score and provenance."""

    type: MemoryType
    id: str
    text: str
    score: float = 1.0
    source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextFragment(BaseModel):
    """One fragment in assembled working memory."""

    type: MemoryType
    text: str
    provenance: str
    tokens: int


class AssembledContext(BaseModel):
    """Working-memory assembly result."""

    goal: str
    fragments: list[ContextFragment] = Field(default_factory=list)
    total_tokens: int = 0
    budget: int = 0
    evicted: int = 0

    def to_prompt_block(self) -> str:
        if not self.fragments:
            return ""
        lines = ["", "MEMORY CONTEXT (provenance-tagged):"]
        for f in self.fragments:
            lines.append(f"- [{f.type}|{f.provenance}] {f.text}")
        return "\n".join(lines)


class ProspectiveIntention(BaseModel):
    """A future intention scheduled for a later agent tick."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    tenant_id: str = "default"
    subject_id: str | None = None
    goal: str
    trigger_type: Literal["time", "condition"] = "time"
    trigger_at: float | None = None
    trigger_condition: str | None = None
    status: Literal["pending", "surfaced", "done", "cancelled"] = "pending"
    created_at: float = Field(default_factory=time.time)


class ConsolidationReport(BaseModel):
    """Summary of a consolidation pass."""

    episodes_processed: int = 0
    heuristics_created: int = 0
    facts_promoted: int = 0
    evicted: int = 0
