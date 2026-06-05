import pytest
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_requisitions_isolated_by_tenant(client):
    await client.post("/requisitions/", json={
        "tenant_id": str(TENANT_A), "product_sku": "SKU-A1", "quantity": 1,
    })
    await client.post("/requisitions/", json={
        "tenant_id": str(TENANT_B), "product_sku": "SKU-B1", "quantity": 1,
    })

    resp_a = await client.get(f"/requisitions/?tenant_id={TENANT_A}")
    resp_b = await client.get(f"/requisitions/?tenant_id={TENANT_B}")

    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 1
    assert resp_a.json()[0]["tenant_id"] == str(TENANT_A)


@pytest.mark.asyncio
async def test_purchase_orders_cross_tenant_not_visible(client):
    create_a = await client.post("/purchase-orders/", json={
        "tenant_id": str(TENANT_A),
        "items": [{"product_sku": "SKU-PA", "quantity": 1, "unit_price": "1.00"}],
    })
    po_a_id = create_a.json()["id"]

    resp_b = await client.get(f"/purchase-orders/?tenant_id={TENANT_B}")
    ids_b = [p["id"] for p in resp_b.json()]
    assert po_a_id not in ids_b
