import pytest
from tests.conftest import TENANT_A, cloudevent


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_order_created_builds_revenue(client, db_session):
    from app.consumer import handle_event

    ev = cloudevent("sales.order.created", TENANT_A, {
        "order_id": "o1",
        "items": [
            {"product_sku": "A", "quantity": 2, "unit_price": "10.00"},
            {"product_sku": "B", "quantity": 1, "unit_price": "5.50"},
        ],
    })
    await handle_event(db_session, "sales.order.created", ev)

    resp = await client.get(f"/metrics/revenue?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["order_count"] == 1
    assert rows[0]["revenue_total"] == "25.50"


@pytest.mark.asyncio
async def test_two_orders_same_day_aggregate(client, db_session):
    from app.consumer import handle_event

    for _ in range(2):
        await handle_event(db_session, "sales.order.created", cloudevent(
            "sales.order.created", TENANT_A,
            {"items": [{"product_sku": "A", "quantity": 1, "unit_price": "100.00"}]},
        ))

    resp = await client.get(f"/metrics/revenue?tenant_id={TENANT_A}")
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["order_count"] == 2
    assert rows[0]["revenue_total"] == "200.00"


@pytest.mark.asyncio
async def test_procurement_spend_aggregates(client, db_session):
    from app.consumer import handle_event

    await handle_event(db_session, "procurement.po.created", cloudevent(
        "procurement.po.created", TENANT_A, {"po_id": "p1", "total_amount": "300.00"}))
    await handle_event(db_session, "accounting.invoice.created", cloudevent(
        "accounting.invoice.created", TENANT_A, {"invoice_id": "i1", "total_amount": "300.00"}))
    await handle_event(db_session, "accounting.payment.recorded", cloudevent(
        "accounting.payment.recorded", TENANT_A, {"payment_id": "pay1", "amount": "120.00"}))

    resp = await client.get(f"/metrics/procurement?tenant_id={TENANT_A}")
    body = resp.json()
    assert body["po_count"] == 1
    assert body["po_total"] == "300.00"
    assert body["invoice_count"] == 1
    assert body["invoice_total"] == "300.00"
    assert body["paid_total"] == "120.00"


@pytest.mark.asyncio
async def test_inventory_signals(client, db_session):
    from app.consumer import handle_event

    await handle_event(db_session, "inventory.stock.reserved", cloudevent(
        "inventory.stock.reserved", TENANT_A,
        {"reserved_items": [{"product_sku": "SKU-1", "quantity": 7}]}))
    await handle_event(db_session, "inventory.stock.low", cloudevent(
        "inventory.stock.low", TENANT_A,
        {"product_sku": "SKU-1", "qty_available": 3, "reorder_point": 10}))

    resp = await client.get(f"/metrics/inventory?tenant_id={TENANT_A}")
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["product_sku"] == "SKU-1"
    assert rows[0]["qty_reserved_total"] == 7
    assert rows[0]["low_stock_events"] == 1


@pytest.mark.asyncio
async def test_overview_combines_domains(client, db_session):
    from app.consumer import handle_event

    await handle_event(db_session, "sales.order.created", cloudevent(
        "sales.order.created", TENANT_A,
        {"items": [{"product_sku": "A", "quantity": 1, "unit_price": "50.00"}]}))
    await handle_event(db_session, "procurement.po.created", cloudevent(
        "procurement.po.created", TENANT_A, {"total_amount": "80.00"}))
    await handle_event(db_session, "inventory.stock.low", cloudevent(
        "inventory.stock.low", TENANT_A, {"product_sku": "X"}))

    resp = await client.get(f"/metrics/overview?tenant_id={TENANT_A}")
    body = resp.json()
    assert body["order_count"] == 1
    assert body["revenue_total"] == "50.00"
    assert body["po_count"] == 1
    assert body["po_total"] == "80.00"
    assert body["low_stock_skus"] == 1
    assert len(body["revenue_daily"]) == 1


@pytest.mark.asyncio
async def test_malformed_event_ignored(client, db_session):
    from app.consumer import handle_event
    # No tenant_id — should be ignored gracefully
    await handle_event(db_session, "sales.order.created", {"data": {}})
    resp = await client.get(f"/metrics/overview?tenant_id={TENANT_A}")
    assert resp.json()["order_count"] == 0


@pytest.mark.asyncio
async def test_empty_overview_defaults(client):
    resp = await client.get(f"/metrics/overview?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_count"] == 0
    assert body["po_total"] == "0.00"
