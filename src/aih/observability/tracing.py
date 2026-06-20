"""Lightweight tracing spans for agent / skill / connector calls."""

from __future__ import annotations

import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel, Field


class Span(BaseModel):
    """One observability span (OpenTelemetry-shaped, JSON-exportable)."""

    trace_id: str
    span_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    start_ts: float = Field(default_factory=time.time)
    end_ts: float | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    status: str = "ok"

    def finish(self, status: str = "ok") -> None:
        self.end_ts = time.time()
        self.status = status

    @property
    def duration_ms(self) -> float:
        end = self.end_ts or time.time()
        return (end - self.start_ts) * 1000


class Tracer:
    """In-process tracer collecting spans for run traces."""

    def __init__(self, trace_id: str) -> None:
        self.trace_id = trace_id
        self.spans: list[Span] = []
        self.estimated_tokens: int = 0
        self.estimated_cost_usd: float = 0.0

    def start_span(self, name: str, **attributes: Any) -> Span:
        span = Span(trace_id=self.trace_id, name=name, attributes=dict(attributes))
        self.spans.append(span)
        return span

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Generator[Span, None, None]:
        s = self.start_span(name, **attributes)
        try:
            yield s
        except Exception:
            s.finish(status="error")
            raise
        else:
            s.finish()

    def add_token_estimate(self, tokens: int, cost_usd: float = 0.0) -> None:
        self.estimated_tokens += tokens
        self.estimated_cost_usd += cost_usd

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "spans": [s.model_dump() for s in self.spans],
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
        }
