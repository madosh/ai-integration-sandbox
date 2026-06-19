"""MCP server exposing connector + RAG capabilities as tools.

See ``specs/mcp.md``. Run with ``python -m aih.mcp_server`` (stdio transport).
"""

from __future__ import annotations

from aih.mcp_server.server import STATE, mcp

__all__ = ["STATE", "mcp"]
