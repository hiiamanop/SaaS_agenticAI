import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Invoice, InvoiceLineItem
from app.schemas import InvoiceCreate, InvoiceRead, InvoiceUpdate
from app.service import create_invoice, serialize_invoice

router = APIRouter(prefix="/invoices", tags=["invoices"])


async def _load_items(invoice_id: uuid.UUID, db: AsyncSession) -> list[InvoiceLineItem]:
    result = await db.execute(
        select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice_id)
    )
    return list(result.scalars().all())


@router.post("/", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice_endpoint(body: InvoiceCreate, db: AsyncSession = Depends(get_db)):
    invoice, items = await create_invoice(
        db,
        tenant_id=body.tenant_id,
        items_data=[i.model_dump() for i in body.items],
        vendor_id=body.vendor_id,
        po_id=body.po_id,
    )
    return serialize_invoice(invoice, items)


@router.get("/", response_model=list[InvoiceRead])
async def list_invoices(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.tenant_id == tenant_id))
    invoices = result.scalars().all()
    out = []
    for inv in invoices:
        items = await _load_items(inv.id, db)
        out.append(serialize_invoice(inv, items))
    return out


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(invoice_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    items = await _load_items(inv.id, db)
    return serialize_invoice(inv, items)


@router.patch("/{invoice_id}", response_model=InvoiceRead)
async def update_invoice(
    invoice_id: uuid.UUID, body: InvoiceUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(inv, field, value)
    inv.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(inv)
    items = await _load_items(inv.id, db)
    return serialize_invoice(inv, items)
