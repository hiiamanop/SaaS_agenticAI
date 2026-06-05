import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Requisition
from app.schemas import RequisitionCreate, RequisitionRead, RequisitionUpdate

router = APIRouter(prefix="/requisitions", tags=["requisitions"])


@router.post("/", response_model=RequisitionRead, status_code=status.HTTP_201_CREATED)
async def create_requisition(body: RequisitionCreate, db: AsyncSession = Depends(get_db)):
    req = Requisition(
        tenant_id=body.tenant_id,
        product_sku=body.product_sku,
        quantity=body.quantity,
        reason=body.reason,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/", response_model=list[RequisitionRead])
async def list_requisitions(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Requisition).where(Requisition.tenant_id == tenant_id))
    return result.scalars().all()


@router.get("/{requisition_id}", response_model=RequisitionRead)
async def get_requisition(requisition_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Requisition).where(Requisition.id == requisition_id))
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Requisition not found")
    return req


@router.patch("/{requisition_id}", response_model=RequisitionRead)
async def update_requisition(
    requisition_id: uuid.UUID, body: RequisitionUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Requisition).where(Requisition.id == requisition_id))
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Requisition not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(req, field, value)
    req.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(req)
    return req
