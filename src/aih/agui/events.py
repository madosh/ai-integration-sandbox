"""AG-UI typed event models (target ~16 types, 5 categories)."""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "RUN_STARTED",
    "RUN_FINISHED",
    "RUN_ERROR",
    "STEP_STARTED",
    "STEP_FINISHED",
    "TEXT_MESSAGE_START",
    "TEXT_MESSAGE_CONTENT",
    "TEXT_MESSAGE_END",
    "TOOL_CALL_START",
    "TOOL_CALL_ARGS",
    "TOOL_CALL_END",
    "TOOL_CALL_RESULT",
    "STATE_SNAPSHOT",
    "STATE_DELTA",
    "RAW",
    "CUSTOM",
    "INPUT_REQUEST",
]


class AguiEvent(BaseModel):
    type: EventType
    run_id: str
    timestamp: float = Field(default_factory=time.time)
    payload: dict[str, Any] = Field(default_factory=dict)


def run_started(run_id: str, goal: str) -> AguiEvent:
    return AguiEvent(type="RUN_STARTED", run_id=run_id, payload={"goal": goal})


def run_finished(run_id: str, status: str, summary: dict[str, Any]) -> AguiEvent:
    return AguiEvent(
        type="RUN_FINISHED",
        run_id=run_id,
        payload={"status": status, "summary": summary},
    )


def run_error(run_id: str, message: str) -> AguiEvent:
    return AguiEvent(type="RUN_ERROR", run_id=run_id, payload={"message": message})


def step_started(run_id: str, index: int, kind: str, skill: str | None = None) -> AguiEvent:
    return AguiEvent(
        type="STEP_STARTED",
        run_id=run_id,
        payload={"index": index, "kind": kind, "skill": skill},
    )


def step_finished(run_id: str, index: int, message: str) -> AguiEvent:
    return AguiEvent(
        type="STEP_FINISHED",
        run_id=run_id,
        payload={"index": index, "message": message},
    )


def input_request(run_id: str, action: str, preview: dict[str, Any]) -> AguiEvent:
    return AguiEvent(
        type="INPUT_REQUEST",
        run_id=run_id,
        payload={"action": action, "preview": preview, "reversibility": "low"},
    )


def state_snapshot(run_id: str, state: dict[str, Any]) -> AguiEvent:
    return AguiEvent(type="STATE_SNAPSHOT", run_id=run_id, payload={"state": state})


def state_delta(run_id: str, ops: list[dict[str, Any]]) -> AguiEvent:
    return AguiEvent(type="STATE_DELTA", run_id=run_id, payload={"ops": ops})


def custom_a2ui(run_id: str, component: dict[str, Any]) -> AguiEvent:
    return AguiEvent(
        type="CUSTOM",
        run_id=run_id,
        payload={"channel": "a2ui", "component": component},
    )
