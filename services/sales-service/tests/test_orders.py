# services/sales-service/tests/test_orders.py
import pytest
import uuid
from unittest.mock import patch, AsyncMock
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_order(client):
    resp = await client.post("/orders/", json={
        "tenant_id": str(TENANT_A),
        "contact_id": None,
        "notes": "Test order",
        "items": [
            {
                "product_sku": "SKU-001",
                "product_name": "Widget A",
                "quantity": 2,
                "unit_price": "10.00",
            }
        ],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert "order_number" in data
    assert data["order_number"].startswith("ORD-")
    assert "id" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["product_sku"] == "SKU-001"


@pytest.mark.asyncio
async def test_get_order(client):
    create = await client.post("/orders/", json={
        "tenant_id": str(TENANT_A),
        "items": [
            {
                "product_sku": "SKU-002",
                "product_name": "Widget B",
                "quantity": 1,
                "unit_price": "25.00",
            }
        ],
    })
    order_id = create.json()["id"]
    resp = await client.get(f"/orders/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id
    assert len(resp.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_orders_by_tenant(client):
    for i in range(3):
        await client.post("/orders/", json={
            "tenant_id": str(TENANT_A),
            "items": [
                {
                    "product_sku": f"SKU-{i:03d}",
                    "product_name": f"Product {i}",
                    "quantity": 1,
                    "unit_price": "5.00",
                }
            ],
        })
    resp = await client.get(f"/orders/?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_update_order_status_publishes_event(client):
    create = await client.post("/orders/", json={
        "tenant_id": str(TENANT_A),
        "items": [
            {
                "product_sku": "SKU-003",
                "product_name": "Widget C",
                "quantity": 5,
                "unit_price": "15.00",
            }
        ],
    })
    order_id = create.json()["id"]

    with patch("app.routers.orders.publish", new=AsyncMock()) as mock_publish:
        resp = await client.patch(f"/orders/{order_id}", json={"status": "confirmed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"
        mock_publish.assert_awaited_once()
        call_args = mock_publish.call_args[0]
        assert call_args[0] == "sales.order.created"
        assert call_args[1] == "sales.order.created"


@pytest.mark.asyncio
async def test_orders_isolated_by_tenant(client):
    # Create order for TENANT_A
    await client.post("/orders/", json={
        "tenant_id": str(TENANT_A),
        "items": [
            {
                "product_sku": "SKU-A",
                "product_name": "Product A",
                "quantity": 1,
                "unit_price": "10.00",
            }
        ],
    })
    # Create order for TENANT_B
    await client.post("/orders/", json={
        "tenant_id": str(TENANT_B),
        "items": [
            {
                "product_sku": "SKU-B",
                "product_name": "Product B",
                "quantity": 1,
                "unit_price": "10.00",
            }
        ],
    })
    # TENANT_A sees only their order
    resp_a = await client.get(f"/orders/?tenant_id={TENANT_A}")
    assert len(resp_a.json()) == 1
    assert resp_a.json()[0]["tenant_id"] == str(TENANT_A)
