"""A2A task registry and JSON-RPC handler."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

import httpx

from aih.a2a.models import (
    Artifact,
    DataPart,
    JsonRpcRequest,
    JsonRpcResponse,
    Message,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TextPart,
)
from aih.agent.models import RunTrace


@dataclass
class A2AState:
    tasks: dict[str, Task] = field(default_factory=dict)
    subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = field(default_factory=dict)
    run_to_task: dict[str, str] = field(default_factory=dict)


def _goal_from_message(msg: Message) -> str:
    parts = [p.text for p in msg.parts if isinstance(p, TextPart)]
    return " ".join(parts) if parts else "unspecified task"


def sanitize_artifact(artifact: Artifact) -> Artifact:
    """Treat peer text as data — strip instruction-like prefixes."""
    clean: list[TextPart | DataPart] = []
    for p in artifact.parts:
        if isinstance(p, TextPart):
            text = p.text.replace("ignore previous", "[filtered]")
            clean.append(TextPart(text=text))
        else:
            clean.append(p)
    return Artifact(name=artifact.name, parts=clean, metadata=artifact.metadata)


class A2AServer:
    def __init__(
        self,
        state: A2AState,
        *,
        start_run: Callable[[str, str], Coroutine[Any, Any, None]],
        get_trace: Callable[[str], RunTrace | None],
        resolve_approval: Callable[[str, bool, str], bool],
    ) -> None:
        self._state = state
        self._start_run = start_run
        self._get_trace = get_trace
        self._resolve_approval = resolve_approval

    def subscribe(self, task_id: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._state.subscribers.setdefault(task_id, []).append(q)
        return q

    def _emit(self, task_id: str, event: dict[str, Any]) -> None:
        for q in self._state.subscribers.get(task_id, []):
            q.put_nowait(event)

    async def _push_webhook(self, task: Task, event: dict[str, Any]) -> None:
        if not task.webhook_url:
            return
        try:
            async with httpx.AsyncClient() as client:
                await client.post(task.webhook_url, json=event, timeout=2.0)
        except httpx.HTTPError:
            pass

    async def handle_rpc(self, body: JsonRpcRequest) -> JsonRpcResponse:
        if body.method != "message/send":
            return JsonRpcResponse(
                id=body.id,
                error={"code": -32601, "message": f"method not found: {body.method}"},
            )
        params = body.params
        msg = Message.model_validate(params.get("message", {"parts": []}))
        task = Task(
            message=msg,
            webhook_url=params.get("webhook_url"),
            metadata=params.get("metadata", {}),
        )
        goal = _goal_from_message(msg)
        self._state.tasks[task.id] = task
        self._emit(task.id, TaskStatusUpdateEvent(task_id=task.id, state="submitted").model_dump())
        task.state = "working"
        task.updated_at = time.time()
        self._emit(task.id, TaskStatusUpdateEvent(task_id=task.id, state="working").model_dump())
        run_id = task.id
        task.run_id = run_id
        self._state.run_to_task[run_id] = task.id
        asyncio.create_task(self._start_run(goal, run_id))
        asyncio.create_task(self._watch_run(task.id, run_id))
        return JsonRpcResponse(id=body.id, result={"task": task.model_dump()})

    async def _watch_run(self, task_id: str, run_id: str) -> None:
        task = self._state.tasks[task_id]
        seen_approval = False
        for _ in range(120):
            await asyncio.sleep(0.05)
            trace = self._get_trace(run_id)
            if trace is None:
                continue
            if trace.pending_approval() and not seen_approval:
                seen_approval = True
                task.state = "input-required"
                ev = TaskStatusUpdateEvent(
                    task_id=task_id,
                    state="input-required",
                    message="awaiting human approval",
                ).model_dump()
                self._emit(task_id, ev)
                await self._push_webhook(task, ev)
            if trace.status != "running":
                if trace.status == "completed":
                    task.state = "completed"
                    artifact = Artifact(
                        name="result",
                        parts=[DataPart(data=trace.value_summary or {})],
                    )
                    task.artifacts.append(artifact)
                    self._emit(
                        task_id,
                        TaskArtifactUpdateEvent(task_id=task_id, artifact=artifact).model_dump(),
                    )
                elif trace.status == "denied":
                    task.state = "failed"
                    self._emit(
                        task_id,
                        TaskStatusUpdateEvent(
                            task_id=task_id, state="failed", message="denied"
                        ).model_dump(),
                    )
                else:
                    task.state = "failed"
                final = TaskStatusUpdateEvent(task_id=task_id, state=task.state).model_dump()
                self._emit(task_id, final)
                await self._push_webhook(task, final)
                return

    async def resume_task(self, task_id: str, *, approved: bool, decided_by: str = "a2a") -> bool:
        task = self._state.tasks.get(task_id)
        if task is None or task.run_id is None:
            return False
        if task.state != "input-required":
            return False
        ok = self._resolve_approval(task.run_id, approved, decided_by)
        if ok:
            task.state = "working"
            self._emit(
                task_id,
                TaskStatusUpdateEvent(
                    task_id=task_id, state="working", message="resumed"
                ).model_dump(),
            )
        return ok

    def get_task(self, task_id: str) -> Task | None:
        return self._state.tasks.get(task_id)
