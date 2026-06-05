import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import String
from sqlmodel import SQLModel, Field, Column, JSON


class RecommendationStatus(str, Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    executed = "executed"
    failed = "failed"


class AgentRecommendation(SQLModel, table=True):
    __tablename__ = "agent_recommendations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    agent_type: str = Field(max_length=50, index=True)  # procurement_reorder
    trigger: str = Field(max_length=20)  # event | manual
    input_context: dict = Field(default_factory=dict, sa_column=Column(JSON))
    recommendation: dict = Field(default_factory=dict, sa_column=Column(JSON))
    rationale: Optional[str] = None
    status: RecommendationStatus = Field(default=RecommendationStatus.proposed, sa_type=String)
    approval_request_id: Optional[uuid.UUID] = Field(default=None, index=True)
    executed_ref_id: Optional[uuid.UUID] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentActionLog(SQLModel, table=True):
    __tablename__ = "agent_action_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    recommendation_id: uuid.UUID = Field(index=True)
    action: str = Field(max_length=50)
    detail: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
