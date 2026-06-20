"""FastMCP server exposing connector + RAG capabilities as tools.

Tools are intentionally thin and defensive: typed Pydantic args/results and
explicit error envelopes (never a raw stack trace across the protocol). Side
effects (``push_creative``) are NOT executed here — they return a
``requires_approval`` envelope that the agent layer (Phase 4) must resolve.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from aih.agent.approval import ApprovalRequest
from aih.connectors.base import Connector
from aih.connectors.errors import ConnectorError
from aih.connectors.registry import REGISTRY, default_config
from aih.mcp_server.envelopes import (
    ApprovalEnvelope,
    Citation,
    ConnectorInfo,
    ConnectorsResult,
    DeterministicHit,
    RecordsResult,
    RunStatusResult,
    SearchHit,
    SearchResultEnvelope,
    ToolError,
)
from aih.observability.logging import get_logger
from aih.rag.corpus import CORPUS_DIR
from aih.rag.retriever import HybridRetriever

_log = get_logger("aih.mcp_server")


@dataclass
class ServerState:
    """Shared state so tests can inject an in-process transport + retriever."""

    httpx_transport: httpx.AsyncBaseTransport | None = None
    retriever: HybridRetriever | None = None
    run_status: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_connector(self, name: str) -> Connector:
        config = default_config(name, httpx_transport=self.httpx_transport)
        return REGISTRY.build(name, config)

    def get_retriever(self) -> HybridRetriever:
        if self.retriever is None:
            self.retriever = HybridRetriever()
        return self.retriever


#: Process-wide state (reconfigured by tests).
STATE = ServerState()

mcp = FastMCP("aih")


def _capabilities(connector: Connector) -> list[str]:
    cls = type(connector)
    caps = []
    if cls.get_records is not Connector.get_records:
        caps.append("get_records")
    if cls.push_record is not Connector.push_record:
        caps.append("push_record")
    if cls.push_creative is not Connector.push_creative:
        caps.append("push_creative")
    if cls.get_creative is not Connector.get_creative:
        caps.append("get_creative")
    return caps


@mcp.tool()
async def list_connectors() -> ConnectorsResult:
    """List available connectors and the capabilities each supports."""
    infos: list[ConnectorInfo] = []
    for name in REGISTRY.names():
        connector = STATE.get_connector(name)
        try:
            infos.append(ConnectorInfo(name=name, capabilities=_capabilities(connector)))
        finally:
            await connector.aclose()
    return ConnectorsResult(connectors=infos)


@mcp.tool()
async def fetch_records(
    connector: str,
    resource: str = "campaigns",
    filters: dict[str, Any] | None = None,
    limit: int = 100,
) -> RecordsResult:
    """Fetch normalized records from a connector (GET, paginated)."""
    if not REGISTRY.has(connector):
        return RecordsResult(
            ok=False,
            connector=connector,
            resource=resource,
            error=ToolError(type="unknown_connector", message=f"unknown connector: {connector!r}"),
        )
    conn = STATE.get_connector(connector)
    try:
        records: list[dict[str, Any]] = []
        async for campaign in conn.get_records(resource, filters=filters):
            records.append(campaign.model_dump(exclude={"raw"}))
            if len(records) >= limit:
                break
        return RecordsResult(
            ok=True,
            connector=connector,
            resource=resource,
            count=len(records),
            records=records,
        )
    except NotImplementedError as exc:
        return RecordsResult(
            ok=False,
            connector=connector,
            resource=resource,
            error=ToolError(type="unsupported", message=str(exc)),
        )
    except ConnectorError as exc:
        return RecordsResult(
            ok=False,
            connector=connector,
            resource=resource,
            error=ToolError(type=type(exc).__name__, message=str(exc)),
        )
    finally:
        await conn.aclose()


@mcp.tool()
async def push_creative(connector: str, file_ref: str, name: str = "creative") -> ApprovalEnvelope:
    """Request publishing a creative. Returns requires_approval; does NOT execute."""
    return ApprovalEnvelope(
        approval=ApprovalRequest(
            action="push_creative",
            connector=connector,
            summary=f"Publish creative {name!r} ({file_ref}) to {connector}",
            payload_preview={"connector": connector, "file_ref": file_ref, "name": name},
            reversibility="low",
        )
    )


@mcp.tool()
async def get_run_status(run_id: str) -> RunStatusResult:
    """Return the status of an agent run (run ledger is wired in Phase 6)."""
    entry = STATE.run_status.get(run_id)
    if entry is None:
        return RunStatusResult(ok=True, run_id=run_id, status="unknown", detail="no such run")
    return RunStatusResult(
        ok=True,
        run_id=run_id,
        status=str(entry.get("status", "unknown")),
        detail=entry.get("detail"),
    )


@mcp.tool()
async def search_docs(query: str, k: int = 5) -> SearchResultEnvelope:
    """Search company docs with hybrid RAG; returns cited hits + optional record."""
    try:
        retriever = STATE.get_retriever()
        result = await retriever.search(query, k=k)
        hits = [
            SearchHit(
                text=rc.text,
                score=rc.score,
                citation=Citation(
                    source=rc.provenance.source,
                    doc_id=rc.provenance.doc_id,
                    chunk_id=rc.provenance.chunk_id,
                    score=rc.provenance.fused,
                    signals=rc.provenance.signals,
                ),
            )
            for rc in result.chunks
        ]
        deterministic = None
        if result.deterministic is not None:
            deterministic = DeterministicHit(
                id=result.deterministic.id,
                partner=result.deterministic.partner,
                data=result.deterministic.data,
                source=result.deterministic.provenance.source,
            )
        return SearchResultEnvelope(query=query, hits=hits, deterministic=deterministic)
    except Exception as exc:  # noqa: BLE001 - never raise raw across the boundary
        _log.exception("search_docs failed")
        return SearchResultEnvelope(
            ok=False, query=query, error=ToolError(type="search_error", message=str(exc))
        )


@mcp.resource("corpus://{doc_id}")
async def corpus_resource(doc_id: str) -> str:
    """MCP resource: read a corpus markdown document by stem id."""
    path = CORPUS_DIR / f"{doc_id}.md"
    if not path.exists():
        return f"error: document {doc_id!r} not found"
    return path.read_text(encoding="utf-8")


@mcp.resource("corpus://index")
async def corpus_index() -> str:
    """MCP resource: list available corpus document ids."""
    ids = sorted(p.stem for p in CORPUS_DIR.glob("*.md"))
    return "\n".join(ids)


@mcp.prompt()
def integration_runbook(goal: str = "sync campaigns") -> str:
    """Prompt template for integration automation goals."""
    return (
        f"You are an integration agent. Goal: {goal}. "
        "Use read-only tools unless the goal requires a side effect. "
        "Side effects require human approval."
    )
