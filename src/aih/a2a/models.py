"""A2A protocol models (v0.2.x target shape)."""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

TaskState = Literal[
    "submitted",
    "working",
    "input-required",
    "completed",
    "failed",
    "canceled",
]


class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class DataPart(BaseModel):
    type: Literal["data"] = "data"
    data: dict[str, Any] = Field(default_factory=dict)


Part = TextPart | DataPart


class Message(BaseModel):
    role: Literal["user", "agent"] = "user"
    parts: list[Part]


class Artifact(BaseModel):
    name: str
    parts: list[Part]
    metadata: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: TaskState = "submitted"
    message: Message | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    run_id: str | None = None
    webhook_url: str | None = None


class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)


class AgentCard(BaseModel):
    name: str
    description: str
    version: str = "0.2.0"
    protocol_version: str = "0.2.x"
    url: str
    authentication: dict[str, str] = Field(default_factory=lambda: {"schemes": ["none"]})
    default_input_modes: list[str] = Field(default_factory=lambda: ["text"])
    default_output_modes: list[str] = Field(default_factory=lambda: ["text", "data"])
    skills: list[AgentSkill] = Field(default_factory=list)


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
    id: str | int | None = None


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Any | None = None
    error: dict[str, Any] | None = None
    id: str | int | None = None


class TaskStatusUpdateEvent(BaseModel):
    kind: Literal["status"] = "status"
    task_id: str
    state: TaskState
    message: str | None = None


class TaskArtifactUpdateEvent(BaseModel):
    kind: Literal["artifact"] = "artifact"
    task_id: str
    artifact: Artifact
