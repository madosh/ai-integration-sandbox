# Spec: observability — OpenTelemetry trace export

## Goal

Give operators end-to-end visibility into agent runs without compromising the offline-first
default. Each run already records in-process spans; this feature optionally exports them to an OTLP
collector (Jaeger) so a reviewer can inspect per-step latency and failures in a real trace UI.

## Inputs / Outputs

- **Inputs:**
  - The `Tracer` accumulated during `Agent.run` (`src/aih/observability/tracing.py`), containing
    `Span` records (`name`, `start_ts`, `end_ts`, `attributes`, `status`) plus token/cost estimates.
  - Settings: `otel_enabled`, `otel_service_name`, `otel_endpoint` (`src/aih/config.py`, env
    `AIH_OTEL_*`).
- **Outputs:**
  - When enabled: OTLP spans exported over gRPC — a parent `run:<trace_id>` span with one child per
    recorded span, timestamps preserved, error status mapped.
  - When disabled/unavailable: no output (silent no-op). No change to the `RunResult`/ledger.

## Behaviour

1. `Agent.run` finishes, persists the trace, then calls `export_run(tracer)`.
2. `export_run` returns immediately if the tracer has no spans.
3. `_get_otel_tracer()` lazily builds a `TracerProvider` + `OTLPSpanExporter` +
   `BatchSpanProcessor` once, cached for the process.
4. A root span is created from the earliest `start_ts`; each recorded span becomes a child with its
   original start/end time and `aih.*` attributes; `status == "error"` maps to `StatusCode.ERROR`.
5. The root span ends at the latest `end_ts`; the batch processor flushes asynchronously.

## Constraints

- **Offline-first:** default `otel_enabled=false`. The OTel packages live behind the optional
  `otel` extra and are NOT installed for the test suite.
- **Fail-closed:** missing packages (`ImportError`) or any exporter error degrade to a logged
  no-op; tracing must never raise into, slow, or fail an agent run.
- **Type-safe:** strict mypy clean; OTel imports are local/guarded.
- **Non-invasive:** reuses the existing `Tracer`/`Span` model; no new span plumbing in skills.

## Failure modes

- OTel extra not installed → log `otel.disabled` once, no-op thereafter.
- Provider/exporter init throws → log `otel.init_error`, set failed flag, no-op thereafter.
- Export throws mid-run → log `otel.export_error`, swallow; run still succeeds.
- Collector (Jaeger) down → `BatchSpanProcessor` drops/retries in the background; run unaffected.

## Success criteria (measurable)

- With OTel disabled (default), `export_run` is a no-op and the full test suite passes with the OTel
  packages absent.
- With `AIH_OTEL_ENABLED=true` but packages missing, `export_run` logs a warning and returns without
  raising.
- `docker compose up` exposes Jaeger on `:16686`; triggering a run produces a `run:<id>` trace under
  service `aih-service` with one child span per step.

## Out of scope

- Metrics and logs pipelines (only traces here).
- Sampling configuration and trace-context propagation across the connector HTTP boundary.
- Auth/TLS to the collector (compose uses an insecure local OTLP endpoint).
