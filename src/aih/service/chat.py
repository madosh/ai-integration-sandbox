"""Multi-turn chat sessions (RAG-grounded)."""

from __future__ import annotations

from collections import deque
from typing import Any

from aih.llm.base import ChatMessage
from aih.skills.answer_from_docs import AnswerFromDocs, AnswerInput
from aih.skills.base import SkillContext

# Cap per-thread history and total threads so a public deployment can't grow unbounded.
MAX_TURNS_PER_THREAD = 20  # messages (user + assistant)
MAX_THREADS = 200
HISTORY_TURNS_FOR_PROMPT = 6

_sessions: dict[str, deque[ChatMessage]] = {}


def _session(thread_id: str) -> deque[ChatMessage]:
    if thread_id not in _sessions and len(_sessions) >= MAX_THREADS:
        # Evict the oldest thread (dict preserves insertion order).
        _sessions.pop(next(iter(_sessions)))
    return _sessions.setdefault(thread_id, deque(maxlen=MAX_TURNS_PER_THREAD))


async def chat_turn(
    thread_id: str,
    message: str,
    ctx: SkillContext,
    *,
    k: int = 4,
) -> dict[str, Any]:
    """Run one chat turn; maintains bounded message history per thread_id."""
    history = _session(thread_id)
    prior = [f"{m.role}: {m.content}" for m in list(history)[-HISTORY_TURNS_FOR_PROMPT:]]
    history.append(ChatMessage(role="user", content=message))
    skill = AnswerFromDocs()
    out = await skill.run(AnswerInput(question=message, k=k, history=prior), ctx)
    history.append(ChatMessage(role="assistant", content=out.answer))
    return {
        "thread_id": thread_id,
        "answer": out.answer,
        "citations": [c.model_dump() for c in out.citations],
        "deterministic": out.deterministic,
        "turns": len(history) // 2,
    }


def clear_session(thread_id: str) -> None:
    _sessions.pop(thread_id, None)
