import uuid
from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_consumer_opens_workflow_on_po_created(client, db_session):
    from app.consumer import handle_event
    from app.models import ApprovalRequest, ApprovalStep
    from sqlmodel import select

    po_id = str(uuid.uuid4())
    event = {
        "type": "procurement.po.created",
        "tenantid": str(TENANT_A),
        "data": {"po_id": po_id, "tenant_id": str(TENANT_A)},
    }

    with patch("app.service.publish", new=AsyncMock()):
        await handle_event(db_session, "procurement.po.created", event)

    result = await db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.reference_id == uuid.UUID(po_id))
    )
    req = result.scalar_one()
    assert req.request_type == "procurement_po"
    assert req.status == "pending"

    steps = await db_session.execute(
        select(ApprovalStep).where(ApprovalStep.approval_request_id == req.id)
    )
    assert len(steps.scalars().all()) == 3


@pytest.mark.asyncio
async def test_consumer_opens_workflow_on_invoice_created(client, db_session):
    from app.consumer import handle_event
    from app.models import ApprovalRequest
    from sqlmodel import select

    invoice_id = str(uuid.uuid4())
    event = {
        "type": "accounting.invoice.created",
        "tenantid": str(TENANT_A),
        "data": {"invoice_id": invoice_id, "tenant_id": str(TENANT_A)},
    }

    with patch("app.service.publish", new=AsyncMock()):
        await handle_event(db_session, "accounting.invoice.created", event)

    result = await db_session.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.reference_id == uuid.UUID(invoice_id)
        )
    )
    req = result.scalar_one()
    assert req.request_type == "accounting_invoice"


@pytest.mark.asyncio
async def test_consumer_ignores_malformed_event(client, db_session):
    from app.consumer import handle_event
    from app.models import ApprovalRequest
    from sqlmodel import select

    await handle_event(db_session, "procurement.po.created", {"data": {}})

    result = await db_session.execute(select(ApprovalRequest))
    assert len(result.scalars().all()) == 0
