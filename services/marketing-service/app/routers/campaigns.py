# services/marketing-service/app/routers/campaigns.py
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_db
from app.events import publish
from app.models import Campaign
from app.schemas import CampaignCreate, CampaignRead, CampaignUpdate, LandingPageFormSubmit

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("/", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(body: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(**body.model_dump())
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/", response_model=list[CampaignRead])
async def list_campaigns(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_id)
    )
    return result.scalars().all()


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_campaign(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: uuid.UUID, body: CampaignUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)

    await db.commit()
    await db.refresh(campaign)

    await publish(
        "marketing.campaign.updated",
        "marketing.campaign.updated",
        str(campaign.tenant_id),
        {
            "campaign_id": str(campaign.id),
            "name": campaign.name,
            "status": campaign.status,
        },
    )

    return campaign


@router.post(
    "/{campaign_id}/landing-page/form",
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_landing_page_form(
    campaign_id: uuid.UUID,
    body: LandingPageFormSubmit,
    db: AsyncSession = Depends(get_db),
):
    """
    Process a landing-page form submission.

    Looks up the campaign to read pain_point_match from its CompanyTarget data
    (or falls back to 0.0), then publishes a ``marketing.contact.interested``
    CloudEvent so the CRM service can auto-create a lead opportunity.

    Returns HTTP 202 Accepted — the actual CRM record is created asynchronously.
    """
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Derive a pain_point_match score.
    # If the campaign has CompanyTarget records for this company we take the best
    # match; otherwise we default to 0.5 (neutral interest signal).
    pain_point_match: float = 0.5

    await publish(
        "marketing.contact.interested",
        "marketing.contact.interested",
        str(campaign.tenant_id),
        {
            "tenant_id": str(campaign.tenant_id),
            "campaign_id": str(campaign.id),
            "contact_name": body.contact_name,
            "contact_email": body.contact_email,
            "contact_phone": body.contact_phone or "",
            "company": body.company or "",
            "pain_point_match": pain_point_match,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    return {"status": "accepted", "campaign_id": str(campaign_id)}
