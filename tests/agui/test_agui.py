"""AG-UI event bridge tests."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from aih.agent.approval import APIApprover
from aih.agent.models import ApprovalRequest, RunStep, RunTrace
from aih.agui.a2ui import approval_card_from_step
from aih.agui.bridge import AguiBridge
from aih.service.app import create_app
from aih.service.deps import build_state


def test_approval_a2ui_spec_renders_fields() -> None:
    spec = approval_card_from_step("publish_creative", {"connector": "creativebox"})
    assert spec["component"] == "ApprovalCard"
    assert spec["action"] == "publish_creative"
    assert spec["approve_label"] == "Approve"


def test_bridge_emits_input_request_and_a2ui() -> None:
    trace = RunTrace(run_id="r1", goal="publish creative")
    trace.add(
        RunStep(
            index=0,
            kind="approval",
            skill="publish_creative",
            approval=ApprovalRequest(
                action="publish_creative",
                summary="needs approval",
                payload_preview={"connector": "creativebox"},
                run_id="r1",
            ),
            message="awaiting",
        )
    )
    bridge = AguiBridge()
    events = bridge.bootstrap(trace)
    types = [e.type for e in events]
    assert "INPUT_REQUEST" in types
    assert "CUSTOM" in types


@pytest.mark.asyncio
async def test_agui_stream_endpoint() -> None:
    ledger = build_state(memory=None).ledger
    trace = RunTrace(run_id="stream1", goal="test goal", status="completed")
    ledger.save(trace)
    state = build_state(ledger=ledger, approver=APIApprover(), memory=None)
    app = create_app(state)
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/agui/runs/stream1/stream", timeout=5.0)
        assert resp.status_code == 200
        text = resp.text
        assert "RUN_STARTED" in text
