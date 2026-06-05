import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import RevenueDaily, ProcurementSpend, InventorySignal
from app.schemas import (
    RevenueDailyRead,
    ProcurementSpendRead,
    InventorySignalRead,
    OverviewRead,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/revenue", response_model=list[RevenueDailyRead])
async def revenue(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RevenueDaily)
        .where(RevenueDaily.tenant_id == tenant_id)
        .order_by(RevenueDaily.day)
    )
    return result.scalars().all()


@router.get("/procurement", response_model=ProcurementSpendRead)
async def procurement(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProcurementSpend).where(ProcurementSpend.tenant_id == tenant_id)
    )
    spend = result.scalar_one_or_none()
    if spend is None:
        return ProcurementSpendRead(
            tenant_id=tenant_id, po_count=0, po_total=Decimal("0.00"),
            invoice_count=0, invoice_total=Decimal("0.00"), paid_total=Decimal("0.00"),
        )
    return spend


@router.get("/inventory", response_model=list[InventorySignalRead])
async def inventory(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(InventorySignal).where(InventorySignal.tenant_id == tenant_id)
    )
    return result.scalars().all()


@router.get("/overview", response_model=OverviewRead)
async def overview(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rev_result = await db.execute(
        select(RevenueDaily)
        .where(RevenueDaily.tenant_id == tenant_id)
        .order_by(RevenueDaily.day)
    )
    rev_rows = rev_result.scalars().all()

    spend_result = await db.execute(
        select(ProcurementSpend).where(ProcurementSpend.tenant_id == tenant_id)
    )
    spend = spend_result.scalar_one_or_none()

    sig_result = await db.execute(
        select(InventorySignal).where(
            InventorySignal.tenant_id == tenant_id,
            InventorySignal.low_stock_events > 0,
        )
    )
    low_stock_skus = len(sig_result.scalars().all())

    return OverviewRead(
        tenant_id=tenant_id,
        order_count=sum(r.order_count for r in rev_rows),
        revenue_total=sum((r.revenue_total for r in rev_rows), Decimal("0.00")),
        po_count=spend.po_count if spend else 0,
        po_total=spend.po_total if spend else Decimal("0.00"),
        invoice_total=spend.invoice_total if spend else Decimal("0.00"),
        paid_total=spend.paid_total if spend else Decimal("0.00"),
        low_stock_skus=low_stock_skus,
        revenue_daily=rev_rows,
    )
