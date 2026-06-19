"""Real provider adapter (Anthropic), behind an env flag.

This is intentionally a thin stub: it imports the optional ``anthropic`` package
lazily so the default offline install never requires it. Selected only when
``AIH_LLM_PROVIDER=anthropic`` (and an API key is configured).

TODO: flesh out streaming + native tool-use mapping when exercising the real path.
"""

from __future__ import annotations

from aih.config import get_settings
from aih.llm.base import ChatMessage, Completion, ToolCall, ToolSpec


class AnthropicLLM:
    """Adapter mapping :class:`LLMClient` onto the Anthropic Messages API."""

    def __init__(self) -> None:
        self._settings = get_settings()
        if not self._settings.anthropic_api_key:
            raise RuntimeError(
                "AIH_LLM_PROVIDER=anthropic requires AIH_ANTHROPIC_API_KEY to be set."
            )

    def _client(self) -> object:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Install the 'anthropic' extra: pip install -e '.[anthropic]'"
            ) from exc
        return anthropic.AsyncAnthropic(api_key=self._settings.anthropic_api_key)

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Completion:
        client = self._client()
        system = "\n".join(m.content for m in messages if m.role == "system")
        convo = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in {"user", "assistant"}
        ]
        resp = await client.messages.create(  # type: ignore[attr-defined]
            model=self._settings.anthropic_model,
            system=system or None,
            messages=convo,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return Completion(text=text, finish_reason="stop")

    async def tool_call(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
        *,
        temperature: float = 0.0,
    ) -> Completion:
        client = self._client()
        system = "\n".join(m.content for m in messages if m.role == "system")
        convo = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in {"user", "assistant"}
        ]
        tool_defs = [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in tools
        ]
        resp = await client.messages.create(  # type: ignore[attr-defined]
            model=self._settings.anthropic_model,
            system=system or None,
            messages=convo,
            tools=tool_defs,
            temperature=temperature,
            max_tokens=1024,
        )
        for block in resp.content:
            if block.type == "tool_use":
                return Completion(
                    tool_call=ToolCall(name=block.name, arguments=dict(block.input)),
                    finish_reason="tool_call",
                )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return Completion(text=text, finish_reason="stop")


class AnthropicEmbedder:
    """Placeholder real embedder. Anthropic has no first-party embeddings API; in
    practice you'd wire Voyage/OpenAI here. Kept as a stub to document the seam."""

    def __init__(self) -> None:
        raise RuntimeError(
            "No real embedder configured. Use AIH_EMBEDDER=hash (offline) or wire a "
            "provider here (e.g. Voyage/OpenAI)."
        )

    @property
    def dim(self) -> int:  # pragma: no cover - stub
        raise NotImplementedError

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - stub
        raise NotImplementedError
