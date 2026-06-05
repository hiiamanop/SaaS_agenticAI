"""Approval workflow engine — shared by routers and the Kafka consumer.

A request always gets a fixed 3-step chain: manager -> director -> cfo.
Steps must be approved in order. When the final step is approved the request
is approved; any rejection rejects the whole request.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalStatus,
    StepStatus,
)
from app.events import publish

WORKFLOW_ROLES = ["manager", "director", "cfo"]


def serialize_request(req: ApprovalRequest, steps: list[ApprovalStep]) -> dict:
    return {
        "id": req.id,
        "tenant_id": req.tenant_id,
        "request_type": req.request_type,
        "reference_id": req.reference_id,
        "status": req.status,
        "created_at": req.created_at,
        "steps": [
            {
                "id": s.id,
                "approval_request_id": s.approval_request_id,
                "approver_role": s.approver_role,
                "order_number": s.order_number,
                "status": s.status,
                "created_at": s.created_at,
            }
            for s in sorted(steps, key=lambda s: s.order_number)
        ],
    }


async def load_steps(db: AsyncSession, request_id: uuid.UUID) -> list[ApprovalStep]:
    result = await db.execute(
        select(ApprovalStep).where(ApprovalStep.approval_request_id == request_id)
    )
    return list(result.scalars().all())


async def create_approval_request(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    request_type: str,
    reference_id: uuid.UUID,
    publish_event: bool = True,
) -> tuple[ApprovalRequest, list[ApprovalStep]]:
    """Create an approval request with the standard 3-step workflow."""
    req = ApprovalRequest(
        tenant_id=tenant_id,
        request_type=request_type,
        reference_id=reference_id,
        status=ApprovalStatus.pending,
    )
    db.add(req)
    await db.flush()

    steps: list[ApprovalStep] = []
    for idx, role in enumerate(WORKFLOW_ROLES, start=1):
        step = ApprovalStep(
            tenant_id=tenant_id,
            approval_request_id=req.id,
            approver_role=role,
            order_number=idx,
        )
        db.add(step)
        steps.append(step)

    await db.commit()
    await db.refresh(req)

    if publish_event:
        await publish(
            "approval.request.created",
            "approval.request.created",
            str(tenant_id),
            {
                "approval_request_id": str(req.id),
                "tenant_id": str(tenant_id),
                "request_type": request_type,
                "reference_id": str(reference_id),
            },
        )

    return req, steps


async def _publish_request_outcome(req: ApprovalRequest, event_type: str) -> None:
    await publish(
        event_type,
        event_type,
        str(req.tenant_id),
        {
            "approval_request_id": str(req.id),
            "tenant_id": str(req.tenant_id),
            "request_type": req.request_type,
            "reference_id": str(req.reference_id),
            "status": req.status.value,
        },
    )
