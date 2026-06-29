"""Bridge RunTrace updates to AG-UI events."""

from __future__ import annotations

from typing import Any

from aih.agent.models import RunTrace
from aih.agui.a2ui import approval_card_from_step, metric_card
from aih.agui.events import (
    AguiEvent,
    custom_a2ui,
    input_request,
    run_finished,
    run_started,
    state_delta,
    state_snapshot,
    step_finished,
    step_started,
)


class AguiBridge:
    """Convert trace diffs into ordered AG-UI events."""

    def __init__(self) -> None:
        self._last_step_count: dict[str, int] = {}

    def bootstrap(self, trace: RunTrace) -> list[AguiEvent]:
        events = [
            run_started(trace.run_id, trace.goal),
            state_snapshot(trace.run_id, _trace_state(trace)),
        ]
        self._last_step_count[trace.run_id] = 0
        events.extend(self.diff(trace))
        return events

    def diff(self, trace: RunTrace) -> list[AguiEvent]:
        events: list[AguiEvent] = []
        prev = self._last_step_count.get(trace.run_id, 0)
        new_steps = trace.steps[prev:]
        for step in new_steps:
            events.append(step_started(trace.run_id, step.index, step.kind, step.skill))
            if step.kind == "approval" and step.approval:
                preview = step.approval.payload_preview or {}
                events.append(input_request(trace.run_id, step.approval.action, preview))
                events.append(
                    custom_a2ui(
                        trace.run_id,
                        approval_card_from_step(step.approval.action, preview),
                    )
                )
            events.append(step_finished(trace.run_id, step.index, step.message or ""))
            events.append(
                state_delta(
                    trace.run_id,
                    [{"op": "replace", "path": "/status", "value": trace.status}],
                )
            )
        self._last_step_count[trace.run_id] = len(trace.steps)

        pending = trace.pending_approval()
        if trace.status != "running" and pending is None:
            events.append(run_finished(trace.run_id, trace.status, trace.value_summary or {}))
            if trace.value_summary:
                events.append(
                    custom_a2ui(trace.run_id, metric_card("Run metrics", trace.value_summary))
                )
        return events


def _trace_state(trace: RunTrace) -> dict[str, Any]:
    return {
        "run_id": trace.run_id,
        "goal": trace.goal,
        "status": trace.status,
        "steps": len(trace.steps),
        "pending_approval": trace.pending_approval() is not None,
    }
