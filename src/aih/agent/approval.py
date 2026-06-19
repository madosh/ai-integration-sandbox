"""Human-in-the-loop approval primitives.

The data models live here so both the MCP layer (which emits ``requires_approval``
envelopes for side-effecting tools) and the agent layer (which enforces the gate)
share one shape. The enforcing gate + approvers are added in Phase 4.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Reversibility = Literal["low", "medium", "high"]


class ApprovalRequest(BaseModel):
    """A structured request for human sign-off before a side effect runs."""

    action: str  # what (e.g. "push_creative")
    connector: str | None = None
    summary: str  # why / human-readable description
    payload_preview: dict[str, Any] = Field(default_factory=dict)
    reversibility: Reversibility = "low"


class ApprovalDecision(BaseModel):
    """The resolution of an approval request."""

    approved: bool
    decided_by: str = "unknown"
    reason: str | None = None
