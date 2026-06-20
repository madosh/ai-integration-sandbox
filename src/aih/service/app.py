"""FastAPI service — wires agent, RAG, registries, metrics, and HITL approval."""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from aih.agent.models import RunTrace
from aih.config import get_settings
from aih.connectors.registry import REGISTRY
from aih.evals.online import maybe_sample_run
from aih.observability.logging import configure_logging, get_logger
from aih.service.deps import AppState, build_state

_log = get_logger("aih.service")


class StartRunRequest(BaseModel):
    goal: str = Field(min_length=1)


class StartRunResponse(BaseModel):
    run_id: str
    status: str


class ApproveRequest(BaseModel):
    approved: bool = True
    decided_by: str = "api"


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=20)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)


class SearchChunk(BaseModel):
    text: str
    score: float
    doc_id: str | None = None
    chunk_id: str | None = None
    source: str | None = None


class SearchResponse(BaseModel):
    query: str
    chunks: list[SearchChunk]
    deterministic: dict[str, str] | None = None


def _trace_summary(trace: RunTrace) -> dict[str, Any]:
    return {
        "run_id": trace.run_id,
        "goal": trace.goal,
        "status": trace.status,
        "steps": [s.model_dump() for s in trace.steps],
        "value_summary": trace.value_summary,
        "created_at": trace.created_at,
        "updated_at": trace.updated_at,
        "pending_approval": trace.pending_approval() is not None,
        "tracing": trace.tracing,
    }


def create_app(state: AppState | None = None) -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app_state = state or build_state()

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        app.state.aih = app_state
        yield

    app = FastAPI(
        title="AI Integration Hub",
        version="0.1.0",
        description="Offline-first integration + agent API",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        response: Response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/connectors")
    async def list_connectors() -> list[dict[str, Any]]:
        return [{"name": n} for n in REGISTRY.names()]

    @app.get("/skills")
    async def list_skills() -> list[dict[str, Any]]:
        return app_state.skills.describe()

    @app.get("/metrics")
    async def metrics() -> dict[str, Any]:
        return app_state.metrics()

    @app.post("/search", response_model=SearchResponse)
    async def search(body: SearchRequest) -> SearchResponse:
        retriever = app_state.build_retriever()
        result = await retriever.search(body.query, k=body.k, alpha=body.alpha, method="rrf")
        chunks = [
            SearchChunk(
                text=c.text,
                score=c.score,
                doc_id=c.provenance.doc_id,
                chunk_id=c.provenance.chunk_id,
                source=c.provenance.source,
            )
            for c in result.chunks
        ]
        deterministic = None
        if result.deterministic is not None:
            deterministic = {
                "id": result.deterministic.id,
                "partner": result.deterministic.partner,
                "source": result.deterministic.provenance.source,
            }
        return SearchResponse(query=body.query, chunks=chunks, deterministic=deterministic)

    @app.post("/search/stream")
    async def search_stream(body: SearchRequest) -> EventSourceResponse:
        retriever = app_state.build_retriever()

        async def token_stream():  # type: ignore[no-untyped-def]
            result = await retriever.search(body.query, k=body.k, alpha=body.alpha, method="rrf")
            meta = {
                "query": body.query,
                "count": len(result.chunks),
                "chunks": [
                    {
                        "text": c.text[:200],
                        "score": c.score,
                        "doc_id": c.provenance.doc_id,
                        "signals": c.provenance.signals,
                    }
                    for c in result.chunks
                ],
            }
            yield {"event": "meta", "data": json.dumps(meta)}
            text = result.chunks[0].text if result.chunks else "No results."
            for word in text.split():
                yield {"event": "token", "data": json.dumps({"t": word + " "})}
                await asyncio.sleep(0.02)
            yield {"event": "done", "data": "{}"}

        return EventSourceResponse(token_stream())  # type: ignore[no-untyped-call]

    async def _run_agent(goal: str, run_id: str) -> None:
        agent = app_state.build_agent()
        ledger = app_state.ledger
        original_save = ledger.save

        def save_and_notify(trace: RunTrace) -> None:
            original_save(trace)
            app_state.notify(trace)

        ledger.save = save_and_notify  # type: ignore[method-assign]
        try:
            result = await agent.run(goal, run_id=run_id)
            app_state.notify(result.trace)
            maybe_sample_run(_trace_summary(result.trace))
        except Exception as exc:  # noqa: BLE001
            _log.exception("run.failed", extra={"context": {"error": str(exc)}})
        finally:
            ledger.save = original_save  # type: ignore[method-assign]

    @app.post("/runs", response_model=StartRunResponse)
    async def start_run(body: StartRunRequest) -> StartRunResponse:
        run_id = uuid.uuid4().hex[:12]
        asyncio.create_task(_run_agent(body.goal, run_id))
        return StartRunResponse(run_id=run_id, status="running")

    @app.get("/runs")
    async def list_runs() -> list[dict[str, Any]]:
        return [_trace_summary(t) for t in app_state.ledger.list_runs()]

    @app.get("/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        trace = app_state.ledger.get(run_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="run not found")
        return _trace_summary(trace)

    @app.post("/runs/{run_id}/approve")
    async def approve_run(run_id: str, body: ApproveRequest) -> dict[str, Any]:
        trace = app_state.ledger.get(run_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="run not found")
        if trace.pending_approval() is None:
            raise HTTPException(status_code=409, detail="no pending approval")
        if not app_state.approver.resolve(
            run_id, approved=body.approved, decided_by=body.decided_by
        ):
            raise HTTPException(status_code=409, detail="approval gate not active")
        updated = app_state.ledger.get(run_id)
        return {
            "run_id": run_id,
            "approved": body.approved,
            "status": updated.status if updated else "unknown",
        }

    @app.get("/runs/{run_id}/stream")
    async def stream_run(run_id: str) -> EventSourceResponse:
        trace = app_state.ledger.get(run_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="run not found")

        async def event_generator():  # type: ignore[no-untyped-def]
            q = app_state.subscribe(run_id)
            current = app_state.ledger.get(run_id)
            if current:
                yield {"event": "update", "data": json.dumps(_trace_summary(current))}
            while True:
                try:
                    updated = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield {"event": "update", "data": json.dumps(_trace_summary(updated))}
                    if updated.status != "running":
                        break
                except TimeoutError:
                    yield {"event": "ping", "data": "{}"}

        return EventSourceResponse(event_generator())  # type: ignore[no-untyped-call]

    return app


app = create_app()
