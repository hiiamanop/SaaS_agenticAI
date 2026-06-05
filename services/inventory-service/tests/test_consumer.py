# services/inventory-service/tests/test_consumer.py
import uuid
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_consumer_reserves_on_order_created(client, db_session):
    """Consumer should reserve stock when sales.order.created event is received."""
    from app.consumer import handle_order_created_event
    from app.models import Stock, StockMovement
    from sqlmodel import select

    # Create warehouse
    wh_resp = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A),
        "name": "Consumer WH",
        "code": "WH-CONS",
    })
    wh_id = wh_resp.json()["id"]

    # Create stock
    stock_resp = await client.post("/stock/", json={
        "tenant_id": str(TENANT_A),
        "warehouse_id": wh_id,
        "product_sku": "SKU-EVENT",
        "product_name": "Event Product",
        "qty_on_hand": 100,
    })
    stock_id = stock_resp.json()["id"]

    order_id = str(uuid.uuid4())

    # Build CloudEvent payload
    event = {
        "specversion": "1.0",
        "type": "sales.order.created",
        "source": "/services/sales",
        "id": str(uuid.uuid4()),
        "tenantid": str(TENANT_A),
        "data": {
            "order_id": order_id,
            "order_number": "ORD-TEST-001",
            "tenant_id": str(TENANT_A),
            "items": [
                {
                    "product_sku": "SKU-EVENT",
                    "product_name": "Event Product",
                    "quantity": 10,
                    "unit_price": "5.00",
                }
            ],
        },
    }

    # Mock the Kafka producer so publish doesn't fail
    with patch("app.consumer.publish", new=AsyncMock()):
        await handle_order_created_event(db_session, event)

    # Verify stock was reserved
    result = await db_session.execute(
        select(Stock).where(Stock.id == uuid.UUID(stock_id))
    )
    stock = result.scalar_one()
    assert stock.qty_available == 90
    assert stock.qty_reserved == 10

    # Verify StockMovement was created
    mvt_result = await db_session.execute(
        select(StockMovement).where(StockMovement.stock_id == stock.id)
    )
    movements = mvt_result.scalars().all()
    assert len(movements) == 1
    assert movements[0].movement_type == "reservation"
    assert movements[0].quantity == 10
    assert movements[0].reference == order_id


@pytest.mark.asyncio
async def test_consumer_emits_stock_low_at_reorder_point(client, db_session):
    """Reserving down to/below the reorder point publishes inventory.stock.low."""
    from app.consumer import handle_order_created_event

    wh_resp = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A), "name": "Low WH", "code": "WH-LOW",
    })
    wh_id = wh_resp.json()["id"]

    # qty_on_hand 12, reorder_point 10 -> reserving 5 leaves available 7 (<= 10)
    await client.post("/stock/", json={
        "tenant_id": str(TENANT_A),
        "warehouse_id": wh_id,
        "product_sku": "SKU-LOW",
        "product_name": "Low Product",
        "qty_on_hand": 12,
        "reorder_point": 10,
    })

    event = {
        "type": "sales.order.created",
        "tenantid": str(TENANT_A),
        "data": {
            "order_id": str(uuid.uuid4()),
            "tenant_id": str(TENANT_A),
            "items": [{"product_sku": "SKU-LOW", "product_name": "Low Product",
                       "quantity": 5, "unit_price": "1.00"}],
        },
    }

    with patch("app.consumer.publish", new=AsyncMock()) as mock_pub:
        await handle_order_created_event(db_session, event)

    topics = [c.args[0] for c in mock_pub.await_args_list]
    assert "inventory.stock.reserved" in topics
    assert "inventory.stock.low" in topics
    low_call = next(c for c in mock_pub.await_args_list if c.args[0] == "inventory.stock.low")
    assert low_call.args[3]["product_sku"] == "SKU-LOW"
    assert low_call.args[3]["qty_available"] == 7
    assert low_call.args[3]["reorder_point"] == 10
