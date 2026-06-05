"""
Phase 4 Task 7: Cross-Domain Integration Test (live e2e)

Proves the full Procurement -> Accounting -> Approval event chain:
1. Create requisition in Procurement Service
2. Create PO from the requisition
3. Confirm PO -> publishes procurement.po.created
4. Accounting consumer auto-creates a draft invoice (accounting.invoice.created)
5. Approval consumer opens a 3-step workflow for the PO
6. Approve all 3 steps (manager -> director -> cfo) -> approval.request.approved
7. Record a payment against the auto-created invoice -> invoice becomes paid

Requires the live stack running with Kafka topics created:
    Procurement  -> http://localhost:8004
    Accounting   -> http://localhost:8005
    Approval     -> http://localhost:8006

Run with: pytest services/tests/test_phase4_cross_domain.py -v -s
"""

import asyncio
import uuid

import httpx
import pytest
import pytest_asyncio

PROCUREMENT_URL = "http://localhost:8004"
ACCOUNTING_URL = "http://localhost:8005"
APPROVAL_URL = "http://localhost:8006"

TENANT_ID = "00000000-0000-0000-0000-000000000042"


@pytest_asyncio.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client


@pytest.mark.asyncio
async def test_services_health(http_client):
    for url in (PROCUREMENT_URL, ACCOUNTING_URL, APPROVAL_URL):
        resp = await http_client.get(f"{url}/health")
        assert resp.status_code == 200, f"{url} not healthy"
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_full_procure_to_pay_flow(http_client):
    sku = f"SKU-{uuid.uuid4().hex[:8]}"

    # 1. Requisition
    req = await http_client.post(f"{PROCUREMENT_URL}/requisitions/", json={
        "tenant_id": TENANT_ID,
        "product_sku": sku,
        "quantity": 5,
        "reason": "phase4 e2e",
    })
    assert req.status_code == 201
    requisition_id = req.json()["id"]

    # 2. Purchase order from requisition
    po = await http_client.post(f"{PROCUREMENT_URL}/purchase-orders/", json={
        "tenant_id": TENANT_ID,
        "requisition_id": requisition_id,
        "vendor_id": str(uuid.uuid4()),
        "items": [
            {"product_sku": sku, "quantity": 5, "unit_price": "20.00"},
        ],
    })
    assert po.status_code == 201
    po_id = po.json()["id"]
    assert po.json()["total_amount"] == "100.00"

    # 3. Confirm PO -> publishes procurement.po.created
    confirm = await http_client.patch(f"{PROCUREMENT_URL}/purchase-orders/{po_id}", json={
        "status": "confirmed",
    })
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"

    # 4 + 5. Wait for Accounting + Approval consumers to react
    await asyncio.sleep(3)

    # 4. Accounting auto-created an invoice for this PO
    invoices = await http_client.get(f"{ACCOUNTING_URL}/invoices/?tenant_id={TENANT_ID}")
    assert invoices.status_code == 200
    po_invoices = [i for i in invoices.json() if i["po_id"] == po_id]
    assert len(po_invoices) == 1, f"Expected 1 auto-invoice for PO {po_id}"
    invoice = po_invoices[0]
    assert invoice["total_amount"] == "100.00"
    assert invoice["status"] == "pending"
    invoice_id = invoice["id"]

    # 5. Approval opened a 3-step workflow referencing the PO
    requests = await http_client.get(f"{APPROVAL_URL}/approval-requests/?tenant_id={TENANT_ID}")
    assert requests.status_code == 200
    po_requests = [
        r for r in requests.json()
        if r["reference_id"] == po_id and r["request_type"] == "procurement_po"
    ]
    assert len(po_requests) == 1, f"Expected 1 approval workflow for PO {po_id}"
    approval = po_requests[0]
    assert len(approval["steps"]) == 3
    approval_id = approval["id"]

    # 6. Approve all 3 steps in order
    for step in sorted(approval["steps"], key=lambda s: s["order_number"]):
        r = await http_client.post(
            f"{APPROVAL_URL}/approval-requests/{approval_id}/steps/{step['id']}/approve",
            json={"approver_id": "e2e-user", "message": f"approve {step['approver_role']}"},
        )
        assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # 7. Record payment against the auto-created invoice
    pay = await http_client.post(f"{ACCOUNTING_URL}/payments/", json={
        "tenant_id": TENANT_ID,
        "invoice_id": invoice_id,
        "amount": "100.00",
        "method": "bank_transfer",
        "reference": "e2e-pay-1",
    })
    assert pay.status_code == 201

    paid = await http_client.get(f"{ACCOUNTING_URL}/invoices/{invoice_id}")
    assert paid.json()["status"] == "paid"
