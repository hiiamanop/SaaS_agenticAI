import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models import PlanName, PLAN_MODULES


class SubscriptionCreate(BaseModel):
    tenant_id: uuid.UUID
    plan: PlanName


class SubscriptionRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    plan: PlanName
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class ModuleList(BaseModel):
    tenant_id: uuid.UUID
    plan: PlanName
    modules: list[str]
