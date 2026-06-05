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


class Decision(str, Enum):
    """Level-4 routing decision for a recommendation."""
    auto_execute = "auto_execute"
    escalate = "escalate"


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
    # Level-4 autonomy: how the recommendation was routed and ultimately executed.
    decision: Optional[str] = Field(default=None, sa_type=String)  # auto_execute | escalate
    decision_reason: Optional[str] = None
    autonomy_mode: Optional[str] = Field(default=None, sa_type=String)  # auto | hitl
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


class ExecutionPolicy(SQLModel, table=True):
    """Per-tenant, per-agent-type envelope for Level-4 autonomous execution.

    Default-off: with no row (or auto_execute_enabled=False) the agent behaves
    exactly like Level 3 — every recommendation escalates to HITL.
    """
    __tablename__ = "execution_policies"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    agent_type: str = Field(max_length=50, index=True)
    auto_execute_enabled: bool = Field(default=False)
    max_auto_qty: int = Field(default=0)
    max_auto_value: Optional[float] = Field(default=None)
    allowed_urgencies: list = Field(
        default_factory=lambda: ["normal", "high"], sa_column=Column(JSON)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
