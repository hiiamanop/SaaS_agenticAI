import uuid
from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_stock_low_triggers_recommendation(client, db_session):
    from app.consumer import handle_event
    from app.models import AgentRecommendation
    from sqlmodel import select

    event = {
        "type": "inventory.stock.low",
        "tenantid": str(TENANT_A),
        "data": {
            "tenant_id": str(TENANT_A),
            "product_sku": "SKU-LOW",
            "qty_available": 1,
            "reorder_point": 10,
        },
    }
    with patch("app.service.publish", new=AsyncMock()):
        await handle_event(db_session, "inventory.stock.low", event)

    result = await db_session.execute(
        select(AgentRecommendation).where(AgentRecommendation.tenant_id == TENANT_A)
    )
    rec = result.scalar_one()
    assert rec.trigger == "event"
    assert rec.recommendation["recommended_qty"] == 19  # 20 - 1


@pytest.mark.asyncio
async def test_approval_approved_executes_recommendation(client, db_session):
    from app.consumer import handle_event
    from app.models import AgentRecommendation, RecommendationStatus
    from sqlmodel import select

    # First create a proposed recommendation
    with patch("app.service.publish", new=AsyncMock()):
        created = await client.post("/agents/reorder/run", json={
            "tenant_id": str(TENANT_A), "product_sku": "SKU-EXEC",
            "qty_available": 0, "reorder_point": 6,
        })
    rec_id = created.json()["id"]
    fake_requisition_id = uuid.uuid4()

    approved_event = {
        "type": "approval.request.approved",
        "tenantid": str(TENANT_A),
        "data": {
            "tenant_id": str(TENANT_A),
            "request_type": "agent_action",
            "reference_id": rec_id,
            "status": "approved",
        },
    }
    with patch("app.service.publish", new=AsyncMock()) as mock_pub, \
            patch("app.service.create_requisition", new=AsyncMock(return_value=fake_requisition_id)) as mock_req:
        await handle_event(db_session, "approval.request.approved", approved_event)
        mock_req.assert_awaited_once()
        # agent.action.executed published
        assert any(c.args[0] == "agent.action.executed" for c in mock_pub.await_args_list)

    result = await db_session.execute(
        select(AgentRecommendation).where(AgentRecommendation.id == uuid.UUID(rec_id))
    )
    rec = result.scalar_one()
    assert rec.status == RecommendationStatus.executed
    assert rec.executed_ref_id == fake_requisition_id


@pytest.mark.asyncio
async def test_approval_approved_ignores_non_agent_requests(client, db_session):
    from app.consumer import handle_event
    from app.models import AgentRecommendation
    from sqlmodel import select

    event = {
        "type": "approval.request.approved",
        "tenantid": str(TENANT_A),
        "data": {
            "tenant_id": str(TENANT_A),
            "request_type": "procurement_po",  # not an agent action
            "reference_id": str(uuid.uuid4()),
        },
    }
    # Should be a no-op (no exception, no execution)
    await handle_event(db_session, "approval.request.approved", event)
    result = await db_session.execute(select(AgentRecommendation))
    assert len(result.scalars().all()) == 0


@pytest.mark.asyncio
async def test_stock_low_malformed_ignored(client, db_session):
    from app.consumer import handle_event
    from app.models import AgentRecommendation
    from sqlmodel import select

    await handle_event(db_session, "inventory.stock.low", {"data": {}})
    result = await db_session.execute(select(AgentRecommendation))
    assert len(result.scalars().all()) == 0
