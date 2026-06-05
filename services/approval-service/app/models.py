import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import String
from sqlmodel import SQLModel, Field


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"


class StepStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ApprovalRequest(SQLModel, table=True):
    __tablename__ = "approval_requests"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    request_type: str = Field(max_length=50, index=True)  # procurement_po / accounting_invoice
    reference_id: uuid.UUID = Field(index=True)
    status: ApprovalStatus = Field(default=ApprovalStatus.pending, sa_type=String)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalStep(SQLModel, table=True):
    __tablename__ = "approval_steps"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    approval_request_id: uuid.UUID = Field(index=True)
    approver_role: str = Field(max_length=50)  # manager / director / cfo
    order_number: int = Field(default=1)
    status: StepStatus = Field(default=StepStatus.pending, sa_type=String)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalComment(SQLModel, table=True):
    __tablename__ = "approval_comments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    approval_step_id: uuid.UUID = Field(index=True)
    approver_id: str = Field(max_length=200)
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
