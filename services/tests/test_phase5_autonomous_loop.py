"""
Phase 5 Task 9: Autonomous Loop Integration Test (live e2e)

Proves the full AI-with-human-in-the-loop loop end to end through Kafka:

  sales order confirmed
    -> inventory reserves stock, available drops to/below reorder point
    -> inventory.stock.low
    -> Agent (LLM/mock) produces a reorder recommendation
    -> agent.action.recommended
    -> Approval Center opens a 3-step agent_action workflow
    -> (human approves all 3 steps)
    -> approval.request.approved
    -> Agent executes: creates a procurement requisition
    -> agent.action.executed

Requires the live stack running with Kafka topics created:
    sales       -> http://localhost:8002
    inventory   -> http://localhost:8003
    procurement -> http://localhost:8004
    approval    -> http://localhost:8006
    agent       -> http://localhost:8008   (MODEL_PROVIDER=mock)

Run with: pytest services/tests/test_phase5_autonomous_loop.py -v -s -o asyncio_mode=auto
"""

import asyncio
import uuid

import httpx
import pytest
import pytest_asyncio

SALES_URL = "http://localhost:8002"
INVENTORY_URL = "http://localhost:8003"
PROCUREMENT_URL = "http://localhost:8004"
APPROVAL_URL = "http://localhost:8006"
AGENT_URL = "http://localhost:8008"

TENANT_ID = "00000000-0000-0000-0000-000000000055"


@pytest_asyncio.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client


@pytest.mark.asyncio
async def test_services_health(http_client):
    for url in (SALES_URL, INVENTORY_URL, PROCUREMENT_URL, APPROVAL_URL, AGENT_URL):
        resp = await http_client.get(f"{url}/health")
        assert resp.status_code == 200, f"{url} not healthy"


@pytest.mark.asyncio
async def test_full_autonomous_reorder_loop(http_client):
    sku = f"SKU-{uuid.uuid4().hex[:12]}"

    # 1. Stock with a reorder point that a single order will breach
    wh = await http_client.post(f"{INVENTORY_URL}/warehouses/", json={
        "tenant_id": TENANT_ID, "name": "Auto WH", "code": f"WH-{uuid.uuid4().hex[:8]}",
    })
    assert wh.status_code == 201
    stock = await http_client.post(f"{INVENTORY_URL}/stock/", json={
        "tenant_id": TENANT_ID,
        "warehouse_id": wh.json()["id"],
        "product_sku": sku,
        "product_name": "Auto Product",
        "qty_on_hand": 12,
        "reorder_point": 10,
    })
    assert stock.status_code == 201

    # 2. Sales order for 5 units, then confirm -> sales.order.created
    order = await http_client.post(f"{SALES_URL}/orders/", json={
        "tenant_id": TENANT_ID,
        "items": [{"product_sku": sku, "product_name": "Auto Product",
                   "quantity": 5, "unit_price": "10.00"}],
    })
    assert order.status_code == 201
    order_id = order.json()["id"]
    confirm = await http_client.patch(f"{SALES_URL}/orders/{order_id}", json={"status": "confirmed"})
    assert confirm.status_code == 200

    # 3. inventory reserves -> stock.low -> agent recommends. Poll for the recommendation.
    recommendation = None
    for _ in range(15):
        await asyncio.sleep(1)
        recs = await http_client.get(f"{AGENT_URL}/agents/recommendations?tenant_id={TENANT_ID}")
        match = [r for r in recs.json() if r["input_context"].get("product_sku") == sku]
        if match:
            recommendation = match[0]
            break
    assert recommendation is not None, "Agent never produced a recommendation"
    assert recommendation["status"] == "proposed"
    assert recommendation["recommendation"]["recommended_qty"] > 0
    rec_id = recommendation["id"]

    # 4. Approval Center opened an agent_action workflow for this recommendation
    approval = None
    for _ in range(10):
        reqs = await http_client.get(f"{APPROVAL_URL}/approval-requests/?tenant_id={TENANT_ID}")
        match = [
            r for r in reqs.json()
            if r["reference_id"] == rec_id and r["request_type"] == "agent_action"
        ]
        if match:
            approval = match[0]
            break
        await asyncio.sleep(1)
    assert approval is not None, "Approval workflow was never opened for the recommendation"
    assert len(approval["steps"]) == 3

    # 5. Human approves all three steps -> approval.request.approved
    approval_id = approval["id"]
    for step in sorted(approval["steps"], key=lambda s: s["order_number"]):
        r = await http_client.post(
            f"{APPROVAL_URL}/approval-requests/{approval_id}/steps/{step['id']}/approve",
            json={"approver_id": "e2e-manager", "message": f"ok {step['approver_role']}"},
        )
        assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # 6. Agent executes -> recommendation becomes executed with a requisition ref
    executed = None
    for _ in range(15):
        await asyncio.sleep(1)
        rec = await http_client.get(f"{AGENT_URL}/agents/recommendations/{rec_id}")
        if rec.json()["status"] == "executed":
            executed = rec.json()
            break
    assert executed is not None, "Agent never executed the approved recommendation"
    assert executed["executed_ref_id"] is not None

    # 7. The requisition really exists in procurement
    reqs = await http_client.get(f"{PROCUREMENT_URL}/requisitions/?tenant_id={TENANT_ID}")
    skus = [r["product_sku"] for r in reqs.json()]
    assert sku in skus, "Procurement requisition was not created by the agent"
