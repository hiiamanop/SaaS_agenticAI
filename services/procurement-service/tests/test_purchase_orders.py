import uuid
from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_create_purchase_order_with_items(client):
    resp = await client.post("/purchase-orders/", json={
        "tenant_id": str(TENANT_A),
        "vendor_id": str(uuid.uuid4()),
        "items": [
            {"product_sku": "SKU-A", "quantity": 2, "unit_price": "10.00"},
            {"product_sku": "SKU-B", "quantity": 3, "unit_price": "5.00"},
        ],
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["total_amount"] == "35.00"
    assert len(body["items"]) == 2
    assert body["order_number"].startswith("PO-")


@pytest.mark.asyncio
async def test_get_purchase_order(client):
    create = await client.post("/purchase-orders/", json={
        "tenant_id": str(TENANT_A),
        "items": [{"product_sku": "SKU-X", "quantity": 1, "unit_price": "9.99"}],
    })
    po_id = create.json()["id"]
    resp = await client.get(f"/purchase-orders/{po_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == po_id
    assert len(resp.json()["items"]) == 1


@pytest.mark.asyncio
async def test_get_purchase_order_not_found(client):
    resp = await client.get(f"/purchase-orders/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_confirm_po_publishes_event(client):
    create = await client.post("/purchase-orders/", json={
        "tenant_id": str(TENANT_A),
        "items": [{"product_sku": "SKU-EV", "quantity": 1, "unit_price": "100.00"}],
    })
    po_id = create.json()["id"]

    with patch("app.routers.purchase_orders.publish", new=AsyncMock()) as mock_pub:
        resp = await client.patch(f"/purchase-orders/{po_id}", json={"status": "confirmed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"
        mock_pub.assert_awaited_once()
        args = mock_pub.await_args.args
        assert args[0] == "procurement.po.created"
        assert args[3]["po_id"] == po_id
        assert len(args[3]["items"]) == 1
