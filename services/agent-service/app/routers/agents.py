import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import AgentRecommendation
from app.schemas import ReorderRunRequest, RecommendationRead
from app.service import create_reorder_recommendation

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/reorder/run", response_model=RecommendationRead, status_code=status.HTTP_201_CREATED)
async def run_reorder_agent(body: ReorderRunRequest, db: AsyncSession = Depends(get_db)):
    """Manually trigger the reorder agent (also driven by inventory.stock.low)."""
    rec = await create_reorder_recommendation(
        db,
        tenant_id=body.tenant_id,
        product_sku=body.product_sku,
        qty_available=body.qty_available,
        reorder_point=body.reorder_point,
        trigger="manual",
    )
    return rec


@router.get("/recommendations", response_model=list[RecommendationRead])
async def list_recommendations(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentRecommendation)
        .where(AgentRecommendation.tenant_id == tenant_id)
        .order_by(AgentRecommendation.created_at.desc())
    )
    return result.scalars().all()


@router.get("/recommendations/{rec_id}", response_model=RecommendationRead)
async def get_recommendation(rec_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentRecommendation).where(AgentRecommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec
