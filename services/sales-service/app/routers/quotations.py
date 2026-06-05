# services/sales-service/app/routers/quotations.py
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Quotation, QuotationStatus, Order
from app.schemas import QuotationCreate, QuotationRead, QuotationUpdate, OrderRead

router = APIRouter(prefix="/quotations", tags=["quotations"])


def _next_quotation_number() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"QUO-{ts}"


@router.post("/", response_model=QuotationRead, status_code=status.HTTP_201_CREATED)
async def create_quotation(body: QuotationCreate, db: AsyncSession = Depends(get_db)):
    quotation = Quotation(
        **body.model_dump(),
        quotation_number=_next_quotation_number(),
    )
    db.add(quotation)
    await db.commit()
    await db.refresh(quotation)
    return quotation


@router.get("/", response_model=list[QuotationRead])
async def list_quotations(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Quotation).where(Quotation.tenant_id == tenant_id))
    return result.scalars().all()


@router.get("/{quotation_id}", response_model=QuotationRead)
async def get_quotation(quotation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Quotation).where(Quotation.id == quotation_id))
    quotation = result.scalar_one_or_none()
    if quotation is None:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return quotation


@router.patch("/{quotation_id}", response_model=QuotationRead)
async def update_quotation(
    quotation_id: uuid.UUID, body: QuotationUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Quotation).where(Quotation.id == quotation_id))
    quotation = result.scalar_one_or_none()
    if quotation is None:
        raise HTTPException(status_code=404, detail="Quotation not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(quotation, field, value)

    quotation.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(quotation)
    return quotation


@router.post("/{quotation_id}/convert", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def convert_quotation_to_order(
    quotation_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Quotation).where(Quotation.id == quotation_id))
    quotation = result.scalar_one_or_none()
    if quotation is None:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status != QuotationStatus.accepted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only accepted quotations can be converted to orders",
        )

    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    order = Order(
        tenant_id=quotation.tenant_id,
        order_number=f"ORD-{ts}",
        quotation_id=quotation.id,
        contact_id=quotation.contact_id,
        total_amount=quotation.total_amount,
        notes=quotation.notes,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Return with empty items list
    order_dict = {
        "id": order.id,
        "tenant_id": order.tenant_id,
        "order_number": order.order_number,
        "quotation_id": order.quotation_id,
        "contact_id": order.contact_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "notes": order.notes,
        "created_at": order.created_at,
        "items": [],
    }
    return order_dict
