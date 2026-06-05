"""Shared invoice/payment domain logic used by both routers and the Kafka consumer."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Invoice, InvoiceLineItem, InvoiceStatus
from app.events import publish


def next_invoice_number() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"INV-{ts}"


def serialize_invoice(inv: Invoice, items: list[InvoiceLineItem]) -> dict:
    return {
        "id": inv.id,
        "tenant_id": inv.tenant_id,
        "invoice_number": inv.invoice_number,
        "po_id": inv.po_id,
        "vendor_id": inv.vendor_id,
        "total_amount": inv.total_amount,
        "status": inv.status,
        "created_at": inv.created_at,
        "items": [
            {
                "id": it.id,
                "invoice_id": it.invoice_id,
                "po_item_id": it.po_item_id,
                "product_sku": it.product_sku,
                "quantity": it.quantity,
                "amount": it.amount,
                "created_at": it.created_at,
            }
            for it in items
        ],
    }


async def create_invoice(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    items_data: list[dict],
    vendor_id: uuid.UUID | None = None,
    po_id: uuid.UUID | None = None,
    publish_event: bool = True,
) -> tuple[Invoice, list[InvoiceLineItem]]:
    """Create an invoice with line items, commit, and optionally publish
    accounting.invoice.created. Returns (invoice, line_items)."""
    total = Decimal("0.00")
    for item in items_data:
        total += Decimal(str(item.get("amount", "0.00")))

    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number=next_invoice_number(),
        vendor_id=vendor_id,
        po_id=po_id,
        total_amount=total,
        status=InvoiceStatus.pending,
    )
    db.add(invoice)
    await db.flush()

    line_items: list[InvoiceLineItem] = []
    for item in items_data:
        li = InvoiceLineItem(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            po_item_id=item.get("po_item_id"),
            product_sku=item.get("product_sku"),
            quantity=int(item.get("quantity", 1)),
            amount=Decimal(str(item.get("amount", "0.00"))),
        )
        db.add(li)
        line_items.append(li)

    await db.commit()
    await db.refresh(invoice)

    if publish_event:
        await publish(
            "accounting.invoice.created",
            "accounting.invoice.created",
            str(tenant_id),
            {
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "tenant_id": str(tenant_id),
                "po_id": str(po_id) if po_id else None,
                "vendor_id": str(vendor_id) if vendor_id else None,
                "total_amount": str(invoice.total_amount),
            },
        )

    return invoice, line_items
