"""FastAPI service — wires agent, RAG, registries, metrics, and HITL approval."""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from aih.a2a.card import build_agent_card
from aih.a2a.models import JsonRpcRequest, JsonRpcResponse
from aih.a2a.server import A2AServer
from aih.config import get_settings, validate_settings
from aih.connectors.health import check_all_connectors, check_connector_health
from aih.connectors.registry import REGISTRY
from aih.evals.online import maybe_sample_run
from aih.observability.logging import configure_logging, get_logger
from aih.service.chat import chat_turn
from aih.service.deps import AppState, build_state
from aih.service.webhooks import list_events, receive

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
    confidence: str = "low"


class ChatRequest(BaseModel):
    thread_id: str = Field(default="default", min_length=1)
    message: str = Field(min_length=1)
    k: int = Field(default=4, ge=1, le=20)


class WebhookPayload(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


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
        for warning in validate_settings(settings):
            _log.warning("config.warning", extra={"context": {"detail": warning}})
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

    _NO_AUTH_PATHS = {"/healthz", "/.well-known/agent-card.json"}

    @app.middleware("http")
    async def api_key_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        if settings.api_key is not None and request.url.path not in _NO_AUTH_PATHS:
            provided = request.headers.get("x-api-key")
            if provided != settings.api_key:
                return Response(
                    content='{"detail":"invalid or missing api key"}',
                    status_code=401,
                    media_type="application/json",
                )
        return await call_next(request)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/connectors")
    async def list_connectors() -> list[dict[str, Any]]:
        return [{"name": n} for n in REGISTRY.names()]

    @app.get("/connectors/health")
    async def connectors_health() -> list[dict[str, Any]]:
        transport = app_state.httpx_transport
        return await check_all_connectors(httpx_transport=transport)

    @app.get("/connectors/{name}/health")
    async def connector_health(name: str) -> dict[str, Any]:
        if not REGISTRY.has(name):
            raise HTTPException(status_code=404, detail="connector not found")
        return await check_connector_health(name, httpx_transport=app_state.httpx_transport)

    @app.post("/webhooks/{partner}")
    async def webhook_receiver(partner: str, body: WebhookPayload) -> dict[str, Any]:
        event = receive(partner, body.payload)
        return {"status": "received", "event_id": event["id"]}

    @app.get("/webhooks")
    async def webhook_list(partner: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return list_events(partner=partner, limit=limit)

    @app.post("/chat")
    async def chat(body: ChatRequest) -> dict[str, Any]:
        ctx = app_state.skill_context()
        return await chat_turn(body.thread_id, body.message, ctx, k=body.k)

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
        return SearchResponse(
            query=body.query,
            chunks=chunks,
            deterministic=deterministic,
            confidence=result.confidence,
        )

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

    app_state.a2a_server = A2AServer(
        app_state.a2a_state,
        start_run=_run_agent,
        get_trace=app_state.ledger.get,
        resolve_approval=lambda rid, ok, who: app_state.approver.resolve(
            rid, approved=ok, decided_by=who
        ),
    )

    @app.post("/runs", response_model=StartRunResponse)
    async def start_run(body: StartRunRequest) -> StartRunResponse:
        run_id = uuid.uuid4().hex[:12]
        asyncio.create_task(_run_agent(body.goal, run_id))
        return StartRunResponse(run_id=run_id, status="running")

    @app.get("/runs")
    async def list_runs(
        limit: int = Query(default=50, ge=1, le=200),
        cursor: str | None = Query(default=None),
        status: str | None = Query(default=None),
    ) -> dict[str, Any]:
        all_runs = app_state.ledger.list_runs()
        if status is not None:
            all_runs = [t for t in all_runs if t.status == status]
        total = len(all_runs)
        if cursor is not None:
            run_ids = [t.run_id for t in all_runs]
            try:
                idx = run_ids.index(cursor)
                all_runs = all_runs[idx + 1 :]
            except ValueError:
                raise HTTPException(status_code=400, detail="invalid cursor")
        page = all_runs[:limit]
        next_cursor = page[-1].run_id if len(all_runs) > limit else None
        return {
            "runs": [_trace_summary(t) for t in page],
            "next_cursor": next_cursor,
            "total": total,
        }

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

    @app.get("/.well-known/agent-card.json")
    async def agent_card() -> dict[str, Any]:
        return build_agent_card().model_dump()

    @app.post("/a2a")
    async def a2a_rpc(body: JsonRpcRequest) -> JsonRpcResponse:
        if app_state.a2a_server is None:
            raise HTTPException(status_code=503, detail="a2a not ready")
        return await app_state.a2a_server.handle_rpc(body)

    @app.get("/a2a/tasks/{task_id}/events")
    async def a2a_task_events(task_id: str) -> EventSourceResponse:
        if app_state.a2a_server is None:
            raise HTTPException(status_code=503, detail="a2a not ready")

        async def gen():  # type: ignore[no-untyped-def]
            q = app_state.a2a_server.subscribe(task_id)  # type: ignore[union-attr]
            task = app_state.a2a_server.get_task(task_id)  # type: ignore[union-attr]
            if task:
                yield {"event": "status", "data": json.dumps({"state": task.state})}
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield {"event": ev.get("kind", "status"), "data": json.dumps(ev)}
                    if ev.get("state") in {"completed", "failed", "canceled"}:
                        break
                except TimeoutError:
                    yield {"event": "ping", "data": "{}"}

        return EventSourceResponse(gen())  # type: ignore[no-untyped-call]

    class A2AResumeRequest(BaseModel):
        approved: bool = True
        decided_by: str = "a2a-client"

    @app.post("/a2a/tasks/{task_id}/resume")
    async def a2a_resume(task_id: str, body: A2AResumeRequest) -> dict[str, Any]:
        if app_state.a2a_server is None:
            raise HTTPException(status_code=503, detail="a2a not ready")
        ok = await app_state.a2a_server.resume_task(
            task_id, approved=body.approved, decided_by=body.decided_by
        )
        if not ok:
            raise HTTPException(status_code=409, detail="cannot resume task")
        return {"task_id": task_id, "resumed": True, "approved": body.approved}

    class AguiInputRequest(BaseModel):
        action: str = Field(description="approve | deny | cancel")
        decided_by: str = "dashboard"

    @app.get("/agui/runs/{run_id}/stream")
    async def agui_stream(run_id: str) -> EventSourceResponse:
        trace = app_state.ledger.get(run_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="run not found")

        async def gen():  # type: ignore[no-untyped-def]
            q = app_state.subscribe_agui(run_id)
            current = app_state.ledger.get(run_id)
            if current:
                for ev in app_state.agui_bridge.bootstrap(current):
                    yield {"event": ev.type, "data": json.dumps(ev.model_dump())}
                if current.status != "running":
                    return
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield {
                        "event": str(payload.get("type", "CUSTOM")),
                        "data": json.dumps(payload),
                    }
                    if payload.get("type") in {"RUN_FINISHED", "RUN_ERROR"}:
                        break
                except TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    current = app_state.ledger.get(run_id)
                    if current and current.status != "running":
                        break

        return EventSourceResponse(gen())  # type: ignore[no-untyped-call]

    @app.post("/agui/runs/{run_id}/input")
    async def agui_input(run_id: str, body: AguiInputRequest) -> dict[str, Any]:
        trace = app_state.ledger.get(run_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="run not found")
        if body.action == "cancel":
            trace.status = "denied"
            app_state.ledger.save(trace)
            app_state.notify(trace)
            return {"run_id": run_id, "status": "cancelled"}
        approved = body.action == "approve"
        if trace.pending_approval() is None:
            raise HTTPException(status_code=409, detail="no pending approval")
        if not app_state.approver.resolve(run_id, approved=approved, decided_by=body.decided_by):
            raise HTTPException(status_code=409, detail="approval gate not active")
        updated = app_state.ledger.get(run_id)
        return {"run_id": run_id, "approved": approved, "status": updated.status if updated else ""}

    return app


app = create_app()
