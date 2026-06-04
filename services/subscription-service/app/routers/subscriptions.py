import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Subscription, PLAN_MODULES
from app.schemas import SubscriptionCreate, SubscriptionRead, ModuleList

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_subscription(body: SubscriptionCreate, db: AsyncSession = Depends(get_db)):
    sub = Subscription(tenant_id=body.tenant_id, plan=body.plan)
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.get("/{tenant_id}", response_model=SubscriptionRead)
async def get_subscription(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)  # noqa: E712
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub


@router.get("/{tenant_id}/modules", response_model=ModuleList)
async def get_modules(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)  # noqa: E712
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return ModuleList(
        tenant_id=sub.tenant_id,
        plan=sub.plan,
        modules=PLAN_MODULES.get(sub.plan.value, []),
    )
