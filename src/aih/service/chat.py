"""Multi-turn chat sessions (RAG-grounded)."""

from __future__ import annotations

from typing import Any

from aih.llm.base import ChatMessage
from aih.skills.answer_from_docs import AnswerFromDocs, AnswerInput
from aih.skills.base import SkillContext

_sessions: dict[str, list[ChatMessage]] = {}


async def chat_turn(
    thread_id: str,
    message: str,
    ctx: SkillContext,
    *,
    k: int = 4,
) -> dict[str, Any]:
    """Run one chat turn; maintains message history per thread_id."""
    history = _sessions.setdefault(thread_id, [])
    history.append(ChatMessage(role="user", content=message))
    skill = AnswerFromDocs()
    out = await skill.run(AnswerInput(question=message, k=k), ctx)
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
