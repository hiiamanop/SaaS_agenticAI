# services/sales-service/app/routers/orders.py
import uuid
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Order, OrderItem, OrderStatus
from app.schemas import OrderCreate, OrderRead, OrderUpdate, OrderItemRead
from app.events import publish

router = APIRouter(prefix="/orders", tags=["orders"])


def _next_order_number() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"ORD-{ts}"


async def _get_order_with_items(order_id: uuid.UUID, db: AsyncSession) -> dict | None:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        return None

    items_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    items = items_result.scalars().all()

    return {
        "id": order.id,
        "tenant_id": order.tenant_id,
        "order_number": order.order_number,
        "quotation_id": order.quotation_id,
        "contact_id": order.contact_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "notes": order.notes,
        "created_at": order.created_at,
        "items": [
            {
                "id": item.id,
                "order_id": item.order_id,
                "product_sku": item.product_sku,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(body: OrderCreate, db: AsyncSession = Depends(get_db)):
    # Calculate total from items
    total = Decimal("0.00")
    for item in body.items:
        total += item.unit_price * item.quantity

    order = Order(
        tenant_id=body.tenant_id,
        order_number=_next_order_number(),
        contact_id=body.contact_id,
        quotation_id=body.quotation_id,
        notes=body.notes,
        total_amount=total,
    )
    db.add(order)
    await db.flush()  # get order.id

    order_items = []
    for item_data in body.items:
        item = OrderItem(
            tenant_id=body.tenant_id,
            order_id=order.id,
            product_sku=item_data.product_sku,
            product_name=item_data.product_name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            total_price=item_data.unit_price * item_data.quantity,
        )
        db.add(item)
        order_items.append(item)

    await db.commit()
    await db.refresh(order)

    return {
        "id": order.id,
        "tenant_id": order.tenant_id,
        "order_number": order.order_number,
        "quotation_id": order.quotation_id,
        "contact_id": order.contact_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "notes": order.notes,
        "created_at": order.created_at,
        "items": [
            {
                "id": item.id,
                "order_id": item.order_id,
                "product_sku": item.product_sku,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
                "created_at": item.created_at,
            }
            for item in order_items
        ],
    }


@router.get("/", response_model=list[OrderRead])
async def list_orders(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.tenant_id == tenant_id))
    orders = result.scalars().all()

    out = []
    for order in orders:
        items_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = items_result.scalars().all()
        out.append({
            "id": order.id,
            "tenant_id": order.tenant_id,
            "order_number": order.order_number,
            "quotation_id": order.quotation_id,
            "contact_id": order.contact_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "notes": order.notes,
            "created_at": order.created_at,
            "items": [
                {
                    "id": item.id,
                    "order_id": item.order_id,
                    "product_sku": item.product_sku,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "created_at": item.created_at,
                }
                for item in items
            ],
        })
    return out


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    data = await _get_order_with_items(order_id, db)
    if data is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return data


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: uuid.UUID, body: OrderUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    prev_status = order.status
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(order, field, value)

    order.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(order)

    # Publish event when status transitions to confirmed
    if prev_status != OrderStatus.confirmed and order.status == OrderStatus.confirmed:
        items_result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        items = items_result.scalars().all()

        await publish(
            "sales.order.created",
            "sales.order.created",
            str(order.tenant_id),
            {
                "order_id": str(order.id),
                "order_number": order.order_number,
                "tenant_id": str(order.tenant_id),
                "items": [
                    {
                        "product_sku": item.product_sku,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                    }
                    for item in items
                ],
            },
        )

    data = await _get_order_with_items(order_id, db)
    return data
