"""
Phase 8 Task 4: Marketing → CRM Integration Tests

Three tests:
  1. test_contact_interested_publishes_kafka_event
     — POST /campaigns/{id}/landing-page/form publishes marketing.contact.interested
  2. test_crm_consumer_creates_opportunity
     — CRM consumer creates Contact + Opportunity from the event
  3. test_opportunity_scored_from_campaign
     — Opportunity.value == pain_point_match * 10_000

Tests 2 & 3 use SQLite in-memory with a per-test session.
Test 1 also uses SQLite in-memory for the marketing DB.
No live Postgres or Kafka is required.

NOTE: tests are ordered so that the marketing test (test 1) runs FIRST while
marketing-service is on sys.path, then CRM tests (2 & 3) run with crm-service
active.  SQLModel table metadata for each service is registered exactly once.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel, select

# ── repo paths ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
MARKETING_PATH = str(BASE / "marketing-service")
CRM_PATH = str(BASE / "crm-service")

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
CAMPAIGN_ID = uuid.uuid4()

# ── module-level state ─────────────────────────────────────────────────────────
# We keep a single shared engine for the CRM in-memory SQLite DB
# so that table definitions are registered only once.
_crm_engine = None
_crm_tables_created = False
# Module references cached after first import
_crm_Contact = None
_crm_Opportunity = None
_crm_handle_event = None


# ── CloudEvent factory ──────────────────────────────────────────────────────────

def _make_event(
    *,
    tenant_id: str = str(TENANT_ID),
    campaign_id: str = str(CAMPAIGN_ID),
    contact_name: str = "Budi Santoso",
    contact_email: str = "budi@example.com",
    contact_phone: str = "+6281234567890",
    company: str = "PT Maju Bersama",
    pain_point_match: float = 0.85,
) -> dict:
    return {
        "specversion": "1.0",
        "type": "marketing.contact.interested",
        "source": "marketing-service",
        "subject": f"campaign/{campaign_id}",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "tenantid": tenant_id,
        "correlationid": str(uuid.uuid4()),
        "data": {
            "tenant_id": tenant_id,
            "campaign_id": campaign_id,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "company": company,
            "pain_point_match": pain_point_match,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


# ── sys.path helpers ────────────────────────────────────────────────────────────

def _set_active_service(service_path: str) -> None:
    """Place service_path at the front of sys.path (remove if already present)."""
    if service_path in sys.path:
        sys.path.remove(service_path)
    sys.path.insert(0, service_path)


def _evict_app_modules() -> None:
    """Remove all cached 'app' / 'app.*' modules so the next import picks up the active service."""
    for key in list(sys.modules.keys()):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]


# ══════════════════════════════════════════════════════════════════════════════
# One-time CRM setup: import models + create tables exactly once
# ══════════════════════════════════════════════════════════════════════════════

async def _bootstrap_crm() -> None:
    """Import CRM app.models once and build the in-memory SQLite schema."""
    global _crm_engine, _crm_tables_created, _crm_Contact, _crm_Opportunity, _crm_handle_event

    if _crm_tables_created:
        return  # already done — do NOT re-import (would hit duplicate-table error)

    _set_active_service(CRM_PATH)
    _evict_app_modules()

    import app.models as crm_models
    import app.consumer as crm_consumer

    _crm_Contact = crm_models.Contact
    _crm_Opportunity = crm_models.Opportunity
    _crm_handle_event = crm_consumer.handle_contact_interested_event

    _crm_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with _crm_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    _crm_tables_created = True


@pytest_asyncio.fixture
async def crm_session():
    """Yield a fresh per-test session; tables are cleared between tests."""
    await _bootstrap_crm()

    session_factory = async_sessionmaker(_crm_engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(text("DELETE FROM opportunities"))
        await session.execute(text("DELETE FROM contacts"))
        await session.commit()
        yield session


# ══════════════════════════════════════════════════════════════════════════════
# Test 1 — Marketing service publishes Kafka event on form submit
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_contact_interested_publishes_kafka_event():
    """
    POST /campaigns/{id}/landing-page/form must publish a
    marketing.contact.interested CloudEvent to Kafka.
    """
    _set_active_service(MARKETING_PATH)
    _evict_app_modules()

    from app.main import app
    from app.database import get_db
    from app.models import Campaign  # noqa: F401

    marketing_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with marketing_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_factory = async_sessionmaker(marketing_engine, expire_on_commit=False)

    async with session_factory() as seed_session:
        campaign = Campaign(
            id=CAMPAIGN_ID,
            tenant_id=TENANT_ID,
            name="Q2 SaaS Growth",
            industry="SaaS",
            pain_points="manual workflows",
        )
        seed_session.add(campaign)
        await seed_session.commit()

    published_events: list[tuple[str, dict]] = []

    async def fake_publish(
        topic: str, event_type: str, tenant_id: str, data: dict
    ) -> None:
        published_events.append((topic, {"type": event_type, "data": data}))

    async def override_db():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = override_db

    from httpx import AsyncClient, ASGITransport

    with patch("app.routers.campaigns.publish", side_effect=fake_publish):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                f"/campaigns/{CAMPAIGN_ID}/landing-page/form",
                json={
                    "contact_name": "Budi Santoso",
                    "contact_email": "budi@example.com",
                    "contact_phone": "+6281234567890",
                    "company": "PT Maju Bersama",
                },
            )

    app.dependency_overrides.clear()
    await marketing_engine.dispose()

    assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"

    topics = [e[0] for e in published_events]
    assert "marketing.contact.interested" in topics, (
        f"Expected topic 'marketing.contact.interested', got: {topics}"
    )

    evt = next(
        e[1] for e in published_events if e[0] == "marketing.contact.interested"
    )
    assert evt["type"] == "marketing.contact.interested"
    assert evt["data"]["contact_email"] == "budi@example.com"
    assert evt["data"]["campaign_id"] == str(CAMPAIGN_ID)
    assert "pain_point_match" in evt["data"]


# ══════════════════════════════════════════════════════════════════════════════
# Test 2 — CRM consumer creates Contact + Opportunity from event
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_crm_consumer_creates_opportunity(crm_session: AsyncSession):
    """
    handle_contact_interested_event must persist:
      - one Contact (first/last name split, email, phone, company)
      - one Opportunity linked to that contact (title contains company name)
    """
    Contact = _crm_Contact
    Opportunity = _crm_Opportunity
    handle_contact_interested_event = _crm_handle_event

    event = _make_event(
        contact_name="Siti Rahayu",
        contact_email="siti@example.com",
        contact_phone="+6289876543210",
        company="PT Teknologi Nusantara",
        pain_point_match=0.72,
    )

    # Patch publish in the crm events module (already loaded as app.events)
    with patch("app.events.publish", new_callable=AsyncMock):
        await handle_contact_interested_event(crm_session, event)

    contacts = (
        await crm_session.execute(
            select(Contact).where(Contact.tenant_id == TENANT_ID)
        )
    ).scalars().all()
    assert len(contacts) == 1, f"Expected 1 contact, got {len(contacts)}"
    contact = contacts[0]
    assert contact.email == "siti@example.com"
    assert contact.first_name == "Siti"
    assert contact.last_name == "Rahayu"
    assert contact.company == "PT Teknologi Nusantara"

    opps = (
        await crm_session.execute(
            select(Opportunity).where(Opportunity.tenant_id == TENANT_ID)
        )
    ).scalars().all()
    assert len(opps) == 1, f"Expected 1 opportunity, got {len(opps)}"
    opp = opps[0]
    assert opp.contact_id == contact.id
    assert "PT Teknologi Nusantara" in opp.title


# ══════════════════════════════════════════════════════════════════════════════
# Test 3 — Opportunity value is scored from pain_point_match
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_opportunity_scored_from_campaign(crm_session: AsyncSession):
    """
    Opportunity.value must equal pain_point_match * 10_000.
    Stage must be 'prospect'.
    """
    Opportunity = _crm_Opportunity
    handle_contact_interested_event = _crm_handle_event

    pain_score = 0.85

    event = _make_event(
        contact_name="Andi Pratama",
        contact_email="andi@startup.id",
        contact_phone="+6281111222333",
        company="StartupKeren",
        pain_point_match=pain_score,
    )

    with patch("app.events.publish", new_callable=AsyncMock):
        await handle_contact_interested_event(crm_session, event)

    opps = (
        await crm_session.execute(
            select(Opportunity).where(Opportunity.tenant_id == TENANT_ID)
        )
    ).scalars().all()
    assert len(opps) == 1, f"Expected 1 opportunity, got {len(opps)}"

    expected = pain_score * 10_000
    assert opps[0].value == pytest.approx(expected), (
        f"Expected value {expected}, got {opps[0].value}"
    )
    assert opps[0].stage.value == "prospect"
