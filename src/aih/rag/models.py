"""RAG data models (Pydantic v2)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A token-aware chunk of a source document, with preserved metadata."""

    id: str
    doc_id: str
    text: str
    start_token: int = 0
    end_token: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Provenance(BaseModel):
    """Where a retrieved result came from and why it ranked."""

    source: str  # "doc:<doc_id>" or "connector:<partner>"
    doc_id: str | None = None
    chunk_id: str | None = None
    bm25: float | None = None
    dense: float | None = None
    fused: float | None = None
    method: Literal["alpha", "rrf", "deterministic"] = "alpha"
    signals: list[str] = Field(default_factory=list)


class RetrievedChunk(BaseModel):
    """A scored, cited chunk returned from retrieval."""

    text: str
    score: float
    provenance: Provenance
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthoritativeRecord(BaseModel):
    """A deterministic, authoritative record from a connector (not text retrieval)."""

    kind: Literal["campaign"] = "campaign"
    id: str
    partner: str
    data: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class SearchResult(BaseModel):
    """The full result of a hybrid search: probabilistic + deterministic."""

    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    deterministic: AuthoritativeRecord | None = None
