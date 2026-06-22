"""Versioned prompt templates for reproducible LLM calls."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str, version: str = "v1") -> tuple[str, str]:
    """Load a prompt template; returns (text, prompt_id)."""
    path = PROMPTS_DIR / name / f"{version}.txt"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {name}/{version}")
    return path.read_text(encoding="utf-8"), f"{name}/{version}"
