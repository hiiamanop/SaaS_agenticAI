# services/crm-service/app/routers/opportunities.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Opportunity, OpportunityStage
from app.schemas import OpportunityCreate, OpportunityRead, OpportunityUpdate
from app.events import publish

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.post("/", response_model=OpportunityRead, status_code=status.HTTP_201_CREATED)
async def create_opportunity(body: OpportunityCreate, db: AsyncSession = Depends(get_db)):
    opp = Opportunity(**body.model_dump())
    db.add(opp)
    await db.commit()
    await db.refresh(opp)
    return opp


@router.get("/", response_model=list[OpportunityRead])
async def list_opportunities(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Opportunity).where(Opportunity.tenant_id == tenant_id)
    )
    return result.scalars().all()


@router.get("/{opp_id}", response_model=OpportunityRead)
async def get_opportunity(opp_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Opportunity).where(Opportunity.id == opp_id))
    opp = result.scalar_one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp


@router.patch("/{opp_id}", response_model=OpportunityRead)
async def update_opportunity(
    opp_id: uuid.UUID, body: OpportunityUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Opportunity).where(Opportunity.id == opp_id))
    opp = result.scalar_one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    prev_stage = opp.stage
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(opp, field, value)

    await db.commit()
    await db.refresh(opp)

    if prev_stage != OpportunityStage.won and opp.stage == OpportunityStage.won:
        await publish(
            "crm.opportunity.won",
            "crm.opportunity.won",
            str(opp.tenant_id),
            {
                "opportunity_id": str(opp.id),
                "title": opp.title,
                "value": opp.value,
                "contact_id": str(opp.contact_id) if opp.contact_id else None,
            },
        )

    return opp
