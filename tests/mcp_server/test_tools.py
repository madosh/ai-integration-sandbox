"""Drive each MCP tool via the in-memory MCP client.

The client session is opened with ``async with`` *inside* each test so the anyio
task scope is entered and exited in the same task (avoids a teardown RuntimeError
when used as an async-generator fixture under pytest-asyncio).
"""

from __future__ import annotations

from typing import Any

from mcp.shared.memory import create_connected_server_and_client_session

from aih.mcp_server.server import mcp


def _structured(result: Any) -> dict[str, Any]:
    data = result.structuredContent
    assert data is not None, "tool returned no structured content"
    return data


async def test_list_connectors_reports_capabilities() -> None:
    async with create_connected_server_and_client_session(mcp) as client:
        data = _structured(await client.call_tool("list_connectors", {}))
    names = {c["name"] for c in data["connectors"]}
    assert names == {"pulseads", "novareach", "creativebox"}
    caps = {c["name"]: c["capabilities"] for c in data["connectors"]}
    assert "get_records" in caps["pulseads"]
    assert "push_creative" in caps["creativebox"]


async def test_fetch_records_returns_normalized() -> None:
    async with create_connected_server_and_client_session(mcp) as client:
        data = _structured(
            await client.call_tool(
                "fetch_records", {"connector": "novareach", "resource": "campaigns"}
            )
        )
    assert data["ok"] is True
    assert data["count"] == 4
    assert data["records"][0]["partner"] == "novareach"
    assert "raw" not in data["records"][0]


async def test_push_creative_requires_approval() -> None:
    async with create_connected_server_and_client_session(mcp) as client:
        data = _structured(
            await client.call_tool(
                "push_creative",
                {"connector": "creativebox", "file_ref": "s3://bucket/banner.png"},
            )
        )
    assert data["status"] == "requires_approval"
    assert data["approval"]["action"] == "push_creative"
    assert data["approval"]["connector"] == "creativebox"


async def test_unknown_connector_returns_typed_error() -> None:
    async with create_connected_server_and_client_session(mcp) as client:
        data = _structured(await client.call_tool("fetch_records", {"connector": "does-not-exist"}))
    assert data["ok"] is False
    assert data["error"]["type"] == "unknown_connector"


async def test_search_docs_returns_cited_hits() -> None:
    async with create_connected_server_and_client_session(mcp) as client:
        data = _structured(
            await client.call_tool(
                "search_docs", {"query": "how do I handle a 429 rate limit", "k": 3}
            )
        )
    assert data["ok"] is True
    assert data["hits"]
    assert data["hits"][0]["citation"]["source"].startswith("doc:")


async def test_get_run_status_unknown() -> None:
    async with create_connected_server_and_client_session(mcp) as client:
        data = _structured(await client.call_tool("get_run_status", {"run_id": "missing"}))
    assert data["status"] == "unknown"
