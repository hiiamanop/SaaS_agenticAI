import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"
    __table_args__ = (UniqueConstraint("slug"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(default_factory=uuid.uuid4, index=True)
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=50)
    email: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TenantMembership(SQLModel, table=True):
    __tablename__ = "tenant_memberships"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    user_id: str = Field(index=True)
    role: str = Field(default="staff")
    created_at: datetime = Field(default_factory=datetime.utcnow)
