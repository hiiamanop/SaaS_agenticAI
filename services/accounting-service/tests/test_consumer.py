import uuid
from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_consumer_creates_invoice_on_po_created(client, db_session):
    """Consumer should auto-create a draft invoice when procurement.po.created arrives."""
    from app.consumer import handle_po_created_event
    from app.models import Invoice, InvoiceLineItem
    from sqlmodel import select

    po_id = str(uuid.uuid4())
    vendor_id = str(uuid.uuid4())

    event = {
        "specversion": "1.0",
        "type": "procurement.po.created",
        "source": "/services/procurement",
        "tenantid": str(TENANT_A),
        "data": {
            "po_id": po_id,
            "order_number": "PO-TEST-1",
            "tenant_id": str(TENANT_A),
            "vendor_id": vendor_id,
            "total_amount": "150.00",
            "items": [
                {
                    "po_item_id": str(uuid.uuid4()),
                    "product_sku": "SKU-PO",
                    "quantity": 3,
                    "unit_price": "50.00",
                    "total_price": "150.00",
                }
            ],
        },
    }

    with patch("app.service.publish", new=AsyncMock()):
        await handle_po_created_event(db_session, event)

    result = await db_session.execute(
        select(Invoice).where(Invoice.po_id == uuid.UUID(po_id))
    )
    invoice = result.scalar_one()
    assert invoice.total_amount == 150
    assert invoice.vendor_id == uuid.UUID(vendor_id)
    assert invoice.status.value == "pending"

    items_result = await db_session.execute(
        select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice.id)
    )
    items = items_result.scalars().all()
    assert len(items) == 1
    assert items[0].amount == 150


@pytest.mark.asyncio
async def test_consumer_ignores_malformed_event(client, db_session):
    from app.consumer import handle_po_created_event
    from app.models import Invoice
    from sqlmodel import select

    # Missing po_id and tenant_id — should be ignored gracefully
    await handle_po_created_event(db_session, {"data": {}})

    result = await db_session.execute(select(Invoice))
    assert len(result.scalars().all()) == 0
