# services/audit-service/app/models.py
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_id: str = Field(index=True)
    event_type: str = Field(index=True)
    topic: str
    tenant_id: Optional[str] = Field(default=None, index=True)
    source: Optional[str] = None
    payload: str
    received_at: datetime = Field(default_factory=datetime.utcnow)
