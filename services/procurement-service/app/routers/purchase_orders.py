import uuid
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus
from app.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderRead,
    PurchaseOrderUpdate,
)
from app.events import publish

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


def _next_order_number() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"PO-{ts}"


def _serialize_po(po: PurchaseOrder, items: list[PurchaseOrderItem]) -> dict:
    return {
        "id": po.id,
        "tenant_id": po.tenant_id,
        "order_number": po.order_number,
        "requisition_id": po.requisition_id,
        "vendor_id": po.vendor_id,
        "status": po.status,
        "total_amount": po.total_amount,
        "notes": po.notes,
        "created_at": po.created_at,
        "items": [
            {
                "id": item.id,
                "purchase_order_id": item.purchase_order_id,
                "product_sku": item.product_sku,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


async def _load_items(po_id: uuid.UUID, db: AsyncSession) -> list[PurchaseOrderItem]:
    result = await db.execute(
        select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po_id)
    )
    return list(result.scalars().all())


@router.post("/", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(body: PurchaseOrderCreate, db: AsyncSession = Depends(get_db)):
    total = Decimal("0.00")
    for item in body.items:
        total += item.unit_price * item.quantity

    po = PurchaseOrder(
        tenant_id=body.tenant_id,
        order_number=_next_order_number(),
        requisition_id=body.requisition_id,
        vendor_id=body.vendor_id,
        notes=body.notes,
        total_amount=total,
    )
    db.add(po)
    await db.flush()

    items = []
    for item_data in body.items:
        item = PurchaseOrderItem(
            tenant_id=body.tenant_id,
            purchase_order_id=po.id,
            product_sku=item_data.product_sku,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            total_price=item_data.unit_price * item_data.quantity,
        )
        db.add(item)
        items.append(item)

    await db.commit()
    await db.refresh(po)
    return _serialize_po(po, items)


@router.get("/", response_model=list[PurchaseOrderRead])
async def list_purchase_orders(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id)
    )
    orders = result.scalars().all()
    out = []
    for po in orders:
        items = await _load_items(po.id, db)
        out.append(_serialize_po(po, items))
    return out


@router.get("/{po_id}", response_model=PurchaseOrderRead)
async def get_purchase_order(po_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    items = await _load_items(po.id, db)
    return _serialize_po(po, items)


@router.patch("/{po_id}", response_model=PurchaseOrderRead)
async def update_purchase_order(
    po_id: uuid.UUID, body: PurchaseOrderUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    prev_status = po.status
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(po, field, value)
    po.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(po)

    items = await _load_items(po.id, db)

    # Publish event when PO transitions to confirmed
    if prev_status != PurchaseOrderStatus.confirmed and po.status == PurchaseOrderStatus.confirmed:
        await publish(
            "procurement.po.created",
            "procurement.po.created",
            str(po.tenant_id),
            {
                "po_id": str(po.id),
                "order_number": po.order_number,
                "tenant_id": str(po.tenant_id),
                "vendor_id": str(po.vendor_id) if po.vendor_id else None,
                "total_amount": str(po.total_amount),
                "items": [
                    {
                        "po_item_id": str(item.id),
                        "product_sku": item.product_sku,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                        "total_price": str(item.total_price),
                    }
                    for item in items
                ],
            },
        )

    return _serialize_po(po, items)
