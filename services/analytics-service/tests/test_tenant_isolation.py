import pytest
from tests.conftest import TENANT_A, TENANT_B, cloudevent


@pytest.mark.asyncio
async def test_revenue_isolated_by_tenant(client, db_session):
    from app.consumer import handle_event

    await handle_event(db_session, "sales.order.created", cloudevent(
        "sales.order.created", TENANT_A,
        {"items": [{"product_sku": "A", "quantity": 1, "unit_price": "10.00"}]}))
    await handle_event(db_session, "sales.order.created", cloudevent(
        "sales.order.created", TENANT_B,
        {"items": [{"product_sku": "A", "quantity": 1, "unit_price": "99.00"}]}))

    resp_a = await client.get(f"/metrics/revenue?tenant_id={TENANT_A}")
    resp_b = await client.get(f"/metrics/revenue?tenant_id={TENANT_B}")
    assert resp_a.json()[0]["revenue_total"] == "10.00"
    assert resp_b.json()[0]["revenue_total"] == "99.00"


@pytest.mark.asyncio
async def test_procurement_isolated_by_tenant(client, db_session):
    from app.consumer import handle_event

    await handle_event(db_session, "procurement.po.created", cloudevent(
        "procurement.po.created", TENANT_A, {"total_amount": "10.00"}))

    resp_b = await client.get(f"/metrics/procurement?tenant_id={TENANT_B}")
    assert resp_b.json()["po_count"] == 0
