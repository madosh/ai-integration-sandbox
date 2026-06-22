"""Deterministic, offline LLM + embedder fakes.

These make tests reproducible and let the whole sandbox run with zero network or
keys. The behaviour is intentionally simple and keyword/regex-driven; it is NOT a
model, but it is deterministic and good enough to exercise control flow, prompts,
tool schemas, and the agent loop.
"""

from __future__ import annotations

import hashlib
import json
import math
import re

from aih.llm.base import ChatMessage, Completion, ToolCall, ToolSpec


class FakeLLM:
    """A deterministic stand-in for a real LLM.

    - :meth:`complete` echoes a compact, rule-based summary of the prompt.
    - :meth:`tool_call` selects a tool by keyword-matching the latest user
      message against tool names/descriptions, and fabricates plausible,
      schema-shaped arguments. This is enough to drive the agent loop.
    """

    def __init__(self, *, seed: str = "aih") -> None:
        self._seed = seed

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> Completion:
        last_user = _last_user_text(messages)
        # If the prompt provides CONTEXT blocks (RAG), answer by extracting the
        # most relevant sentence deterministically.
        context = _extract_context(messages)
        if context:
            answer = _answer_from_context(last_user, context)
            return Completion(text=answer, finish_reason="stop")
        summary = _summarize(last_user)
        return Completion(text=summary, finish_reason="stop")

    async def tool_call(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec],
        *,
        temperature: float = 0.0,
    ) -> Completion:
        if not tools:
            return await self.complete(messages, temperature=temperature)
        text = _last_user_text(messages).lower()
        scored = sorted(
            tools,
            key=lambda t: _keyword_overlap(text, f"{t.name} {t.description}"),
            reverse=True,
        )
        best = scored[0]
        if _keyword_overlap(text, f"{best.name} {best.description}") == 0:
            return Completion(text=_summarize(text), finish_reason="stop")
        args = _fabricate_args(best, text)
        return Completion(
            tool_call=ToolCall(name=best.name, arguments=args),
            finish_reason="tool_call",
        )


class HashEmbedder:
    """Deterministic hashing embedder.

    Maps tokens to dimensions via a stable hash and L2-normalizes, so semantically
    overlapping texts share dimensions. Offline and reproducible.
    """

    def __init__(self, *, dim: int = 256) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for tok in _tokenize(text):
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(h[:4], "big") % self._dim
            sign = 1.0 if h[4] & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the",
    "a",
    "an",
    "to",
    "of",
    "and",
    "or",
    "for",
    "in",
    "on",
    "is",
    "are",
    "with",
    "from",
    "by",
    "this",
    "that",
    "it",
    "as",
    "at",
    "be",
    "we",
    "you",
}


def _tokenize(text: str) -> list[str]:
    return [t for t in _WORD_RE.findall(text.lower()) if t not in _STOP]


def _last_user_text(messages: list[ChatMessage]) -> str:
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return messages[-1].content if messages else ""


def _keyword_overlap(text: str, target: str) -> int:
    a = set(_tokenize(text))
    b = set(_tokenize(target))
    return len(a & b)


def _summarize(text: str) -> str:
    tokens = _tokenize(text)
    top = ", ".join(dict.fromkeys(tokens[:8]))
    return f"[fake-llm] summary of request keywords: {top}" if top else "[fake-llm] (no content)"


def _extract_context(messages: list[ChatMessage]) -> list[str]:
    blocks: list[str] = []
    for msg in messages:
        if "CONTEXT:" not in msg.content:
            continue
        body = msg.content.split("CONTEXT:", 1)[1]
        if "---\nQUESTION:" in body:
            body = body.split("---\nQUESTION:", 1)[0]
        for part in re.split(r"\n-{3,}\n", body):
            part = part.strip()
            if part:
                blocks.append(part)
    return blocks


def _answer_from_context(question: str, context: list[str]) -> str:
    # Blocks are already ranked by hybrid retrieval + rerank; use the top chunk.
    best = context[0] if context else ""
    return f"[fake-llm] Based on the provided context: {best.strip()[:400]}"


def _fabricate_args(tool: ToolSpec, text: str) -> dict[str, object]:
    """Build schema-shaped arguments from a JSON-schema-ish parameters dict."""
    props = tool.parameters.get("properties", {}) if isinstance(tool.parameters, dict) else {}
    args: dict[str, object] = {}
    # Pull obvious entities out of the text deterministically.
    connector = _guess_connector(text)
    for key, schema in props.items():
        kind = schema.get("type") if isinstance(schema, dict) else "string"
        if key in {"connector", "connector_name"} and connector:
            args[key] = connector
        elif key in {"query", "question"}:
            args[key] = text
        elif key in {"resource"}:
            args[key] = "campaigns"
        elif kind == "integer":
            args[key] = 5
        elif kind == "boolean":
            args[key] = False
        elif kind == "array":
            args[key] = []
        elif kind == "object":
            args[key] = {}
        else:
            args[key] = _maybe_default(schema, text)
    return args


def _maybe_default(schema: object, text: str) -> str:
    if isinstance(schema, dict):
        default = schema.get("default")
        if isinstance(default, str):
            return default
    m = re.search(r"\b(creative|campaign)[-_ ]?([a-z0-9]+)\b", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return text[:64]


def _guess_connector(text: str) -> str | None:
    for name in ("pulseads", "novareach", "creativebox"):
        if name in text:
            return name
    return None


def _as_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, default=str)
