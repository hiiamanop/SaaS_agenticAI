import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_db
from app.models import ExecutionPolicy
from app.schemas import PolicyUpsert, PolicyRead

router = APIRouter(prefix="/agents/policies", tags=["policies"])


@router.get("", response_model=list[PolicyRead])
async def list_policies(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ExecutionPolicy).where(ExecutionPolicy.tenant_id == tenant_id)
    )
    return result.scalars().all()


@router.put("/{agent_type}", response_model=PolicyRead)
async def upsert_policy(
    agent_type: str,
    tenant_id: uuid.UUID,
    body: PolicyUpsert,
    db: AsyncSession = Depends(get_db),
):
    """Create or update the Level-4 execution envelope for an agent type."""
    result = await db.execute(
        select(ExecutionPolicy).where(
            ExecutionPolicy.tenant_id == tenant_id,
            ExecutionPolicy.agent_type == agent_type,
        )
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        policy = ExecutionPolicy(tenant_id=tenant_id, agent_type=agent_type)

    policy.auto_execute_enabled = body.auto_execute_enabled
    policy.max_auto_qty = body.max_auto_qty
    policy.max_auto_value = body.max_auto_value
    policy.allowed_urgencies = body.allowed_urgencies
    policy.updated_at = datetime.utcnow()

    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy
