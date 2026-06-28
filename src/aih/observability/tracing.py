"""Lightweight tracing spans for agent / skill / connector calls.

The in-process :class:`Tracer` is always on and dependency-free: it collects
OpenTelemetry-shaped spans that are persisted on the run trace and surfaced in
the dashboard. When ``AIH_OTEL_ENABLED=true`` (and the optional ``otel`` extra is
installed), :func:`export_run` additionally mirrors those spans to an OTLP
collector such as Jaeger. If OTel is disabled or its packages are missing, the
exporter is a silent no-op, so the offline-first default is never broken.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aih.config import get_settings
from aih.observability.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from opentelemetry.trace import Tracer as OTelTracer

_log = get_logger("aih.observability.tracing")


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


# --------------------------------------------------------------------------- #
# Optional OpenTelemetry export (Jaeger via OTLP).                             #
# --------------------------------------------------------------------------- #

_OTEL_TRACER: OTelTracer | None = None
_OTEL_INIT_FAILED = False


def _ns(epoch_seconds: float) -> int:
    """Convert epoch seconds to integer nanoseconds (OTel timestamp unit)."""
    return int(epoch_seconds * 1_000_000_000)


def _get_otel_tracer() -> OTelTracer | None:
    """Lazily build (once) an OTLP-backed tracer, or return ``None`` if OTel is
    disabled, already failed, or the optional packages are not installed."""
    global _OTEL_TRACER, _OTEL_INIT_FAILED
    if _OTEL_TRACER is not None:
        return _OTEL_TRACER
    if _OTEL_INIT_FAILED:
        return None

    settings = get_settings()
    if not settings.otel_enabled:
        return None

    try:
        from opentelemetry import trace as ot_trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        _OTEL_INIT_FAILED = True
        _log.warning(
            "otel.disabled",
            extra={
                "context": {
                    "reason": "opentelemetry packages not installed; "
                    "install the 'otel' extra to enable tracing"
                }
            },
        )
        return None

    try:
        provider = TracerProvider(
            resource=Resource.create({"service.name": settings.otel_service_name})
        )
        exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        ot_trace.set_tracer_provider(provider)
        _OTEL_TRACER = provider.get_tracer("aih")
        _log.info("otel.enabled", extra={"context": {"endpoint": settings.otel_endpoint}})
        return _OTEL_TRACER
    except Exception as exc:  # pragma: no cover - defensive; never break a run
        _OTEL_INIT_FAILED = True
        _log.warning("otel.init_error", extra={"context": {"error": str(exc)}})
        return None


def export_run(tracer: Tracer) -> None:
    """Mirror the in-process spans of a finished run to OTLP/Jaeger.

    No-op when OTel is disabled or unavailable. Failures are swallowed (logged)
    so observability never affects the success of an agent run.
    """
    if not tracer.spans:
        return
    otel = _get_otel_tracer()
    if otel is None:
        return

    try:
        from opentelemetry.trace import set_span_in_context
        from opentelemetry.trace.status import Status, StatusCode

        start = min(s.start_ts for s in tracer.spans)
        end = max((s.end_ts or s.start_ts) for s in tracer.spans)

        root = otel.start_span(f"run:{tracer.trace_id}", start_time=_ns(start))
        root.set_attribute("aih.trace_id", tracer.trace_id)
        root.set_attribute("aih.estimated_tokens", tracer.estimated_tokens)
        root.set_attribute("aih.estimated_cost_usd", tracer.estimated_cost_usd)
        ctx = set_span_in_context(root)

        for s in tracer.spans:
            child = otel.start_span(s.name, context=ctx, start_time=_ns(s.start_ts))
            for key, value in s.attributes.items():
                child.set_attribute(f"aih.{key}", _attr_value(value))
            if s.status == "error":
                child.set_status(Status(StatusCode.ERROR))
            child.end(end_time=_ns(s.end_ts or s.start_ts))

        root.end(end_time=_ns(end))
    except Exception as exc:  # pragma: no cover - defensive
        _log.warning("otel.export_error", extra={"context": {"error": str(exc)}})


def _attr_value(value: Any) -> Any:
    """Coerce a span attribute to an OTel-supported scalar type."""
    if isinstance(value, (str, bool, int, float)):
        return value
    return str(value)
