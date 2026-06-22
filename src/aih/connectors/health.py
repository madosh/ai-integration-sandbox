"""Connector health probes and circuit-breaker introspection."""

from __future__ import annotations

import httpx

from aih.connectors.registry import REGISTRY, default_config


async def check_connector_health(
    name: str,
    *,
    httpx_transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, object]:
    """Probe partner reachability and report transport circuit state."""
    if not REGISTRY.has(name):
        return {"name": name, "status": "unknown", "error": "connector not registered"}
    connector = REGISTRY.build(name, default_config(name, httpx_transport=httpx_transport))
    circuit = connector.transport.circuit_status()
    err: str | None = None
    try:
        resp = await connector.transport.request("GET", "/healthz")
        upstream_ok = resp.status_code == 200
    except Exception as exc:  # noqa: BLE001
        upstream_ok = False
        err = str(exc)
    finally:
        await connector.aclose()

    status = "healthy"
    if circuit.get("open"):
        status = "circuit_open"
    elif not upstream_ok:
        status = "degraded"

    return {
        "name": name,
        "status": status,
        "upstream_ok": upstream_ok,
        "circuit": circuit,
        "error": err,
    }


async def check_all_connectors(
    *,
    httpx_transport: httpx.AsyncBaseTransport | None = None,
) -> list[dict[str, object]]:
    return [
        await check_connector_health(n, httpx_transport=httpx_transport) for n in REGISTRY.names()
    ]
