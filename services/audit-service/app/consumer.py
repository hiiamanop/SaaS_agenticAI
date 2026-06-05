# services/audit-service/app/consumer.py
"""Kafka consumer — persists every event to audit_logs."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from aiokafka import AIOKafkaConsumer

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import AuditLog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def process_event(topic: str, payload: bytes, db: "AsyncSession") -> None:
    """Parse one Kafka message and write to audit_logs. Never raises."""
    try:
        data = json.loads(payload.decode())
        log = AuditLog(
            event_id=data.get("id", "unknown"),
            event_type=data.get("type", topic),
            topic=topic,
            tenant_id=data.get("tenantid"),
            source=data.get("source"),
            payload=payload.decode(),
        )
        db.add(log)
    except Exception as exc:
        logger.warning("audit: failed to parse event on %s: %s", topic, exc)


async def run_consumer() -> None:
    """Long-running Kafka consumer loop. Runs as background task."""
    topics = [t.strip() for t in settings.kafka_topics.split(",") if t.strip()]
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_brokers,
        group_id=settings.kafka_group_id,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            async with AsyncSessionLocal() as db:
                await process_event(msg.topic, msg.value, db)
                await db.commit()
    except asyncio.CancelledError:
        pass
    finally:
        await consumer.stop()
