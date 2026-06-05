import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models import ApprovalStatus, StepStatus


class ApprovalRequestCreate(BaseModel):
    tenant_id: uuid.UUID
    request_type: str
    reference_id: uuid.UUID


class ApprovalStepRead(BaseModel):
    id: uuid.UUID
    approval_request_id: uuid.UUID
    approver_role: str
    order_number: int
    status: StepStatus
    created_at: datetime
    model_config = {"from_attributes": True}


class ApprovalRequestRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    request_type: str
    reference_id: uuid.UUID
    status: ApprovalStatus
    created_at: datetime
    steps: List[ApprovalStepRead] = []
    model_config = {"from_attributes": True}


class StepDecision(BaseModel):
    approver_id: str
    message: Optional[str] = None
