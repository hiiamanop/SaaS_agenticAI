from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_recommendations_isolated_by_tenant(client):
    with patch("app.service.publish", new=AsyncMock()):
        await client.post("/agents/reorder/run", json={
            "tenant_id": str(TENANT_A), "product_sku": "A",
            "qty_available": 1, "reorder_point": 5,
        })
        await client.post("/agents/reorder/run", json={
            "tenant_id": str(TENANT_B), "product_sku": "B",
            "qty_available": 1, "reorder_point": 5,
        })

    resp_a = await client.get(f"/agents/recommendations?tenant_id={TENANT_A}")
    resp_b = await client.get(f"/agents/recommendations?tenant_id={TENANT_B}")
    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 1
    assert resp_a.json()[0]["tenant_id"] == str(TENANT_A)
