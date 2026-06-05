"""Kafka consumer for Approval Service.

Subscribes to procurement.po.created and accounting.invoice.created and starts
a 3-step approval workflow for each. Never crashes on malformed events.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.service import create_approval_request

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task | None = None

# Map source topic -> (request_type, reference key in event data)
TOPIC_MAP = {
    "procurement.po.created": ("procurement_po", "po_id"),
    "accounting.invoice.created": ("accounting_invoice", "invoice_id"),
}


async def handle_event(db: AsyncSession, topic: str, event: dict) -> None:
    """Process a CloudEvent and open an approval workflow."""
    try:
        mapping = TOPIC_MAP.get(topic)
        if mapping is None:
            return
        request_type, ref_key = mapping

        data = event.get("data", {})
        tenant_id_str: str = data.get("tenant_id") or event.get("tenantid", "")
        reference_id_str: str = data.get(ref_key, "")

        if not tenant_id_str or not reference_id_str:
            logger.warning("handle_event: missing tenant_id or %s in event", ref_key)
            return

        await create_approval_request(
            db,
            tenant_id=uuid.UUID(tenant_id_str),
            request_type=request_type,
            reference_id=uuid.UUID(reference_id_str),
        )
        logger.info("Opened %s approval workflow for %s", request_type, reference_id_str)

    except Exception as exc:
        logger.warning("Failed to process %s event: %s", topic, exc, exc_info=True)


async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        *TOPIC_MAP.keys(),
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="approval-service",
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode()),
    )

    try:
        await consumer.start()
        logger.info("Kafka consumer started, listening on %s", list(TOPIC_MAP.keys()))
        async for msg in consumer:
            try:
                async with AsyncSessionLocal() as db:
                    await handle_event(db, msg.topic, msg.value)
            except Exception as exc:
                logger.warning("Error handling Kafka message: %s", exc, exc_info=True)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    logger.info("Approval consumer task created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
    logger.info("Approval consumer task stopped")
