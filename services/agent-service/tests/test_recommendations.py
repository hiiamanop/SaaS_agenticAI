import uuid
from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_run_reorder_agent_creates_recommendation(client):
    with patch("app.service.publish", new=AsyncMock()) as mock_pub:
        resp = await client.post("/agents/reorder/run", json={
            "tenant_id": str(TENANT_A),
            "product_sku": "SKU-1",
            "qty_available": 2,
            "reorder_point": 10,
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "proposed"
        assert body["agent_type"] == "procurement_reorder"
        assert body["trigger"] == "manual"
        assert body["recommendation"]["recommended_qty"] == 18
        mock_pub.assert_awaited_once()
        assert mock_pub.await_args.args[0] == "agent.action.recommended"


@pytest.mark.asyncio
async def test_list_and_get_recommendation(client):
    with patch("app.service.publish", new=AsyncMock()):
        created = await client.post("/agents/reorder/run", json={
            "tenant_id": str(TENANT_A), "product_sku": "SKU-X",
            "qty_available": 0, "reorder_point": 5,
        })
    rec_id = created.json()["id"]

    lst = await client.get(f"/agents/recommendations?tenant_id={TENANT_A}")
    assert len(lst.json()) == 1

    got = await client.get(f"/agents/recommendations/{rec_id}")
    assert got.status_code == 200
    assert got.json()["id"] == rec_id


@pytest.mark.asyncio
async def test_get_recommendation_not_found(client):
    resp = await client.get(f"/agents/recommendations/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_action_log_written(client, db_session):
    from app.models import AgentActionLog
    from sqlmodel import select

    with patch("app.service.publish", new=AsyncMock()):
        await client.post("/agents/reorder/run", json={
            "tenant_id": str(TENANT_A), "product_sku": "SKU-LOG",
            "qty_available": 1, "reorder_point": 4,
        })

    result = await db_session.execute(select(AgentActionLog))
    logs = result.scalars().all()
    assert any(log.action == "recommended" for log in logs)
