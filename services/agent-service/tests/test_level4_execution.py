"""Level-4 autonomous execution: policy API + auto vs escalate routing."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from tests.conftest import TENANT_A


async def _set_policy(client, **body):
    resp = await client.put(
        f"/agents/policies/procurement_reorder?tenant_id={TENANT_A}", json=body
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_policy_upsert_and_list(client):
    created = await _set_policy(
        client, auto_execute_enabled=True, max_auto_qty=50, allowed_urgencies=["normal", "high"]
    )
    assert created["auto_execute_enabled"] is True
    assert created["max_auto_qty"] == 50

    # upsert again (update, not duplicate)
    updated = await _set_policy(client, auto_execute_enabled=False, max_auto_qty=10)
    assert updated["id"] == created["id"]
    assert updated["auto_execute_enabled"] is False

    lst = await client.get(f"/agents/policies?tenant_id={TENANT_A}")
    assert len(lst.json()) == 1


@pytest.mark.asyncio
async def test_no_policy_escalates_to_hitl(client):
    """Backward compatible: without a policy the agent still escalates (Level 3)."""
    with patch("app.service.publish", new=AsyncMock()) as mock_pub:
        resp = await client.post("/agents/reorder/run", json={
            "tenant_id": str(TENANT_A), "product_sku": "SKU-NP",
            "qty_available": 2, "reorder_point": 10,
        })
    body = resp.json()
    assert body["status"] == "proposed"
    assert body["decision"] == "escalate"
    assert body["autonomy_mode"] == "hitl"
    assert mock_pub.await_args.args[0] == "agent.action.recommended"


@pytest.mark.asyncio
async def test_within_policy_auto_executes(client):
    await _set_policy(
        client, auto_execute_enabled=True, max_auto_qty=50, allowed_urgencies=["normal", "high"]
    )
    fake_req = uuid.uuid4()
    with patch("app.service.publish", new=AsyncMock()) as mock_pub, \
         patch("app.service.create_requisition", new=AsyncMock(return_value=fake_req)) as mock_req:
        resp = await client.post("/agents/reorder/run", json={
            "tenant_id": str(TENANT_A), "product_sku": "SKU-AUTO",
            "qty_available": 2, "reorder_point": 10,   # mock -> qty 18, urgency high
        })
    body = resp.json()
    assert body["status"] == "executed"
    assert body["decision"] == "auto_execute"
    assert body["autonomy_mode"] == "auto"
    assert body["executed_ref_id"] == str(fake_req)
    mock_req.assert_awaited_once()
    # executed event carries mode=auto, and no HITL recommend event was emitted
    topics = [c.args[0] for c in mock_pub.await_args_list]
    assert "agent.action.executed" in topics
    assert "agent.action.recommended" not in topics
    exec_call = next(c for c in mock_pub.await_args_list if c.args[0] == "agent.action.executed")
    assert exec_call.args[3]["mode"] == "auto"


@pytest.mark.asyncio
async def test_over_qty_threshold_escalates(client):
    await _set_policy(client, auto_execute_enabled=True, max_auto_qty=5)  # qty 18 > 5
    with patch("app.service.publish", new=AsyncMock()) as mock_pub, \
         patch("app.service.create_requisition", new=AsyncMock()) as mock_req:
        resp = await client.post("/agents/reorder/run", json={
            "tenant_id": str(TENANT_A), "product_sku": "SKU-BIG",
            "qty_available": 2, "reorder_point": 10,
        })
    body = resp.json()
    assert body["status"] == "proposed"
    assert body["decision"] == "escalate"
    assert "exceeds max_auto_qty" in body["decision_reason"]
    mock_req.assert_not_awaited()
    assert mock_pub.await_args.args[0] == "agent.action.recommended"


@pytest.mark.asyncio
async def test_critical_urgency_escalates_by_default(client):
    # allowed only normal/high; empty stock -> mock urgency 'critical' -> escalate
    await _set_policy(client, auto_execute_enabled=True, max_auto_qty=100,
                      allowed_urgencies=["normal", "high"])
    with patch("app.service.publish", new=AsyncMock()), \
         patch("app.service.create_requisition", new=AsyncMock()) as mock_req:
        resp = await client.post("/agents/reorder/run", json={
            "tenant_id": str(TENANT_A), "product_sku": "SKU-CRIT",
            "qty_available": 0, "reorder_point": 8,
        })
    body = resp.json()
    assert body["decision"] == "escalate"
    assert "urgency" in body["decision_reason"]
    mock_req.assert_not_awaited()
