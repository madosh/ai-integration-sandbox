"""Run the aih MCP server over stdio: ``python -m aih.mcp_server``."""

from __future__ import annotations

from aih.mcp_server.server import mcp


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
