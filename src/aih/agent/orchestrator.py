"""The agent: plan -> select -> (gate) -> execute -> observe -> iterate.

Deterministic under FakeLLM. The planner builds real tool specs from skill input
schemas and selects a tool via function-calling. Side-effecting skills are gated
by the injected approver. The full run trace is recorded to the ledger.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from pydantic import ValidationError

from aih.agent.approval import ApprovalRequest, Approver, AutoApprover
from aih.agent.budget import TokenBudget
from aih.agent.memory import MEMORY
from aih.agent.models import RunResult, RunStep, RunTrace
from aih.config import get_settings
from aih.connectors.errors import ConnectorError
from aih.guardrails.validate import validate_skill_args
from aih.llm import get_llm
from aih.llm.base import ChatMessage, LLMClient, ToolSpec
from aih.memory.manager import MemoryManager
from aih.observability.ledger import InMemoryLedger, RunLedger
from aih.observability.logging import get_logger
from aih.observability.tracing import Tracer, export_run
from aih.skills.base import SkillContext
from aih.skills.registry import SKILLS, SkillRegistry

_log = get_logger("aih.agent")

_FINISH_TOOL = ToolSpec(
    name="finish",
    description="Finish the task when the goal is satisfied or no further action helps.",
    parameters={"type": "object", "properties": {}},
)

_SYSTEM_PROMPT = (
    "You are an integration automation agent. Given a goal, select exactly one tool to make "
    "progress, or 'finish' when done. Side-effecting tools require human approval before they run. "
    "Prefer read-only tools unless the goal explicitly asks for a side effect."
)


class Agent:
    """Goal-driven orchestrator with a human-in-the-loop gate."""

    def __init__(
        self,
        *,
        llm: LLMClient | None = None,
        skills: SkillRegistry | None = None,
        approver: Approver | None = None,
        ledger: RunLedger | None = None,
        ctx: SkillContext | None = None,
        max_steps: int | None = None,
        memory: MemoryManager | None = None,
        tenant_id: str = "default",
        subject_id: str | None = None,
    ) -> None:
        self.llm = llm or get_llm()
        self.skills = skills or SKILLS
        self.approver: Approver = approver or AutoApprover(True)
        self.ledger: RunLedger = ledger or InMemoryLedger()
        self.ctx = ctx or SkillContext.default()
        self.max_steps = max_steps or get_settings().agent_max_steps
        self.memory = memory
        self.tenant_id = tenant_id
        self.subject_id = subject_id

    async def run(self, goal: str, *, run_id: str | None = None) -> RunResult:
        trace = RunTrace(run_id=run_id or uuid.uuid4().hex[:12], goal=goal)
        tracer = Tracer(trace.run_id)
        budget = TokenBudget()
        settings = get_settings()
        self.ledger.save(trace)
        system_prompt = _SYSTEM_PROMPT
        if self.memory and settings.agent_enable_memory:
            assembled = await self.memory.assemble_working_memory(
                goal, budget.limit, tenant_id=self.tenant_id
            )
            system_prompt += assembled.to_prompt_block()
        if settings.agent_enable_memory:
            MEMORY.remember(trace.run_id, f"goal:{goal}")
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=f"GOAL: {goal}"),
        ]
        tools = [*self.skills.tool_specs(), _FINISH_TOOL]
        last_sig: str | None = None
        last_output: dict[str, Any] | None = None
        index = 0

        for _ in range(self.max_steps):
            if budget.exhausted:
                trace.add(RunStep(index=index, kind="finish", message="token budget exhausted"))
                trace.status = "max_steps"
                break
            with tracer.span("llm.tool_call", step=index):
                completion = await self.llm.tool_call(messages, tools)
                budget.charge(50)
                tracer.add_token_estimate(50, 0.0001)
            call = completion.tool_call
            if call is None or call.name == "finish":
                trace.add(RunStep(index=index, kind="finish", message="planner finished"))
                if trace.status == "running":
                    trace.status = "completed"
                break

            sig = f"{call.name}:{json.dumps(call.arguments, sort_keys=True)}"
            trace.add(
                RunStep(
                    index=index,
                    kind="plan",
                    skill=call.name,
                    args=call.arguments,
                    message=f"selected {call.name}",
                )
            )
            index += 1

            if sig == last_sig:
                trace.add(RunStep(index=index, kind="finish", message="converged (no new action)"))
                if trace.status == "running":
                    trace.status = "completed"
                break
            last_sig = sig

            if not self.skills.has(call.name):
                trace.add(
                    RunStep(
                        index=index,
                        kind="error",
                        skill=call.name,
                        message=f"unknown skill: {call.name}",
                    )
                )
                index += 1
                self.ledger.save(trace)
                continue

            skill = self.skills.get(call.name)
            ok, err = validate_skill_args(skill.name, call.arguments)
            if not ok:
                trace.add(
                    RunStep(
                        index=index,
                        kind="error",
                        skill=call.name,
                        message=f"guardrail: {err}",
                    )
                )
                index += 1
                self.ledger.save(trace)
                continue
            try:
                payload = skill.input_model(**call.arguments)
            except ValidationError as exc:
                trace.add(
                    RunStep(
                        index=index,
                        kind="error",
                        skill=call.name,
                        message=f"invalid args: {exc.error_count()} error(s)",
                    )
                )
                index += 1
                self.ledger.save(trace)
                continue

            if skill.side_effect:
                proceed = await self._gate(trace, skill.name, call.arguments)
                index = len(trace.steps)
                self.ledger.save(trace)
                if not proceed:
                    messages.append(
                        ChatMessage(role="assistant", content=f"{skill.name} denied; skipped.")
                    )
                    continue

            try:
                with tracer.span("skill.run", skill=skill.name):
                    result = await skill.run(payload, self.ctx)
                budget.charge(20)
            except (ConnectorError, NotImplementedError) as exc:
                trace.add(
                    RunStep(
                        index=index,
                        kind="error",
                        skill=skill.name,
                        message=f"{type(exc).__name__}: {exc}",
                    )
                )
                index += 1
                self.ledger.save(trace)
                messages.append(
                    ChatMessage(role="assistant", content=f"{skill.name} failed: {exc}")
                )
                continue

            last_output = result.model_dump()
            if settings.agent_enable_memory:
                MEMORY.remember(trace.run_id, f"skill:{skill.name}")
            trace.add(
                RunStep(
                    index=index,
                    kind="skill",
                    skill=skill.name,
                    args=call.arguments,
                    result=last_output,
                    message=f"executed {skill.name}",
                )
            )
            index += 1
            self.ledger.save(trace)
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=f"Observed result of {skill.name}: {json.dumps(last_output)[:500]}",
                )
            )
        else:
            if trace.status == "running":
                trace.status = "max_steps"

        trace.value_summary = _summarize_value(trace)
        trace.tracing = tracer.to_dict()
        trace.value_summary["tokens_used"] = budget.used
        trace.value_summary["token_budget"] = budget.limit
        self.ledger.save(trace)
        export_run(tracer)
        if self.memory and settings.agent_enable_memory:
            self.memory.reflect(trace, tenant_id=self.tenant_id, subject_id=self.subject_id)
        _log.info(
            "run.complete",
            extra={"context": {"run_id": trace.run_id, "status": trace.status}},
        )
        return RunResult(trace=trace, output=last_output)

    async def _gate(self, trace: RunTrace, action: str, args: dict[str, Any]) -> bool:
        request = ApprovalRequest(
            action=action,
            connector=args.get("connector"),
            summary=f"Agent requests to run side-effecting skill '{action}'.",
            payload_preview=args,
            reversibility="low",
            run_id=trace.run_id,
        )
        step = trace.add(
            RunStep(
                index=len(trace.steps),
                kind="approval",
                skill=action,
                approval=request,
                message="awaiting approval",
            )
        )
        self.ledger.save(trace)
        decision = await self.approver.decide(request)
        step.decision = decision
        step.message = "approved" if decision.approved else "denied"
        if not decision.approved:
            trace.status = "denied"
        return decision.approved


def _summarize_value(trace: RunTrace) -> dict[str, Any]:
    """Estimate the value generated by the run (used by /metrics later)."""
    skills_run = [s for s in trace.steps if s.kind == "skill"]
    records_synced = sum(
        int((s.result or {}).get("count", 0)) for s in skills_run if s.skill == "sync_campaign_data"
    )
    creatives_pushed = sum(
        1
        for s in skills_run
        if s.skill == "publish_creative" and (s.result or {}).get("status") != "duplicate"
    )
    approvals = [s for s in trace.steps if s.kind == "approval"]
    return {
        "skills_run": len(skills_run),
        "records_synced": records_synced,
        "creatives_pushed": creatives_pushed,
        "approvals_requested": len(approvals),
        "approvals_granted": sum(1 for s in approvals if s.decision and s.decision.approved),
        "estimated_value_usd": records_synced * 0.5 + creatives_pushed * 5.0,
    }
