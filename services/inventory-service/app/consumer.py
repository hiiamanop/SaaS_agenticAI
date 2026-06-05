"""Kafka consumer for Inventory Service.

Subscribes to sales.order.created and reserves stock for each order item.
Never crashes on malformed events — logs warning and continues.
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
from app.events import publish
from app.models import Stock, StockMovement, MovementType

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task | None = None


async def handle_order_created_event(db: AsyncSession, event: dict) -> None:
    """Process a single sales.order.created CloudEvent and reserve stock."""
    try:
        data = event.get("data", {})
        tenant_id_str: str = data.get("tenant_id") or event.get("tenantid", "")
        order_id: str = data.get("order_id", "")
        items: list = data.get("items", [])

        if not tenant_id_str or not order_id:
            logger.warning("handle_order_created_event: missing tenant_id or order_id in event")
            return

        tenant_id = uuid.UUID(tenant_id_str)

        reserved_items = []
        low_stock_items = []

        for item in items:
            product_sku: str = item.get("product_sku", "")
            quantity: int = int(item.get("quantity", 0))

            if not product_sku or quantity <= 0:
                logger.warning("Skipping item with missing sku or zero quantity: %s", item)
                continue

            # Find matching Stock record for this tenant + sku (any warehouse)
            result = await db.execute(
                select(Stock).where(
                    Stock.tenant_id == tenant_id,
                    Stock.product_sku == product_sku,
                )
            )
            stock = result.scalars().first()

            if stock is None:
                logger.warning(
                    "No stock record found for tenant=%s sku=%s — skipping",
                    tenant_id_str,
                    product_sku,
                )
                continue

            # Reserve stock
            stock.qty_available -= quantity
            stock.qty_reserved += quantity
            db.add(stock)

            # Create movement ledger entry
            movement = StockMovement(
                tenant_id=tenant_id,
                stock_id=stock.id,
                movement_type=MovementType.reservation,
                quantity=quantity,
                reference=order_id,
                notes=f"Auto-reserved from order {order_id}",
            )
            db.add(movement)

            reserved_items.append({
                "product_sku": product_sku,
                "quantity": quantity,
                "stock_id": str(stock.id),
            })

            # Flag low stock once availability falls to/below the reorder point
            if stock.qty_available <= stock.reorder_point:
                low_stock_items.append({
                    "product_sku": product_sku,
                    "qty_available": stock.qty_available,
                    "reorder_point": stock.reorder_point,
                    "stock_id": str(stock.id),
                })

        await db.commit()

        # Publish inventory.stock.reserved event
        if reserved_items:
            await publish(
                "inventory.stock.reserved",
                "inventory.stock.reserved",
                tenant_id_str,
                {
                    "order_id": order_id,
                    "tenant_id": tenant_id_str,
                    "reserved_items": reserved_items,
                },
            )

        # Publish inventory.stock.low for each product that hit its reorder point
        for low in low_stock_items:
            await publish(
                "inventory.stock.low",
                "inventory.stock.low",
                tenant_id_str,
                {"tenant_id": tenant_id_str, **low},
            )

    except Exception as exc:
        logger.warning("Failed to process order.created event: %s", exc, exc_info=True)


async def _consume_loop() -> None:
    """Background loop: poll Kafka and process sales.order.created messages."""
    consumer = AIOKafkaConsumer(
        "sales.order.created",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="inventory-service",
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode()),
    )

    try:
        await consumer.start()
        logger.info("Kafka consumer started, listening on sales.order.created")
        async for msg in consumer:
            try:
                event = msg.value
                async with AsyncSessionLocal() as db:
                    await handle_order_created_event(db, event)
            except Exception as exc:
                logger.warning("Error handling Kafka message: %s", exc, exc_info=True)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    logger.info("Inventory consumer task created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
    logger.info("Inventory consumer task stopped")
