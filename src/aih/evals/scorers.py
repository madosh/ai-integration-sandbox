"""Eval scorers: exact match, retrieval metrics, tool-selection, LLM-as-judge."""

from __future__ import annotations

import math
import re
from typing import Any

from aih.llm.base import ChatMessage, LLMClient

_WORD_RE = re.compile(r"[a-z0-9]+")


def exact_match(prediction: str, reference: str) -> float:
    """Return 1.0 when strings match after normalization, else 0.0."""
    return 1.0 if prediction.strip().lower() == reference.strip().lower() else 0.0


def structured_match(
    prediction: dict[str, Any], reference: dict[str, Any], keys: list[str]
) -> float:
    """Fraction of listed keys whose values match between prediction and reference."""
    if not keys:
        return 1.0
    hits = sum(
        1 for k in keys if str(prediction.get(k, "")).lower() == str(reference.get(k, "")).lower()
    )
    return hits / len(keys)


def recall_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    """Recall@k for a single query."""
    if not relevant:
        return 1.0
    top = retrieved[:k]
    return len(relevant & set(top)) / len(relevant)


def mrr_for_ranks(ranks: list[int]) -> float:
    """Mean reciprocal rank from per-query ranks (1-based; 0 means not found)."""
    if not ranks:
        return 0.0
    return sum(1.0 / r if r > 0 else 0.0 for r in ranks) / len(ranks)


def ndcg_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    """nDCG@k for binary relevance."""
    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k], start=1):
        rel = 1.0 if doc_id in relevant else 0.0
        dcg += rel / math.log2(i + 1)
    ideal = min(len(relevant), k)
    if ideal == 0:
        return 1.0
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal + 1))
    return dcg / idcg if idcg > 0 else 0.0


def tool_selection_accuracy(expected: str, actual: str) -> float:
    """Return 1.0 when the planner picked the expected skill/tool name."""
    return 1.0 if expected.strip().lower() == actual.strip().lower() else 0.0


def rubric_keyword_score(answer: str, rubric: str) -> float:
    """Offline judge: fraction of rubric keywords present in the answer."""
    keywords = [w for w in _WORD_RE.findall(rubric.lower()) if len(w) > 2]
    if not keywords:
        return 1.0
    answer_tokens = set(_WORD_RE.findall(answer.lower()))
    hits = sum(1 for kw in keywords if kw in answer_tokens)
    return hits / len(keywords)


async def llm_judge(
    llm: LLMClient,
    answer: str,
    rubric: str,
    *,
    fallback_keywords: bool = True,
) -> float:
    """Score an answer against a rubric via LLM-as-judge (FakeLLM uses keyword overlap)."""
    messages = [
        ChatMessage(
            role="system",
            content=(
                "Score the answer against the rubric. " "Reply with only a number between 0 and 1."
            ),
        ),
        ChatMessage(role="user", content=f"RUBRIC: {rubric}\nANSWER: {answer}"),
    ]
    completion = await llm.complete(messages)
    text = completion.text.strip()
    try:
        val = float(text.split()[0].replace(",", "."))
        return max(0.0, min(1.0, val))
    except (ValueError, IndexError):
        if fallback_keywords:
            return rubric_keyword_score(answer, rubric)
        return 0.0
