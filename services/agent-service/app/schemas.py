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
    approval_request_id: Optional[uuid.UUID]
    executed_ref_id: Optional[uuid.UUID]
    created_at: datetime
    model_config = {"from_attributes": True}
