"""Plan-and-execute graph (lightweight alternative to single tool-call loop)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aih.agent.models import RunResult
from aih.agent.orchestrator import Agent


class PlanStep(BaseModel):
    skill: str
    args: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class ExecutionPlan(BaseModel):
    goal: str
    steps: list[PlanStep] = Field(default_factory=list)


class GraphAgent:
    """Two-phase agent: build a plan (FakeLLM) then execute via the standard Agent."""

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    async def run_with_plan(self, goal: str) -> tuple[ExecutionPlan, RunResult]:
        """Execute goal; plan is derived from the run trace for inspection."""
        result = await self._agent.run(goal)
        steps = [
            PlanStep(
                skill=s.skill or "unknown",
                args=s.args,
                rationale=s.message,
            )
            for s in result.trace.steps
            if s.kind in {"plan", "skill"}
        ]
        plan = ExecutionPlan(goal=goal, steps=steps)
        return plan, result
