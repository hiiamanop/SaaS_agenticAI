import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class LeadStatus(str, Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    lost = "lost"


class Lead(SQLModel, table=True):
    __tablename__ = "leads"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    status: LeadStatus = Field(default=LeadStatus.new)
    source: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Contact(SQLModel, table=True):
    __tablename__ = "contacts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OpportunityStage(str, Enum):
    prospect = "prospect"
    proposal = "proposal"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"


class Opportunity(SQLModel, table=True):
    __tablename__ = "opportunities"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    contact_id: Optional[uuid.UUID] = Field(default=None, index=True)
    title: str = Field(max_length=200)
    value: float = Field(default=0.0)
    stage: OpportunityStage = Field(default=OpportunityStage.prospect)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
