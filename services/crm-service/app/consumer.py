"""Kafka consumer for CRM Service.

Subscribes to ``marketing.contact.interested`` and auto-creates:
  - a ``Contact`` record (name split into first/last)
  - an ``Opportunity`` record (value = pain_point_match * 10_000)

Then publishes ``crm.opportunity.created`` back to Kafka.

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
from app.models import Contact, Opportunity, OpportunityStage

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task | None = None

# ── core handler (testable in isolation) ────────────────────────────────────

async def handle_contact_interested_event(db: AsyncSession, event: dict) -> None:
    """
    Process a single ``marketing.contact.interested`` CloudEvent.

    Steps:
      1. Extract contact data from event.data
      2. Create crm.Contact (split name into first_name / last_name)
      3. Create crm.Opportunity (value = pain_point_match * 10_000)
      4. Commit
      5. Publish crm.opportunity.created
    """
    try:
        data: dict = event.get("data", {})
        tenant_id_str: str = data.get("tenant_id") or event.get("tenantid", "")
        campaign_id_str: str = data.get("campaign_id", "")
        contact_name: str = data.get("contact_name", "")
        contact_email: str = data.get("contact_email", "")
        contact_phone: str = data.get("contact_phone", "")
        company: str = data.get("company", "")
        pain_point_match: float = float(data.get("pain_point_match", 0.0))

        if not tenant_id_str or not contact_email:
            logger.warning(
                "handle_contact_interested_event: missing tenant_id or contact_email — skipping"
            )
            return

        tenant_id = uuid.UUID(tenant_id_str)

        # Split name: "First Last" → first_name="First", last_name="Last"
        # Multi-word names: everything after first token becomes last_name.
        name_parts = contact_name.strip().split(None, 1)
        first_name = name_parts[0] if name_parts else "Unknown"
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # ── 1. Create Contact ───────────────────────────────────────────────
        contact = Contact(
            tenant_id=tenant_id,
            first_name=first_name,
            last_name=last_name,
            email=contact_email,
            phone=contact_phone or None,
            company=company or None,
        )
        db.add(contact)
        await db.flush()  # get contact.id before creating Opportunity

        # ── 2. Create Opportunity ───────────────────────────────────────────
        opportunity_value: float = pain_point_match * 10_000
        opportunity = Opportunity(
            tenant_id=tenant_id,
            contact_id=contact.id,
            title=f"{company} — Marketing Lead" if company else f"{contact_name} — Marketing Lead",
            value=opportunity_value,
            stage=OpportunityStage.prospect,
        )
        db.add(opportunity)
        await db.commit()
        await db.refresh(opportunity)

        logger.info(
            "CRM: created contact=%s opportunity=%s value=%.2f for tenant=%s",
            contact.id,
            opportunity.id,
            opportunity_value,
            tenant_id_str,
        )

        # ── 3. Publish crm.opportunity.created ─────────────────────────────
        await publish(
            "crm.opportunity.created",
            "crm.opportunity.created",
            tenant_id_str,
            {
                "tenant_id": tenant_id_str,
                "campaign_id": campaign_id_str,
                "opportunity_id": str(opportunity.id),
                "contact_id": str(contact.id),
                "contact_email": contact_email,
                "company": company,
                "value": opportunity_value,
                "stage": opportunity.stage.value,
            },
        )

    except Exception as exc:
        logger.warning(
            "Failed to process marketing.contact.interested event: %s",
            exc,
            exc_info=True,
        )


# ── background consumer loop ─────────────────────────────────────────────────

async def _consume_loop() -> None:
    """Poll Kafka and process marketing.contact.interested messages."""
    consumer = AIOKafkaConsumer(
        "marketing.contact.interested",
        bootstrap_servers=settings.kafka_brokers,
        group_id="crm-service",
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode()),
    )

    try:
        await consumer.start()
        logger.info("CRM Kafka consumer started, listening on marketing.contact.interested")
        async for msg in consumer:
            try:
                event = msg.value
                async with AsyncSessionLocal() as db:
                    await handle_contact_interested_event(db, event)
            except Exception as exc:
                logger.warning("Error handling Kafka message: %s", exc, exc_info=True)
    finally:
        await consumer.stop()
        logger.info("CRM Kafka consumer stopped")


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())
    logger.info("CRM consumer task created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    _consumer_task = None
    logger.info("CRM consumer task stopped")
