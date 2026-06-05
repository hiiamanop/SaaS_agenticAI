"""Kafka consumer for Accounting Service.

Subscribes to procurement.po.created and auto-creates a draft vendor invoice.
Never crashes on malformed events — logs warning and continues.
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
from app.service import create_invoice

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task | None = None


async def handle_po_created_event(db: AsyncSession, event: dict) -> None:
    """Process a single procurement.po.created CloudEvent and create a draft invoice."""
    try:
        data = event.get("data", {})
        tenant_id_str: str = data.get("tenant_id") or event.get("tenantid", "")
        po_id_str: str = data.get("po_id", "")
        vendor_id_str: str | None = data.get("vendor_id")
        items: list = data.get("items", [])

        if not tenant_id_str or not po_id_str:
            logger.warning("handle_po_created_event: missing tenant_id or po_id in event")
            return

        tenant_id = uuid.UUID(tenant_id_str)
        po_id = uuid.UUID(po_id_str)
        vendor_id = uuid.UUID(vendor_id_str) if vendor_id_str else None

        items_data = [
            {
                "po_item_id": uuid.UUID(it["po_item_id"]) if it.get("po_item_id") else None,
                "product_sku": it.get("product_sku"),
                "quantity": int(it.get("quantity", 1)),
                "amount": it.get("total_price", it.get("unit_price", "0.00")),
            }
            for it in items
        ]

        await create_invoice(
            db,
            tenant_id=tenant_id,
            items_data=items_data,
            vendor_id=vendor_id,
            po_id=po_id,
        )
        logger.info("Auto-created invoice for PO %s (tenant %s)", po_id_str, tenant_id_str)

    except Exception as exc:
        logger.warning("Failed to process procurement.po.created event: %s", exc, exc_info=True)


async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        "procurement.po.created",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="accounting-service",
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode()),
    )

    try:
        await consumer.start()
        logger.info("Kafka consumer started, listening on procurement.po.created")
        async for msg in consumer:
            try:
                event = msg.value
                async with AsyncSessionLocal() as db:
                    await handle_po_created_event(db, event)
            except Exception as exc:
                logger.warning("Error handling Kafka message: %s", exc, exc_info=True)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    logger.info("Accounting consumer task created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
    logger.info("Accounting consumer task stopped")
