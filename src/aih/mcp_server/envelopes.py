"""Structured result + error envelopes for MCP tools.

Tools NEVER raise raw exceptions across the protocol boundary; they return a typed
envelope with ``ok`` plus either data or a structured ``error``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from aih.agent.approval import ApprovalRequest


class ToolError(BaseModel):
    """A structured, typed error returned in place of an exception."""

    type: str
    message: str


class ConnectorInfo(BaseModel):
    name: str
    capabilities: list[str] = Field(default_factory=list)


class ConnectorsResult(BaseModel):
    ok: bool = True
    connectors: list[ConnectorInfo] = Field(default_factory=list)
    error: ToolError | None = None


class RecordsResult(BaseModel):
    ok: bool = True
    connector: str
    resource: str
    count: int = 0
    records: list[dict[str, Any]] = Field(default_factory=list)
    error: ToolError | None = None


class ApprovalEnvelope(BaseModel):
    """Returned by side-effecting tools: the side effect is NOT executed."""

    ok: bool = True
    status: Literal["requires_approval"] = "requires_approval"
    approval: ApprovalRequest
    error: ToolError | None = None


class RunStatusResult(BaseModel):
    ok: bool = True
    run_id: str
    status: str = "unknown"
    detail: str | None = None
    error: ToolError | None = None


class Citation(BaseModel):
    source: str
    doc_id: str | None = None
    chunk_id: str | None = None
    score: float | None = None
    signals: list[str] = Field(default_factory=list)


class SearchHit(BaseModel):
    text: str
    score: float
    citation: Citation


class DeterministicHit(BaseModel):
    id: str
    partner: str
    data: dict[str, Any] = Field(default_factory=dict)
    source: str


class SearchResultEnvelope(BaseModel):
    ok: bool = True
    query: str
    hits: list[SearchHit] = Field(default_factory=list)
    deterministic: DeterministicHit | None = None
    error: ToolError | None = None
