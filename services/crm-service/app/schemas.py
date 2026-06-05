# services/crm-service/app/schemas.py
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models import LeadStatus, OpportunityStage


class LeadCreate(BaseModel):
    tenant_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None


class LeadRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    company: Optional[str]
    status: LeadStatus
    source: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[LeadStatus] = None
    source: Optional[str] = None


class ContactCreate(BaseModel):
    tenant_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None


class ContactRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    company: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None


class OpportunityCreate(BaseModel):
    tenant_id: uuid.UUID
    title: str
    value: float = 0.0
    contact_id: Optional[uuid.UUID] = None


class OpportunityRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    contact_id: Optional[uuid.UUID]
    title: str
    value: float
    stage: OpportunityStage
    created_at: datetime
    model_config = {"from_attributes": True}


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    value: Optional[float] = None
    stage: Optional[OpportunityStage] = None
    contact_id: Optional[uuid.UUID] = None
