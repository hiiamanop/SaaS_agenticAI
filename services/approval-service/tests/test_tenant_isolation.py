import uuid
from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_requests_isolated_by_tenant(client):
    with patch("app.service.publish", new=AsyncMock()):
        await client.post("/approval-requests/", json={
            "tenant_id": str(TENANT_A),
            "request_type": "procurement_po",
            "reference_id": str(uuid.uuid4()),
        })
        await client.post("/approval-requests/", json={
            "tenant_id": str(TENANT_B),
            "request_type": "procurement_po",
            "reference_id": str(uuid.uuid4()),
        })

    resp_a = await client.get(f"/approval-requests/?tenant_id={TENANT_A}")
    resp_b = await client.get(f"/approval-requests/?tenant_id={TENANT_B}")
    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 1
    assert resp_a.json()[0]["tenant_id"] == str(TENANT_A)
