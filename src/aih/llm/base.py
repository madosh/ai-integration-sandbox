"""LLM interface: protocol + shared I/O models.

The whole codebase talks to LLMs through :class:`LLMClient`. This keeps providers
swappable and lets tests run against a deterministic fake.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class ChatMessage(BaseModel):
    """A single message in a chat completion request."""

    role: Role
    content: str
    name: str | None = None


class ToolSpec(BaseModel):
    """Description of a tool the model may call (function-calling style)."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """A tool invocation requested by the model."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Completion(BaseModel):
    """The result of a completion: free text and/or a tool call."""

    text: str = ""
    tool_call: ToolCall | None = None
    finish_reason: Literal["stop", "tool_call", "length"] = "stop"


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic LLM client."""

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Completion:
        """Return a free-text completion for ``messages``."""
        ...

    async def tool_call(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
        *,
        temperature: float = 0.0,
    ) -> Completion:
        """Return a completion that may select one of ``tools``."""
        ...


@runtime_checkable
class Embedder(Protocol):
    """Provider-agnostic embedder."""

    @property
    def dim(self) -> int:
        """Embedding dimensionality."""
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...
