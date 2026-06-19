"""Agent run trace models (Pydantic v2)."""

from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from aih.agent.approval import ApprovalDecision, ApprovalRequest

StepKind = Literal["plan", "skill", "approval", "observation", "finish", "error"]
RunStatus = Literal["running", "completed", "denied", "max_steps", "error"]


class RunStep(BaseModel):
    """A single step in an agent run."""

    index: int
    kind: StepKind
    message: str = ""
    skill: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    approval: ApprovalRequest | None = None
    decision: ApprovalDecision | None = None
    ts: float = Field(default_factory=time.time)


class RunTrace(BaseModel):
    """The full, inspectable trace of an agent run."""

    run_id: str
    goal: str
    status: RunStatus = "running"
    steps: list[RunStep] = Field(default_factory=list)
    value_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def add(self, step: RunStep) -> RunStep:
        self.steps.append(step)
        self.updated_at = time.time()
        return step

    def pending_approval(self) -> RunStep | None:
        """Return the most recent approval step still awaiting a decision."""
        for step in reversed(self.steps):
            if step.kind == "approval" and step.decision is None:
                return step
        return None


class RunResult(BaseModel):
    """The result of running the agent: final output + full trace."""

    trace: RunTrace
    output: dict[str, Any] | None = None
