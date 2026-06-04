import uuid
from datetime import datetime
from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str
    slug: str
    email: str


class TenantRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    email: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    is_active: bool | None = None
