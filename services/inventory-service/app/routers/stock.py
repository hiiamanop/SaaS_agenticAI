# services/inventory-service/app/routers/stock.py
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_db
from app.models import Stock, StockMovement, MovementType
from app.schemas import StockCreate, StockRead, StockAdjust, StockMovementRead

router = APIRouter(prefix="/stock", tags=["stock"])


@router.post("/", response_model=StockRead, status_code=status.HTTP_201_CREATED)
async def create_stock(body: StockCreate, db: AsyncSession = Depends(get_db)):
    stock = Stock(
        tenant_id=body.tenant_id,
        warehouse_id=body.warehouse_id,
        product_sku=body.product_sku,
        product_name=body.product_name,
        qty_on_hand=body.qty_on_hand,
        qty_reserved=0,
        qty_available=body.qty_on_hand,
        reorder_point=body.reorder_point,
    )
    db.add(stock)
    await db.commit()
    await db.refresh(stock)
    return stock


@router.get("/", response_model=list[StockRead])
async def list_stock(
    tenant_id: Optional[uuid.UUID] = None,
    warehouse_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Stock)
    if tenant_id is not None:
        query = query.where(Stock.tenant_id == tenant_id)
    if warehouse_id is not None:
        query = query.where(Stock.warehouse_id == warehouse_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{stock_id}", response_model=StockRead)
async def get_stock(stock_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Stock).where(Stock.id == stock_id))
    stock = result.scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock


@router.post("/{stock_id}/reserve", response_model=StockRead)
async def reserve_stock(
    stock_id: uuid.UUID, body: StockAdjust, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Stock).where(Stock.id == stock_id))
    stock = result.scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    if stock.qty_available < body.quantity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Insufficient available stock",
        )

    stock.qty_available -= body.quantity
    stock.qty_reserved += body.quantity
    stock.updated_at = datetime.utcnow()
    db.add(stock)

    movement = StockMovement(
        tenant_id=stock.tenant_id,
        stock_id=stock.id,
        movement_type=MovementType.reservation,
        quantity=body.quantity,
        reference=body.reference,
        notes=body.notes,
    )
    db.add(movement)

    await db.commit()
    await db.refresh(stock)
    return stock


@router.post("/{stock_id}/release", response_model=StockRead)
async def release_stock(
    stock_id: uuid.UUID, body: StockAdjust, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Stock).where(Stock.id == stock_id))
    stock = result.scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")

    if stock.qty_reserved < body.quantity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Insufficient reserved stock to release",
        )

    stock.qty_available += body.quantity
    stock.qty_reserved -= body.quantity
    stock.updated_at = datetime.utcnow()
    db.add(stock)

    movement = StockMovement(
        tenant_id=stock.tenant_id,
        stock_id=stock.id,
        movement_type=MovementType.release,
        quantity=body.quantity,
        reference=body.reference,
        notes=body.notes,
    )
    db.add(movement)

    await db.commit()
    await db.refresh(stock)
    return stock


@router.get("/{stock_id}/movements", response_model=list[StockMovementRead])
async def list_movements(stock_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StockMovement).where(StockMovement.stock_id == stock_id)
    )
    return result.scalars().all()
