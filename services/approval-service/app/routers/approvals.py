import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalComment,
    ApprovalStatus,
    StepStatus,
)
from app.schemas import ApprovalRequestCreate, ApprovalRequestRead, StepDecision
from app.service import (
    create_approval_request,
    load_steps,
    serialize_request,
    _publish_request_outcome,
)

router = APIRouter(prefix="/approval-requests", tags=["approvals"])


async def _get_request(db: AsyncSession, request_id: uuid.UUID) -> ApprovalRequest:
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return req


@router.post("/", response_model=ApprovalRequestRead, status_code=status.HTTP_201_CREATED)
async def create_request(body: ApprovalRequestCreate, db: AsyncSession = Depends(get_db)):
    req, steps = await create_approval_request(
        db,
        tenant_id=body.tenant_id,
        request_type=body.request_type,
        reference_id=body.reference_id,
    )
    return serialize_request(req, steps)


@router.get("/", response_model=list[ApprovalRequestRead])
async def list_requests(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.tenant_id == tenant_id)
    )
    requests = result.scalars().all()
    out = []
    for req in requests:
        steps = await load_steps(db, req.id)
        out.append(serialize_request(req, steps))
    return out


@router.get("/{request_id}", response_model=ApprovalRequestRead)
async def get_request(request_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    req = await _get_request(db, request_id)
    steps = await load_steps(db, req.id)
    return serialize_request(req, steps)


def _next_pending_step(steps: list[ApprovalStep]) -> ApprovalStep | None:
    for step in sorted(steps, key=lambda s: s.order_number):
        if step.status == StepStatus.pending:
            return step
    return None


@router.post("/{request_id}/steps/{step_id}/approve", response_model=ApprovalRequestRead)
async def approve_step(
    request_id: uuid.UUID,
    step_id: uuid.UUID,
    body: StepDecision,
    db: AsyncSession = Depends(get_db),
):
    req = await _get_request(db, request_id)
    if req.status != ApprovalStatus.pending:
        raise HTTPException(status_code=409, detail=f"Request already {req.status.value}")

    steps = await load_steps(db, req.id)
    next_step = _next_pending_step(steps)
    if next_step is None or next_step.id != step_id:
        raise HTTPException(
            status_code=409,
            detail="Steps must be approved in order; this is not the next pending step",
        )

    next_step.status = StepStatus.approved
    next_step.updated_at = datetime.utcnow()
    db.add(next_step)
    if body.message:
        db.add(ApprovalComment(
            tenant_id=req.tenant_id,
            approval_step_id=next_step.id,
            approver_id=body.approver_id,
            message=body.message,
        ))

    # If all steps now approved, approve the request
    outcome_event = None
    if all(s.status == StepStatus.approved for s in steps):
        req.status = ApprovalStatus.approved
        req.updated_at = datetime.utcnow()
        db.add(req)
        outcome_event = "approval.request.approved"

    await db.commit()
    await db.refresh(req)
    steps = await load_steps(db, req.id)

    if outcome_event:
        await _publish_request_outcome(req, outcome_event)

    return serialize_request(req, steps)


@router.post("/{request_id}/steps/{step_id}/reject", response_model=ApprovalRequestRead)
async def reject_step(
    request_id: uuid.UUID,
    step_id: uuid.UUID,
    body: StepDecision,
    db: AsyncSession = Depends(get_db),
):
    req = await _get_request(db, request_id)
    if req.status != ApprovalStatus.pending:
        raise HTTPException(status_code=409, detail=f"Request already {req.status.value}")

    steps = await load_steps(db, req.id)
    next_step = _next_pending_step(steps)
    if next_step is None or next_step.id != step_id:
        raise HTTPException(
            status_code=409,
            detail="Steps must be processed in order; this is not the next pending step",
        )

    next_step.status = StepStatus.rejected
    next_step.updated_at = datetime.utcnow()
    db.add(next_step)
    if body.message:
        db.add(ApprovalComment(
            tenant_id=req.tenant_id,
            approval_step_id=next_step.id,
            approver_id=body.approver_id,
            message=body.message,
        ))

    req.status = ApprovalStatus.rejected
    req.updated_at = datetime.utcnow()
    db.add(req)

    await db.commit()
    await db.refresh(req)
    steps = await load_steps(db, req.id)

    await _publish_request_outcome(req, "approval.request.rejected")

    return serialize_request(req, steps)
