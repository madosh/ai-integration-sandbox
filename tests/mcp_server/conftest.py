"""Configure the MCP server state to run fully offline (mock APIs + HashEmbedder)."""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from mock_apis.app import app as mock_app
from mock_apis.app import reset_state

from aih.llm import HashEmbedder
from aih.mcp_server.server import STATE
from aih.rag.retriever import HybridRetriever


@pytest.fixture(autouse=True)
def _configure_state() -> Iterator[None]:
    reset_state()
    STATE.httpx_transport = httpx.ASGITransport(app=mock_app)
    STATE.retriever = HybridRetriever(embedder=HashEmbedder(dim=256))
    STATE.run_status = {}
    yield
    STATE.httpx_transport = None
    STATE.retriever = None
    STATE.run_status = {}
    reset_state()
