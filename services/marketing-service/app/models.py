import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON, Column


class CampaignStatus(str, Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    name: str = Field(max_length=200)
    industry: Optional[str] = Field(default=None, max_length=100)
    target_audience: Optional[str] = None
    pain_points: Optional[str] = None
    value_proposition: Optional[str] = None
    status: CampaignStatus = Field(default=CampaignStatus.draft)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CompanyTargetStatus(str, Enum):
    discovered = "discovered"
    validated = "validated"
    contacted = "contacted"
    qualified = "qualified"
    disqualified = "disqualified"


class CompanyTarget(SQLModel, table=True):
    __tablename__ = "company_targets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    campaign_id: uuid.UUID = Field(index=True)
    tenant_id: uuid.UUID = Field(index=True)
    company_name: str = Field(max_length=200)
    industry: Optional[str] = Field(default=None, max_length=100)
    website: Optional[str] = None
    decision_makers: Optional[str] = None
    pain_point_match: Optional[float] = Field(default=None)
    contact_validation: Optional[str] = None
    status: CompanyTargetStatus = Field(default=CompanyTargetStatus.discovered)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContentAssetType(str, Enum):
    blog_article = "blog_article"
    linkedin_post = "linkedin_post"
    ad_creative = "ad_creative"
    landing_page = "landing_page"
    email_template = "email_template"
    whatsapp_message = "whatsapp_message"


class PublishStatus(str, Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    published = "published"
    archived = "archived"


class ContentAsset(SQLModel, table=True):
    __tablename__ = "content_assets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    campaign_id: uuid.UUID = Field(index=True)
    tenant_id: uuid.UUID = Field(index=True)
    asset_type: ContentAssetType
    title: str = Field(max_length=300)
    content: Optional[str] = None
    asset_metadata: Optional[dict] = Field(default=None, sa_column=Column("asset_metadata", JSON))
    publish_status: PublishStatus = Field(default=PublishStatus.draft)
    engagement_metrics: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AdPlatform(str, Enum):
    meta = "meta"
    google = "google"
    linkedin = "linkedin"
    tiktok = "tiktok"


class AdCampaignStatus(str, Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    active = "active"
    paused = "paused"
    completed = "completed"


class AdCampaign(SQLModel, table=True):
    __tablename__ = "ad_campaigns"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    campaign_id: uuid.UUID = Field(index=True)
    tenant_id: uuid.UUID = Field(index=True)
    platform: AdPlatform
    creative_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    targeting_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    daily_budget: Optional[float] = Field(default=None)
    metrics: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    status: AdCampaignStatus = Field(default=AdCampaignStatus.draft)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
