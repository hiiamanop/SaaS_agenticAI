# services/marketing-service/app/schemas.py
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models import CampaignStatus


class CampaignCreate(BaseModel):
    tenant_id: uuid.UUID
    name: str
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    pain_points: Optional[str] = None
    value_proposition: Optional[str] = None


class CampaignRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    industry: Optional[str]
    target_audience: Optional[str]
    pain_points: Optional[str]
    value_proposition: Optional[str]
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    pain_points: Optional[str] = None
    value_proposition: Optional[str] = None
    status: Optional[CampaignStatus] = None


class LandingPageFormSubmit(BaseModel):
    """Contact data submitted via campaign landing page form."""
    contact_name: str
    contact_email: str
    contact_phone: Optional[str] = None
    company: Optional[str] = None
