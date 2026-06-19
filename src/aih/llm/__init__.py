"""LLM access layer.

All LLM usage goes through the :class:`~aih.llm.base.LLMClient` protocol so the
rest of the codebase never depends on a concrete provider. The default
:class:`~aih.llm.fake.FakeLLM` is deterministic and offline; a real adapter is
selectable via configuration.
"""

from __future__ import annotations

from aih.llm.base import (
    ChatMessage,
    Completion,
    Embedder,
    LLMClient,
    ToolCall,
    ToolSpec,
)
from aih.llm.fake import FakeLLM, HashEmbedder

__all__ = [
    "ChatMessage",
    "Completion",
    "Embedder",
    "FakeLLM",
    "HashEmbedder",
    "LLMClient",
    "ToolCall",
    "ToolSpec",
    "get_embedder",
    "get_llm",
]


def get_llm() -> LLMClient:
    """Return the configured LLM client (FakeLLM by default)."""
    from aih.config import get_settings

    settings = get_settings()
    if settings.llm_provider == "anthropic":
        from aih.llm.anthropic_adapter import AnthropicLLM

        return AnthropicLLM()
    return FakeLLM()


def get_embedder() -> Embedder:
    """Return the configured embedder (HashEmbedder by default)."""
    from aih.config import get_settings

    settings = get_settings()
    if settings.embedder != "hash":
        # Real embedder adapters are opt-in; fall back to the offline default
        # if the optional dependency isn't installed.
        try:
            from aih.llm.anthropic_adapter import AnthropicEmbedder

            return AnthropicEmbedder()
        except Exception:  # noqa: BLE001 - degrade gracefully to offline default
            return HashEmbedder(dim=settings.embedding_dim)
    return HashEmbedder(dim=settings.embedding_dim)
