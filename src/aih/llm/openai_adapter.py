"""Real provider adapter (OpenAI), behind an env flag.

A second real adapter alongside :mod:`aih.llm.anthropic_adapter`, kept here to
demonstrate that the rest of the codebase depends only on the
:class:`~aih.llm.base.LLMClient` protocol, not on any one vendor's SDK. Like the
Anthropic adapter it imports the optional ``openai`` package lazily, so the
default offline install never requires it. Selected only when
``AIH_LLM_PROVIDER=openai`` (and an API key is configured).

TODO: flesh out streaming when exercising the real path.
"""

from __future__ import annotations

import json

from aih.config import get_settings
from aih.llm.base import ChatMessage, Completion, ToolCall, ToolSpec


class OpenAILLM:
    """Adapter mapping :class:`LLMClient` onto the OpenAI Chat Completions API."""

    def __init__(self) -> None:
        self._settings = get_settings()
        if not self._settings.openai_api_key:
            raise RuntimeError("AIH_LLM_PROVIDER=openai requires AIH_OPENAI_API_KEY to be set.")

    def _client(self) -> object:
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Install the 'openai' extra: pip install -e '.[openai]'") from exc
        return openai.AsyncOpenAI(api_key=self._settings.openai_api_key)

    def _messages(self, messages: list[ChatMessage]) -> list[dict[str, str]]:
        # OpenAI accepts the system role inline, so the mapping is 1:1.
        return [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in {"system", "user", "assistant"}
        ]

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Completion:
        client = self._client()
        resp = await client.chat.completions.create(  # type: ignore[attr-defined]
            model=self._settings.openai_model,
            messages=self._messages(messages),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = resp.choices[0].message.content or ""
        return Completion(text=text, finish_reason="stop")

    async def tool_call(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
        *,
        temperature: float = 0.0,
    ) -> Completion:
        client = self._client()
        tool_defs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]
        resp = await client.chat.completions.create(  # type: ignore[attr-defined]
            model=self._settings.openai_model,
            messages=self._messages(messages),
            tools=tool_defs,
            temperature=temperature,
            max_tokens=1024,
        )
        message = resp.choices[0].message
        for call in message.tool_calls or []:
            arguments = json.loads(call.function.arguments or "{}")
            return Completion(
                tool_call=ToolCall(name=call.function.name, arguments=arguments),
                finish_reason="tool_call",
            )
        return Completion(text=message.content or "", finish_reason="stop")
