# services/crm-service/tests/test_opportunities.py
import pytest
import uuid
from unittest.mock import patch, AsyncMock
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_create_opportunity(client):
    resp = await client.post("/opportunities/", json={
        "tenant_id": str(TENANT_A),
        "title": "Big Deal",
        "value": 50000000.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Big Deal"
    assert data["stage"] == "prospect"


@pytest.mark.asyncio
async def test_list_opportunities(client):
    for i in range(2):
        await client.post("/opportunities/", json={
            "tenant_id": str(TENANT_A),
            "title": f"Deal {i}",
            "value": float(i * 1000000),
        })
    resp = await client.get(f"/opportunities/?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_win_opportunity_publishes_event(client):
    create = await client.post("/opportunities/", json={
        "tenant_id": str(TENANT_A),
        "title": "Win This Deal",
        "value": 100000000.0,
    })
    oid = create.json()["id"]

    with patch("app.routers.opportunities.publish", new=AsyncMock()) as mock_publish:
        resp = await client.patch(f"/opportunities/{oid}", json={"stage": "won"})
        assert resp.status_code == 200
        assert resp.json()["stage"] == "won"
        mock_publish.assert_awaited_once()
        assert mock_publish.call_args[0][0] == "crm.opportunity.won"


@pytest.mark.asyncio
async def test_get_nonexistent_opportunity_returns_404(client):
    resp = await client.get(f"/opportunities/{uuid.uuid4()}")
    assert resp.status_code == 404
