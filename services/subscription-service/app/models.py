import uuid
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field

PLAN_MODULES: dict[str, list[str]] = {
    "starter":    ["crm", "sales"],
    "business":   ["crm", "sales", "inventory", "procurement"],
    "enterprise": ["crm", "sales", "inventory", "procurement",
                   "accounting", "ai_platform", "knowledge_platform"],
}


class PlanName(str, Enum):
    starter = "starter"
    business = "business"
    enterprise = "enterprise"


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    plan: PlanName = Field(default=PlanName.starter)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
