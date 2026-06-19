"""Local fake partner APIs.

A single FastAPI app simulating three partners with deliberately different auth
and pagination conventions:

- ``/pulseads/*``    Bearer token, cursor pagination, rate-limited (429 + Retry-After)
- ``/novareach/*``   API-key header, offset/limit pagination, idempotent POST
- ``/creativebox/*`` Basic auth, multipart upload + download, idempotent upload

State (rate-limit arming, idempotency, stored creatives) is in-memory and resettable
via :func:`reset_state` so tests stay deterministic.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Annotated, Any

from fastapi import FastAPI, Form, Header, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse

from mock_apis.data import NOVAREACH_CAMPAIGNS, PULSEADS_CAMPAIGNS

# Accepted credentials (match .env.example defaults).
PULSEADS_TOKEN = "pulse-demo-token"
NOVAREACH_KEY = "nova-demo-key"
CREATIVEBOX_USER = "creativebox"
CREATIVEBOX_PASSWORD = "creativebox-secret"


class _State:
    """Mutable in-memory state for the mock APIs."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.pulseads_rate_limit_remaining = 0
        self.novareach_idempotency: dict[str, str] = {}
        self.creatives: dict[str, dict[str, Any]] = {}
        self.creative_idempotency: dict[str, str] = {}
        self._creative_seq = 0

    def next_creative_id(self) -> str:
        self._creative_seq += 1
        return f"cb-{self._creative_seq}"


STATE = _State()


def reset_state() -> None:
    """Reset all in-memory mock state in place (call between tests)."""
    STATE.reset()


app = FastAPI(title="aih mock partner APIs", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
# PulseAds — Bearer auth, cursor pagination, rate limiting
# --------------------------------------------------------------------------- #


def _require_bearer(authorization: str | None) -> None:
    if authorization != f"Bearer {PULSEADS_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid bearer token")


@app.post("/pulseads/_arm_rate_limit")
def pulseads_arm_rate_limit(count: int = 1) -> dict[str, int]:
    """Test hook: make the next ``count`` campaign reads return 429."""
    STATE.pulseads_rate_limit_remaining = count
    return {"armed": count}


@app.get("/pulseads/campaigns")
def pulseads_campaigns(
    authorization: Annotated[str | None, Header()] = None,
    cursor: str | None = None,
    limit: int = 2,
) -> Response:
    _require_bearer(authorization)
    if STATE.pulseads_rate_limit_remaining > 0:
        STATE.pulseads_rate_limit_remaining -= 1
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited"},
            headers={"Retry-After": "1"},
        )
    start = int(cursor) if cursor else 0
    end = start + limit
    items = PULSEADS_CAMPAIGNS[start:end]
    next_cursor = str(end) if end < len(PULSEADS_CAMPAIGNS) else None
    return JSONResponse({"items": items, "next_cursor": next_cursor})


# --------------------------------------------------------------------------- #
# NovaReach — API-key header, offset/limit pagination, idempotent POST
# --------------------------------------------------------------------------- #


def _require_api_key(x_api_key: str | None) -> None:
    if x_api_key != NOVAREACH_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


@app.get("/novareach/campaigns")
def novareach_campaigns(
    x_api_key: Annotated[str | None, Header()] = None,
    offset: int = 0,
    limit: int = 2,
) -> dict[str, Any]:
    _require_api_key(x_api_key)
    records = NOVAREACH_CAMPAIGNS[offset : offset + limit]
    return {"records": records, "total": len(NOVAREACH_CAMPAIGNS)}


@app.post("/novareach/campaigns")
def novareach_create_campaign(
    payload: dict[str, Any],
    x_api_key: Annotated[str | None, Header()] = None,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_api_key(x_api_key)
    if idempotency_key and idempotency_key in STATE.novareach_idempotency:
        return {"id": STATE.novareach_idempotency[idempotency_key], "duplicate": True}
    new_id = str(payload.get("id") or f"nr-{len(NOVAREACH_CAMPAIGNS) + 1}")
    if idempotency_key:
        STATE.novareach_idempotency[idempotency_key] = new_id
    return {"id": new_id, "duplicate": False}


# --------------------------------------------------------------------------- #
# CreativeBox — Basic auth, multipart upload + download, idempotent upload
# --------------------------------------------------------------------------- #


def _require_basic(authorization: str | None) -> None:
    expected = base64.b64encode(f"{CREATIVEBOX_USER}:{CREATIVEBOX_PASSWORD}".encode()).decode(
        "ascii"
    )
    if authorization != f"Basic {expected}":
        raise HTTPException(status_code=401, detail="invalid basic credentials")


@app.post("/creativebox/creatives")
async def creativebox_upload(
    file: UploadFile,
    name: Annotated[str, Form()],
    authorization: Annotated[str | None, Header()] = None,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_basic(authorization)
    content = await file.read()
    checksum = hashlib.sha256(content).hexdigest()
    if idempotency_key and idempotency_key in STATE.creative_idempotency:
        existing_id = STATE.creative_idempotency[idempotency_key]
        return {
            "id": existing_id,
            "name": name,
            "content_type": file.content_type,
            "size": len(content),
            "checksum": checksum,
            "duplicate": True,
        }
    creative_id = STATE.next_creative_id()
    STATE.creatives[creative_id] = {
        "name": name,
        "content": content,
        "content_type": file.content_type or "application/octet-stream",
        "checksum": checksum,
    }
    if idempotency_key:
        STATE.creative_idempotency[idempotency_key] = creative_id
    return {
        "id": creative_id,
        "name": name,
        "content_type": file.content_type,
        "size": len(content),
        "checksum": checksum,
        "duplicate": False,
    }


@app.get("/creativebox/creatives/{creative_id}")
def creativebox_download(
    creative_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    _require_basic(authorization)
    creative = STATE.creatives.get(creative_id)
    if creative is None:
        raise HTTPException(status_code=404, detail="creative not found")
    return Response(
        content=creative["content"],
        media_type=creative["content_type"],
        headers={
            "X-Creative-Name": creative["name"],
            "X-Creative-Checksum": creative["checksum"],
        },
    )
