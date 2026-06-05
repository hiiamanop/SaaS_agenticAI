"""Agent domain logic — shared by routers and the Kafka consumer.

Flow: recommend (LLM) -> publish agent.action.recommended -> [Approval HITL] ->
execute (create a procurement requisition) -> publish agent.action.executed.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.events import publish
from app.gateway import get_gateway, ReorderContext
from app.models import AgentRecommendation, AgentActionLog, RecommendationStatus

logger = logging.getLogger(__name__)

AGENT_TYPE = "procurement_reorder"


async def _log(db: AsyncSession, rec: AgentRecommendation, action: str, detail: str = "") -> None:
    db.add(AgentActionLog(
        tenant_id=rec.tenant_id,
        recommendation_id=rec.id,
        action=action,
        detail=detail,
    ))


async def create_reorder_recommendation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    product_sku: str,
    qty_available: int,
    reorder_point: int,
    trigger: str = "manual",
    publish_event: bool = True,
) -> AgentRecommendation:
    """Run the model gateway and persist a proposed recommendation."""
    gateway = get_gateway()
    ctx = ReorderContext(
        product_sku=product_sku,
        qty_available=qty_available,
        reorder_point=reorder_point,
    )
    result = await gateway.recommend_reorder(ctx)

    rec = AgentRecommendation(
        tenant_id=tenant_id,
        agent_type=AGENT_TYPE,
        trigger=trigger,
        input_context={
            "product_sku": product_sku,
            "qty_available": qty_available,
            "reorder_point": reorder_point,
        },
        recommendation=result,
        rationale=result.get("reason"),
        status=RecommendationStatus.proposed,
    )
    db.add(rec)
    await db.flush()
    await _log(db, rec, "recommended", f"provider={gateway.name} qty={result.get('recommended_qty')}")
    await db.commit()
    await db.refresh(rec)

    if publish_event:
        await publish(
            "agent.action.recommended",
            "agent.action.recommended",
            str(tenant_id),
            {
                "recommendation_id": str(rec.id),
                "tenant_id": str(tenant_id),
                "agent_type": AGENT_TYPE,
                "product_sku": product_sku,
                "recommended_qty": result.get("recommended_qty"),
                "urgency": result.get("urgency"),
            },
        )
    return rec


async def create_requisition(
    tenant_id: uuid.UUID, product_sku: str, quantity: int, reason: str
) -> uuid.UUID:
    """Call procurement-service to create a requisition. Returns its id."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{settings.procurement_url}/requisitions/",
            json={
                "tenant_id": str(tenant_id),
                "product_sku": product_sku,
                "quantity": quantity,
                "reason": reason,
            },
        )
        resp.raise_for_status()
        return uuid.UUID(resp.json()["id"])


async def execute_recommendation(
    db: AsyncSession, rec: AgentRecommendation, publish_event: bool = True
) -> AgentRecommendation:
    """Execute an approved recommendation by creating a procurement requisition."""
    if rec.status == RecommendationStatus.executed:
        return rec

    sku = rec.recommendation.get("product_sku") or rec.input_context.get("product_sku")
    qty = int(rec.recommendation.get("recommended_qty", 0))

    try:
        requisition_id = await create_requisition(
            rec.tenant_id, sku, qty, reason=f"Auto-reorder by {AGENT_TYPE} agent"
        )
        rec.status = RecommendationStatus.executed
        rec.executed_ref_id = requisition_id
        rec.updated_at = datetime.utcnow()
        db.add(rec)
        await _log(db, rec, "executed", f"requisition={requisition_id}")
        await db.commit()
        await db.refresh(rec)

        if publish_event:
            await publish(
                "agent.action.executed",
                "agent.action.executed",
                str(rec.tenant_id),
                {
                    "recommendation_id": str(rec.id),
                    "tenant_id": str(rec.tenant_id),
                    "requisition_id": str(requisition_id),
                    "product_sku": sku,
                    "quantity": qty,
                },
            )
    except Exception as exc:
        rec.status = RecommendationStatus.failed
        rec.updated_at = datetime.utcnow()
        db.add(rec)
        await _log(db, rec, "failed", str(exc))
        await db.commit()
        if publish_event:
            await publish(
                "agent.workflow.failed",
                "agent.workflow.failed",
                str(rec.tenant_id),
                {"recommendation_id": str(rec.id), "tenant_id": str(rec.tenant_id), "error": str(exc)},
            )
        logger.warning("Execution failed for recommendation %s: %s", rec.id, exc)

    return rec
