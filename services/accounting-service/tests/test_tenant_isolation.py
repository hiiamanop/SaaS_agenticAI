from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_invoices_isolated_by_tenant(client):
    with patch("app.service.publish", new=AsyncMock()):
        await client.post("/invoices/", json={
            "tenant_id": str(TENANT_A),
            "items": [{"product_sku": "SKU-A", "quantity": 1, "amount": "1.00"}],
        })
        await client.post("/invoices/", json={
            "tenant_id": str(TENANT_B),
            "items": [{"product_sku": "SKU-B", "quantity": 1, "amount": "2.00"}],
        })

    resp_a = await client.get(f"/invoices/?tenant_id={TENANT_A}")
    resp_b = await client.get(f"/invoices/?tenant_id={TENANT_B}")
    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 1
    assert resp_a.json()[0]["tenant_id"] == str(TENANT_A)
