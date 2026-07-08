"""Real provider adapters stay offline-safe and gate on their API key.

These run fully offline: constructing an adapter only checks configuration and
never imports the optional vendor SDK (that import is lazy, in ``_client``).
"""

from __future__ import annotations

import pytest

import aih.llm.anthropic_adapter as anthropic_adapter
import aih.llm.openai_adapter as openai_adapter
from aih.config import Settings


def test_openai_adapter_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_adapter, "get_settings", lambda: Settings(openai_api_key=None))
    with pytest.raises(RuntimeError, match="AIH_OPENAI_API_KEY"):
        openai_adapter.OpenAILLM()


def test_openai_adapter_constructs_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        openai_adapter,
        "get_settings",
        lambda: Settings(llm_provider="openai", openai_api_key="sk-test"),
    )
    # Construction must not import the optional `openai` package.
    assert openai_adapter.OpenAILLM() is not None


def test_anthropic_adapter_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        anthropic_adapter, "get_settings", lambda: Settings(anthropic_api_key=None)
    )
    with pytest.raises(RuntimeError, match="AIH_ANTHROPIC_API_KEY"):
        anthropic_adapter.AnthropicLLM()
