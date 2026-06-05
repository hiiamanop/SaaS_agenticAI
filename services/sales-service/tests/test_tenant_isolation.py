# services/sales-service/tests/test_tenant_isolation.py
import pytest
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_quotations_isolated_by_tenant(client):
    # Create quotations for each tenant
    await client.post("/quotations/", json={
        "tenant_id": str(TENANT_A),
        "total_amount": "100.00",
    })
    await client.post("/quotations/", json={
        "tenant_id": str(TENANT_A),
        "total_amount": "200.00",
    })
    await client.post("/quotations/", json={
        "tenant_id": str(TENANT_B),
        "total_amount": "300.00",
    })

    resp_a = await client.get(f"/quotations/?tenant_id={TENANT_A}")
    resp_b = await client.get(f"/quotations/?tenant_id={TENANT_B}")

    assert resp_a.status_code == 200
    assert len(resp_a.json()) == 2
    for q in resp_a.json():
        assert q["tenant_id"] == str(TENANT_A)

    assert resp_b.status_code == 200
    assert len(resp_b.json()) == 1
    assert resp_b.json()[0]["tenant_id"] == str(TENANT_B)


@pytest.mark.asyncio
async def test_orders_cross_tenant_not_visible(client):
    # TENANT_A order
    create_a = await client.post("/orders/", json={
        "tenant_id": str(TENANT_A),
        "items": [
            {
                "product_sku": "SKU-TENANT-A",
                "product_name": "A Product",
                "quantity": 1,
                "unit_price": "50.00",
            }
        ],
    })
    order_a_id = create_a.json()["id"]

    # TENANT_B lists orders - should NOT see TENANT_A's order
    resp_b = await client.get(f"/orders/?tenant_id={TENANT_B}")
    assert resp_b.status_code == 200
    ids_b = [o["id"] for o in resp_b.json()]
    assert order_a_id not in ids_b
