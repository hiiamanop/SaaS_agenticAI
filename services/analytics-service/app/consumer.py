"""Kafka consumer for Analytics Service.

Subscribes to events from sales, inventory, procurement and accounting and
maintains incremental, idempotent read-model tables. Never crashes on a
malformed event — logs a warning and continues.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import RevenueDaily, ProcurementSpend, InventorySignal

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task | None = None

TOPICS = [
    "sales.order.created",
    "inventory.stock.reserved",
    "inventory.stock.low",
    "procurement.po.created",
    "accounting.invoice.created",
    "accounting.payment.recorded",
]


def _dec(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _event_day(event: dict) -> date:
    t = event.get("time")
    if t:
        try:
            return datetime.fromisoformat(t.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    return date.today()


async def _get_spend(db: AsyncSession, tenant_id: uuid.UUID) -> ProcurementSpend:
    result = await db.execute(
        select(ProcurementSpend).where(ProcurementSpend.tenant_id == tenant_id)
    )
    spend = result.scalar_one_or_none()
    if spend is None:
        spend = ProcurementSpend(tenant_id=tenant_id)
        db.add(spend)
        await db.flush()
    return spend


async def _get_signal(db: AsyncSession, tenant_id: uuid.UUID, sku: str) -> InventorySignal:
    result = await db.execute(
        select(InventorySignal).where(
            InventorySignal.tenant_id == tenant_id,
            InventorySignal.product_sku == sku,
        )
    )
    sig = result.scalar_one_or_none()
    if sig is None:
        sig = InventorySignal(tenant_id=tenant_id, product_sku=sku)
        db.add(sig)
        await db.flush()
    return sig


async def handle_event(db: AsyncSession, topic: str, event: dict) -> None:
    """Dispatch a CloudEvent to the matching read-model updater."""
    try:
        data = event.get("data", {})
        tenant_id_str = data.get("tenant_id") or event.get("tenantid", "")
        if not tenant_id_str:
            logger.warning("analytics: event without tenant_id on %s", topic)
            return
        tenant_id = uuid.UUID(tenant_id_str)

        if topic == "sales.order.created":
            total = sum(
                (_dec(i.get("unit_price")) * int(i.get("quantity", 0)) for i in data.get("items", [])),
                Decimal("0.00"),
            )
            day = _event_day(event)
            result = await db.execute(
                select(RevenueDaily).where(
                    RevenueDaily.tenant_id == tenant_id, RevenueDaily.day == day
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = RevenueDaily(tenant_id=tenant_id, day=day)
                db.add(row)
            row.order_count += 1
            row.revenue_total += total
            row.updated_at = datetime.utcnow()

        elif topic == "inventory.stock.reserved":
            for item in data.get("reserved_items", []):
                sku = item.get("product_sku")
                if not sku:
                    continue
                sig = await _get_signal(db, tenant_id, sku)
                sig.qty_reserved_total += int(item.get("quantity", 0))
                sig.updated_at = datetime.utcnow()

        elif topic == "inventory.stock.low":
            sku = data.get("product_sku")
            if sku:
                sig = await _get_signal(db, tenant_id, sku)
                sig.low_stock_events += 1
                sig.updated_at = datetime.utcnow()

        elif topic == "procurement.po.created":
            spend = await _get_spend(db, tenant_id)
            spend.po_count += 1
            spend.po_total += _dec(data.get("total_amount"))
            spend.updated_at = datetime.utcnow()

        elif topic == "accounting.invoice.created":
            spend = await _get_spend(db, tenant_id)
            spend.invoice_count += 1
            spend.invoice_total += _dec(data.get("total_amount"))
            spend.updated_at = datetime.utcnow()

        elif topic == "accounting.payment.recorded":
            spend = await _get_spend(db, tenant_id)
            spend.paid_total += _dec(data.get("amount"))
            spend.updated_at = datetime.utcnow()

        await db.commit()

    except Exception as exc:
        logger.warning("analytics: failed to process %s event: %s", topic, exc, exc_info=True)


async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="analytics-service",
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode()),
    )
    try:
        await consumer.start()
        logger.info("Analytics consumer started on %s", TOPICS)
        async for msg in consumer:
            try:
                async with AsyncSessionLocal() as db:
                    await handle_event(db, msg.topic, msg.value)
            except Exception as exc:
                logger.warning("analytics: error handling message: %s", exc, exc_info=True)
    finally:
        await consumer.stop()
        logger.info("Analytics consumer stopped")


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    logger.info("Analytics consumer task created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
    logger.info("Analytics consumer task stopped")
