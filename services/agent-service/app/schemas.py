import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models import RecommendationStatus


class ReorderRunRequest(BaseModel):
    tenant_id: uuid.UUID
    product_sku: str
    qty_available: int
    reorder_point: int


class RecommendationRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_type: str
    trigger: str
    input_context: dict
    recommendation: dict
    rationale: Optional[str]
    status: RecommendationStatus
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    autonomy_mode: Optional[str] = None
    approval_request_id: Optional[uuid.UUID]
    executed_ref_id: Optional[uuid.UUID]
    created_at: datetime
    model_config = {"from_attributes": True}


class PolicyUpsert(BaseModel):
    auto_execute_enabled: bool = False
    max_auto_qty: int = 0
    max_auto_value: Optional[float] = None
    allowed_urgencies: list[str] = ["normal", "high"]


class PolicyRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_type: str
    auto_execute_enabled: bool
    max_auto_qty: int
    max_auto_value: Optional[float]
    allowed_urgencies: list
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
