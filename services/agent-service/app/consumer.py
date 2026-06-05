"""Kafka consumer for Agent Service.

Two responsibilities:
- inventory.stock.low      -> generate a reorder recommendation (autonomous trigger)
- approval.request.approved -> execute the approved recommendation (HITL close-out)

Never crashes on a malformed event — logs a warning and continues.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import AgentRecommendation, RecommendationStatus
from app.service import create_reorder_recommendation, execute_recommendation

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task | None = None

TOPICS = ["inventory.stock.low", "approval.request.approved"]


async def handle_stock_low(db: AsyncSession, event: dict) -> None:
    data = event.get("data", {})
    tenant_id_str = data.get("tenant_id") or event.get("tenantid", "")
    sku = data.get("product_sku", "")
    if not tenant_id_str or not sku:
        logger.warning("agent: stock.low event missing tenant_id or product_sku")
        return
    await create_reorder_recommendation(
        db,
        tenant_id=uuid.UUID(tenant_id_str),
        product_sku=sku,
        qty_available=int(data.get("qty_available", 0)),
        reorder_point=int(data.get("reorder_point", 0)),
        trigger="event",
    )


async def handle_approval_approved(db: AsyncSession, event: dict) -> None:
    data = event.get("data", {})
    if data.get("request_type") != "agent_action":
        return  # not ours
    tenant_id_str = data.get("tenant_id") or event.get("tenantid", "")
    rec_id_str = data.get("reference_id", "")
    if not tenant_id_str or not rec_id_str:
        logger.warning("agent: approval.approved event missing tenant_id or reference_id")
        return

    result = await db.execute(
        select(AgentRecommendation).where(
            AgentRecommendation.id == uuid.UUID(rec_id_str),
            AgentRecommendation.tenant_id == uuid.UUID(tenant_id_str),
        )
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        logger.warning("agent: no recommendation %s to execute", rec_id_str)
        return
    rec.status = RecommendationStatus.approved
    db.add(rec)
    await db.commit()
    await execute_recommendation(db, rec)


async def handle_event(db: AsyncSession, topic: str, event: dict) -> None:
    try:
        if topic == "inventory.stock.low":
            await handle_stock_low(db, event)
        elif topic == "approval.request.approved":
            await handle_approval_approved(db, event)
    except Exception as exc:
        logger.warning("agent: failed to process %s event: %s", topic, exc, exc_info=True)


async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="agent-service",
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode()),
    )
    try:
        await consumer.start()
        logger.info("Agent consumer started on %s", TOPICS)
        async for msg in consumer:
            try:
                async with AsyncSessionLocal() as db:
                    await handle_event(db, msg.topic, msg.value)
            except Exception as exc:
                logger.warning("agent: error handling message: %s", exc, exc_info=True)
    finally:
        await consumer.stop()
        logger.info("Agent consumer stopped")


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    logger.info("Agent consumer task created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
    logger.info("Agent consumer task stopped")
