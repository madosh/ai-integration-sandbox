"""Skill: answer_from_docs (read-only).

RAG-grounded Q&A: retrieve cited chunks, ground the LLM on them, and return an
answer plus citations.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from aih.llm.base import ChatMessage
from aih.skills.base import Skill, SkillContext


class AnswerInput(BaseModel):
    question: str = Field(description="The question to answer from company docs.")
    k: int = Field(default=4, ge=1, le=20)
    history: list[str] = Field(
        default_factory=list,
        description="Prior conversation turns as 'role: content' lines (generation only; "
        "retrieval always uses the bare question).",
    )


class Citation(BaseModel):
    source: str
    doc_id: str | None = None
    chunk_id: str | None = None
    score: float | None = None


class AnswerOutput(BaseModel):
    answer: str
    citations: list[Citation]
    deterministic: dict[str, str] | None = None


class AnswerFromDocs(Skill):
    name = "answer_from_docs"
    description = "Answer a question grounded in company docs, with citations (RAG)."
    side_effect = False
    input_model: ClassVar[type[BaseModel]] = AnswerInput
    output_model: ClassVar[type[BaseModel]] = AnswerOutput

    async def run(self, payload: BaseModel, ctx: SkillContext) -> AnswerOutput:
        assert isinstance(payload, AnswerInput)
        retriever = ctx.get_retriever()
        result = await retriever.search(payload.question, k=payload.k)

        # Build a grounded prompt. The CONTEXT / --- markers let the FakeLLM extract
        # the most relevant chunk deterministically; a real LLM reads the same context.
        context_block = "\n---\n".join(rc.text for rc in result.chunks)
        conversation = ""
        if payload.history:
            turns = "\n".join(payload.history)
            conversation = f"CONVERSATION SO FAR:\n{turns}\n---\n"
        messages = [
            ChatMessage(
                role="system",
                content="Answer using ONLY the provided context. Cite sources.",
            ),
            ChatMessage(
                role="user",
                content=f"{conversation}CONTEXT:\n{context_block}\n---\nQUESTION: {payload.question}",
            ),
        ]
        completion = await ctx.llm.complete(messages)
        citations = [
            Citation(
                source=rc.provenance.source,
                doc_id=rc.provenance.doc_id,
                chunk_id=rc.provenance.chunk_id,
                score=rc.provenance.fused,
            )
            for rc in result.chunks
        ]
        deterministic = None
        if result.deterministic is not None:
            deterministic = {
                "id": result.deterministic.id,
                "partner": result.deterministic.partner,
                "source": result.deterministic.provenance.source,
            }
        return AnswerOutput(
            answer=completion.text, citations=citations, deterministic=deterministic
        )
