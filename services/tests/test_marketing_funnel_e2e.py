"""
Phase 8 Task 6: End-to-End Marketing Funnel Smoke Test

Full workflow from campaign creation to CRM opportunity creation:

  1.  Create campaign in marketing-service (POST /campaigns/)
  2.  Trigger CIS Agent → discover companies → publish marketing.contacts.discovered
  3.  Verify 3+ company targets discovered
  4.  Trigger Content Planner Agent → generate strategy → HITL approval
  5.  Marketing Manager approves → marketing.campaign.strategy.approved
  6.  Trigger Blog Writer Agent → write article → publish event
  7.  Trigger Ads Orchestrator Agent → create ads → deploy (meta + google)
  8.  Trigger Landing Page Agent → generate page → return page_url
  9.  Submit contact form (POST /campaigns/{id}/landing-page/form)
 10.  Verify marketing.contact.interested published to Kafka
 11.  Verify CRM consumer creates Contact + Opportunity
 12.  Verify opportunity visible (GET /opportunities/?tenant_id=X)
 13.  Verify opportunity value = pain_point_match * 10_000
 14.  Verify event chain completeness (8+ events across the pipeline)

All services use SQLite in-memory — no live Postgres or Kafka required.

Design notes:
- Marketing-service is loaded FIRST and held across the full test so that
  SQLAlchemy's metadata never sees a duplicate table registration.
- Agent-service is loaded SECOND (after marketing models are registered)
  and agents are imported directly.
- CRM models are loaded LAST (single bootstrap) so the CRM test tables
  are only created once.
- The three service paths are kept on sys.path in the order:
    agent-service (for imports) > crm-service (for consumer) > marketing-service
  and `_evict_app_modules()` is called whenever we switch active service.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel, select

# ── repo paths ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
MARKETING_PATH = str(BASE / "marketing-service")
AGENT_PATH = str(BASE / "agent-service")
CRM_PATH = str(BASE / "crm-service")

# ── fixed IDs for the test session ─────────────────────────────────────────────
TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")

# ── module-level singletons (kept for single-bootstrap pattern) ─────────────────
_crm_engine = None
_crm_tables_created = False
_crm_Contact = None
_crm_Opportunity = None
_crm_handle_event = None

_marketing_engine = None
_marketing_tables_created = False
_marketing_app = None
_marketing_get_db = None
_marketing_campaigns_router = None
_marketing_Campaign = None


# ── helpers ─────────────────────────────────────────────────────────────────────


def _set_active_service(service_path: str) -> None:
    """Place *service_path* first on sys.path, evicting previous entry."""
    if service_path in sys.path:
        sys.path.remove(service_path)
    sys.path.insert(0, service_path)


def _evict_app_modules() -> None:
    """Remove all cached 'app' / 'app.*' modules so next import is fresh."""
    for key in list(sys.modules.keys()):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]


async def _bootstrap_marketing() -> tuple:
    """Import marketing-service app + build SQLite schema exactly once.

    Returns (engine, session_factory, app, get_db, campaigns_router, Campaign).
    Safe to call multiple times — re-uses the existing engine on subsequent calls.

    When running alongside test_marketing_crm_integration.py in the same pytest
    session the 'campaigns' table will already be in SQLModel.metadata (from that
    test's import).  We detect this and temporarily remove the marketing tables
    from the metadata registry so the fresh import can re-add them without
    raising "Table already defined".
    """
    global _marketing_engine, _marketing_tables_created
    global _marketing_app, _marketing_get_db, _marketing_campaigns_router, _marketing_Campaign

    if not _marketing_tables_created:
        # Marketing table names registered by this service.
        _MARKETING_TABLES = frozenset(
            ["campaigns", "company_targets", "content_assets", "ad_campaigns"]
        )

        # If these tables are already in SQLModel.metadata (from a previous test
        # in the same session), temporarily remove them so the fresh import does
        # not raise "Table already defined".
        evicted_tables: dict[str, object] = {}
        for tname in _MARKETING_TABLES:
            if tname in SQLModel.metadata.tables:
                evicted_tables[tname] = SQLModel.metadata.tables[tname]
                SQLModel.metadata.remove(SQLModel.metadata.tables[tname])  # type: ignore[arg-type]

        _set_active_service(MARKETING_PATH)
        _evict_app_modules()

        from app.main import app as mk_app
        from app.database import get_db as mk_get_db
        from app.models import Campaign as MkCampaign
        import app.routers.campaigns as mk_campaigns_router

        _marketing_app = mk_app
        _marketing_get_db = mk_get_db
        _marketing_campaigns_router = mk_campaigns_router
        _marketing_Campaign = MkCampaign

        _marketing_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        async with _marketing_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        _marketing_tables_created = True

    session_factory = async_sessionmaker(_marketing_engine, expire_on_commit=False)
    return (
        _marketing_engine,
        session_factory,
        _marketing_app,
        _marketing_get_db,
        _marketing_campaigns_router,
        _marketing_Campaign,
    )


async def _bootstrap_crm() -> None:
    """Import CRM models + build SQLite schema exactly once.

    When test_marketing_crm_integration.py runs before this test in the same
    pytest session, the CRM tables (leads, contacts, opportunities) will already
    be in SQLModel.metadata.  We evict them first so the fresh import succeeds.
    """
    global _crm_engine, _crm_tables_created, _crm_Contact, _crm_Opportunity, _crm_handle_event

    if _crm_tables_created:
        return

    _CRM_TABLES = frozenset(["leads", "contacts", "opportunities"])

    # Remove CRM tables from shared metadata if a previous test already loaded them.
    for tname in _CRM_TABLES:
        if tname in SQLModel.metadata.tables:
            SQLModel.metadata.remove(SQLModel.metadata.tables[tname])  # type: ignore[arg-type]

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


# ══════════════════════════════════════════════════════════════════════════════
# The single end-to-end smoke test
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_complete_marketing_funnel():
    """
    Smoke-test the complete marketing automation funnel:

      campaign created → companies discovered → strategy approved
      → blog article written → ads created → landing page deployed
      → contact form submitted → CRM opportunity created
    """

    # ── Shared event log ────────────────────────────────────────────────────────
    event_log: list[dict] = []
    events_by_topic: dict[str, list[dict]] = {}

    async def fake_publish(topic: str, event_type: str, tenant_id: str, data: dict) -> None:
        entry = {"topic": topic, "type": event_type, "tenant_id": tenant_id, "data": data}
        event_log.append(entry)
        events_by_topic.setdefault(topic, []).append(entry)

    # =========================================================================
    # Phase A: Bootstrap marketing-service ONCE (singleton) — avoids
    #          duplicate-table errors when tests run in the same process.
    # =========================================================================
    (
        marketing_engine,
        mk_session_factory,
        marketing_app,
        marketing_get_db,
        _mk_campaigns_router,
        Campaign,
    ) = await _bootstrap_marketing()

    # Clear all rows so each test run starts fresh
    async with mk_session_factory() as clear_session:
        await clear_session.execute(text("DELETE FROM ad_campaigns"))
        await clear_session.execute(text("DELETE FROM content_assets"))
        await clear_session.execute(text("DELETE FROM company_targets"))
        await clear_session.execute(text("DELETE FROM campaigns"))
        await clear_session.commit()

    async def override_marketing_db():
        async with mk_session_factory() as s:
            yield s

    marketing_app.dependency_overrides[marketing_get_db] = override_marketing_db

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1 — Create campaign via HTTP
    # ─────────────────────────────────────────────────────────────────────────
    from httpx import AsyncClient, ASGITransport

    with patch("app.routers.campaigns.publish", side_effect=fake_publish):
        async with AsyncClient(
            transport=ASGITransport(app=marketing_app), base_url="http://test"
        ) as mc:
            create_resp = await mc.post(
                "/campaigns/",
                json={
                    "tenant_id": str(TENANT_ID),
                    "name": "Q3 SaaS Growth",
                    "industry": "manufacturing",
                    "target_audience": "Operations Managers at Indonesian manufacturers",
                    "pain_points": "manual inventory tracking, spreadsheet chaos, supply chain delays",
                    "value_proposition": "AI-powered ERP that cuts manual work by 80%",
                },
            )

    assert create_resp.status_code == 201, (
        f"Expected 201 campaign created, got {create_resp.status_code}: {create_resp.text}"
    )
    campaign_data = create_resp.json()
    campaign_id: str = campaign_data["id"]

    assert campaign_data["status"] == "draft", (
        f"Expected status 'draft', got '{campaign_data['status']}'"
    )
    assert campaign_data["tenant_id"] == str(TENANT_ID)
    assert campaign_data["name"] == "Q3 SaaS Growth"
    assert campaign_data["industry"] == "manufacturing"

    # =========================================================================
    # Phase B: Load agent-service agents AFTER marketing tables are registered.
    #          We only evict app modules and switch path — marketing_app,
    #          marketing_engine, mk_session_factory stay alive.
    # =========================================================================
    _set_active_service(AGENT_PATH)
    _evict_app_modules()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2 — Trigger CIS Agent → discover companies
    # ─────────────────────────────────────────────────────────────────────────
    from app.agents.cis_agent import CISAgent

    mock_companies = [
        {
            "company_name": "PT Maju Bersama",
            "industry": "manufacturing",
            "website": "https://majubersama.id",
            "phone": "+6281234567890",
            "employees": 200,
            "address": "Jakarta, Indonesia",
            "rating": 4.5,
        },
        {
            "company_name": "CV Nusantara Teknik",
            "industry": "manufacturing",
            "website": "https://nusantarateknik.id",
            "phone": "+6289876543210",
            "employees": 85,
            "address": "Surabaya, Indonesia",
            "rating": 4.2,
        },
        {
            "company_name": "PT Karya Mandiri",
            "industry": "manufacturing",
            "website": "https://karyamandiri.co.id",
            "phone": "+6281122334455",
            "employees": 150,
            "address": "Bandung, Indonesia",
            "rating": 4.0,
        },
        {
            "company_name": "PT Industri Sejahtera",
            "industry": "manufacturing",
            "website": "https://industrisejahtera.id",
            "phone": "+6287766554433",
            "employees": 320,
            "address": "Medan, Indonesia",
            "rating": 4.3,
        },
    ]

    cis_agent = CISAgent(tenant_id=TENANT_ID)

    with (
        patch(
            "app.tools.google_maps_tool.GoogleMapsTool.search_companies",
            new=AsyncMock(return_value=mock_companies),
        ),
        patch("app.agents.cis_agent.publish", side_effect=fake_publish),
    ):
        discovered_companies = await cis_agent.discover_companies(
            industry="manufacturing",
            location="Indonesia",
            limit=20,
        )

    # STEP 3 — Verify 3+ company targets discovered
    assert isinstance(discovered_companies, list), "Expected list of companies"
    assert len(discovered_companies) >= 3, (
        f"Expected 3+ companies discovered, got {len(discovered_companies)}"
    )
    assert "marketing.contacts.discovered" in events_by_topic, (
        f"Expected marketing.contacts.discovered event. Topics: {list(events_by_topic.keys())}"
    )
    discovery_event = events_by_topic["marketing.contacts.discovered"][0]
    assert discovery_event["data"]["count"] == len(discovered_companies)
    assert discovery_event["data"]["industry"] == "manufacturing"

    # Score relevance for each company
    pain_points = ["inventory management", "manual tracking", "supply chain"]
    scored_companies = []
    for company in discovered_companies:
        score = await cis_agent.score_relevance(company=company, pain_points=pain_points)
        scored_companies.append({**company, "relevance": score})
    assert all("relevance" in c for c in scored_companies)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4 — Content Planner Agent → generate strategy
    # ─────────────────────────────────────────────────────────────────────────
    from app.agents.content_planner_agent import ContentPlannerAgent

    planner_agent = ContentPlannerAgent(tenant_id=TENANT_ID)

    with patch("app.agents.content_planner_agent.publish", side_effect=fake_publish):
        strategy = await planner_agent.generate_strategy(
            campaign_id=campaign_id,
            industry="manufacturing",
            pain_points=["manual inventory tracking", "spreadsheet chaos", "supply chain delays"],
            value_proposition="AI-powered ERP that cuts manual work by 80%",
            target_audience="Operations Managers at Indonesian manufacturers",
        )

    assert strategy["status"] == "pending_approval", (
        f"Expected status 'pending_approval', got '{strategy['status']}'"
    )
    assert "blog_articles" in strategy
    assert "linkedin_posts" in strategy
    assert "ad_creatives" in strategy
    assert len(strategy["blog_articles"]) >= 1
    assert len(strategy["ad_creatives"]) >= 1

    assert "marketing.campaign.strategy.proposed" in events_by_topic, (
        f"Expected marketing.campaign.strategy.proposed. Topics: {list(events_by_topic.keys())}"
    )

    # STEP 5 — Marketing Manager approves strategy (HITL)
    approver_id = "manager-001"
    with patch("app.agents.content_planner_agent.publish", side_effect=fake_publish):
        approved_strategy = await planner_agent.approve_strategy(
            strategy=strategy,
            approver_id=approver_id,
        )

    assert approved_strategy["status"] == "approved", (
        f"Expected status 'approved', got '{approved_strategy['status']}'"
    )
    assert approved_strategy["approver_id"] == approver_id

    assert "marketing.campaign.strategy.approved" in events_by_topic, (
        f"Expected marketing.campaign.strategy.approved. Topics: {list(events_by_topic.keys())}"
    )
    approval_event = events_by_topic["marketing.campaign.strategy.approved"][0]
    assert approval_event["data"]["approver_id"] == approver_id
    assert approval_event["data"]["campaign_id"] == campaign_id

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6 — Blog Writer Agent → write article
    # ─────────────────────────────────────────────────────────────────────────
    from app.agents.blog_writer_agent import BlogWriterAgent

    blog_agent = BlogWriterAgent(tenant_id=TENANT_ID)
    first_article = approved_strategy["blog_articles"][0]

    with patch("app.agents.blog_writer_agent.publish", side_effect=fake_publish):
        article = await blog_agent.generate_article(
            title=first_article["title"],
            focus_keyword=first_article["focus_keyword"],
            outline=first_article["outline"],
            industry="manufacturing",
            value_proposition="AI-powered ERP that cuts manual work by 80%",
        )

    assert "content" in article
    assert len(article["content"]) > 0
    assert "word_count" in article
    assert article["word_count"] > 0
    assert article["status"] in ("draft", "published"), (
        f"Unexpected article status: {article['status']}"
    )

    assert "marketing.content.article.created" in events_by_topic, (
        f"Expected marketing.content.article.created. Topics: {list(events_by_topic.keys())}"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7 — Ads Orchestrator Agent → create ads (meta + google)
    # ─────────────────────────────────────────────────────────────────────────
    from app.agents.ads_orchestrator_agent import AdsOrchestratorAgent

    ads_agent = AdsOrchestratorAgent(tenant_id=TENANT_ID)
    headline = "Fix Manual Inventory Tracking Today"
    body = "AI-powered ERP that cuts manual work by 80%. Designed for Indonesian manufacturers."

    with patch("app.agents.ads_orchestrator_agent.publish", side_effect=fake_publish):
        meta_ad = await ads_agent.create_meta_campaign(
            campaign_id=campaign_id,
            headline=headline,
            body=body,
            daily_budget_usd=20.0,
            target_interests=["manufacturing", "supply chain", "ERP"],
        )
        google_ad = await ads_agent.create_google_campaign(
            campaign_id=campaign_id,
            headline=headline,
            body=body,
            daily_budget_usd=30.0,
            keywords=["inventory management software", "ERP Indonesia", "manufacturing ERP"],
        )

    assert meta_ad["platform"] == "meta"
    assert meta_ad["status"] == "ready_to_launch"
    assert meta_ad["campaign_id"] == campaign_id
    assert meta_ad["daily_budget_usd"] == 20.0

    assert google_ad["platform"] == "google"
    assert google_ad["status"] == "ready_to_launch"
    assert google_ad["campaign_id"] == campaign_id
    assert google_ad["daily_budget_usd"] == 30.0

    assert "marketing.ads.meta.created" in events_by_topic, (
        f"Expected marketing.ads.meta.created. Topics: {list(events_by_topic.keys())}"
    )
    assert "marketing.ads.google.created" in events_by_topic, (
        f"Expected marketing.ads.google.created. Topics: {list(events_by_topic.keys())}"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8 — Landing Page Agent → generate page → return page_url
    # ─────────────────────────────────────────────────────────────────────────
    from app.agents.landing_page_agent import LandingPageAgent

    lp_agent = LandingPageAgent(tenant_id=TENANT_ID, base_url="https://app.meetsin.id")

    with patch("app.agents.landing_page_agent.publish", side_effect=fake_publish):
        landing_page = await lp_agent.generate_page(
            campaign_id=campaign_id,
            headline="Transform Your Manufacturing Operations",
            subheadline="AI-powered ERP that eliminates manual inventory tracking",
            value_proposition="AI-powered ERP that cuts manual work by 80%",
            benefits=[
                "80% reduction in manual data entry",
                "Real-time inventory visibility",
                "Automated reorder point alerts",
                "Seamless supplier integration",
            ],
            cta_text="Get Free Demo",
        )

    assert "html" in landing_page
    assert len(landing_page["html"]) > 0
    assert "page_url" in landing_page
    page_url: str = landing_page["page_url"]
    assert page_url.startswith("https://app.meetsin.id/lp/"), (
        f"Expected page_url to start with base_url/lp/, got: {page_url}"
    )
    assert landing_page["status"] == "generated"
    assert "form_fields" in landing_page
    assert len(landing_page["form_fields"]) >= 4  # name, email, phone, company

    assert "marketing.landing_page.generated" in events_by_topic, (
        f"Expected marketing.landing_page.generated. Topics: {list(events_by_topic.keys())}"
    )
    lp_event = events_by_topic["marketing.landing_page.generated"][0]
    assert lp_event["data"]["page_url"] == page_url

    # =========================================================================
    # Phase C: Submit contact form via the SAME marketing_app loaded in Phase A.
    #          We saved a direct reference to _mk_campaigns_router before the
    #          path switch, so we can patch it without any re-import.
    # =========================================================================

    contact_name = "Budi Santoso"
    contact_email = "budi@majubersama.id"
    contact_phone = "+6281234567890"
    contact_company = "PT Maju Bersama"

    form_events: list[tuple[str, dict]] = []

    async def capture_form_publish(topic: str, event_type: str, tenant_id: str, data: dict) -> None:
        form_events.append((topic, {"type": event_type, "data": data}))
        await fake_publish(topic, event_type, tenant_id, data)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 9 — Submit contact form
    # ─────────────────────────────────────────────────────────────────────────
    # Patch the `publish` function on the already-imported campaigns router.
    with patch.object(_mk_campaigns_router, "publish", side_effect=capture_form_publish):
        async with AsyncClient(
            transport=ASGITransport(app=marketing_app), base_url="http://test"
        ) as mc2:
            form_resp = await mc2.post(
                f"/campaigns/{campaign_id}/landing-page/form",
                json={
                    "contact_name": contact_name,
                    "contact_email": contact_email,
                    "contact_phone": contact_phone,
                    "company": contact_company,
                },
            )

    marketing_app.dependency_overrides.clear()
    # Note: marketing_engine is a singleton — do NOT dispose it here.

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 10 — Verify marketing.contact.interested published
    # ─────────────────────────────────────────────────────────────────────────
    assert form_resp.status_code == 202, (
        f"Expected 202 form accepted, got {form_resp.status_code}: {form_resp.text}"
    )
    form_resp_data = form_resp.json()
    assert form_resp_data["status"] == "accepted"
    assert form_resp_data["campaign_id"] == campaign_id

    contact_topics = [t for t, _ in form_events]
    assert "marketing.contact.interested" in contact_topics, (
        f"Expected 'marketing.contact.interested', got: {contact_topics}"
    )

    contact_interested_event = next(
        e for t, e in form_events if t == "marketing.contact.interested"
    )
    assert contact_interested_event["type"] == "marketing.contact.interested"
    assert contact_interested_event["data"]["contact_email"] == contact_email
    assert contact_interested_event["data"]["campaign_id"] == campaign_id
    assert "pain_point_match" in contact_interested_event["data"]

    pain_point_match: float = float(contact_interested_event["data"]["pain_point_match"])
    assert 0.0 <= pain_point_match <= 1.0, (
        f"pain_point_match should be [0, 1], got: {pain_point_match}"
    )

    # =========================================================================
    # Phase D: CRM consumer — bootstrap once, process the event, verify DB
    # =========================================================================
    await _bootstrap_crm()

    Contact = _crm_Contact
    Opportunity = _crm_Opportunity
    handle_contact_interested_event = _crm_handle_event

    crm_session_factory = async_sessionmaker(_crm_engine, expire_on_commit=False)

    # Clear any state left from earlier test runs sharing the CRM engine
    async with crm_session_factory() as cleanup_session:
        await cleanup_session.execute(text("DELETE FROM opportunities"))
        await cleanup_session.execute(text("DELETE FROM contacts"))
        await cleanup_session.commit()

    crm_cloud_event = {
        "specversion": "1.0",
        "type": "marketing.contact.interested",
        "source": "marketing-service",
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat(),
        "datacontenttype": "application/json",
        "tenantid": str(TENANT_ID),
        "data": {
            "tenant_id": str(TENANT_ID),
            "campaign_id": campaign_id,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "company": contact_company,
            "pain_point_match": pain_point_match,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 11 — CRM consumer creates Contact + Opportunity
    # ─────────────────────────────────────────────────────────────────────────
    async with crm_session_factory() as crm_session:
        with patch("app.events.publish", new_callable=AsyncMock):
            await handle_contact_interested_event(crm_session, crm_cloud_event)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 12 — Verify opportunity visible via DB query (simulates GET endpoint)
    # ─────────────────────────────────────────────────────────────────────────
    async with crm_session_factory() as verify_session:
        contacts_result = await verify_session.execute(
            select(Contact).where(Contact.tenant_id == TENANT_ID)
        )
        contacts = contacts_result.scalars().all()

        opps_result = await verify_session.execute(
            select(Opportunity).where(Opportunity.tenant_id == TENANT_ID)
        )
        opportunities = opps_result.scalars().all()

    # Verify Contact
    assert len(contacts) >= 1, f"Expected at least 1 contact, got {len(contacts)}"
    contact_record = contacts[0]
    assert contact_record.email == contact_email, (
        f"Expected email {contact_email}, got {contact_record.email}"
    )
    assert contact_record.first_name == "Budi", (
        f"Expected first_name 'Budi', got '{contact_record.first_name}'"
    )
    assert contact_record.last_name == "Santoso", (
        f"Expected last_name 'Santoso', got '{contact_record.last_name}'"
    )
    assert contact_record.company == contact_company, (
        f"Expected company '{contact_company}', got '{contact_record.company}'"
    )

    # Verify Opportunity linked to Contact
    assert len(opportunities) >= 1, f"Expected at least 1 opportunity, got {len(opportunities)}"
    opportunity = opportunities[0]
    assert opportunity.contact_id == contact_record.id
    assert contact_company in opportunity.title, (
        f"Expected company name in opportunity title, got: {opportunity.title}"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 13 — Verify opportunity value = pain_point_match * 10_000
    # ─────────────────────────────────────────────────────────────────────────
    expected_value = pain_point_match * 10_000
    assert abs(opportunity.value - expected_value) < 0.01, (
        f"Expected opportunity value {expected_value:.2f}, got {opportunity.value:.2f}"
    )
    assert opportunity.stage.value == "prospect", (
        f"Expected stage 'prospect', got '{opportunity.stage.value}'"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 14 — Verify full event chain completeness
    # ─────────────────────────────────────────────────────────────────────────
    required_event_topics = [
        "marketing.contacts.discovered",        # CIS discovers companies
        "marketing.campaign.strategy.proposed", # Content planner proposes
        "marketing.campaign.strategy.approved", # Manager approves (HITL)
        "marketing.content.article.created",    # Blog writer publishes
        "marketing.ads.meta.created",           # Meta ad created
        "marketing.ads.google.created",         # Google ad created
        "marketing.landing_page.generated",     # Landing page deployed
        "marketing.contact.interested",         # Contact form submitted
    ]

    missing_topics = [t for t in required_event_topics if t not in events_by_topic]
    assert not missing_topics, (
        f"Missing Kafka events: {missing_topics}\n"
        f"Published topics: {sorted(events_by_topic.keys())}"
    )

    total_events = len(event_log)
    assert total_events >= 8, (
        f"Expected at least 8 pipeline events, got {total_events}\n"
        f"Published: {[e['topic'] for e in event_log]}"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Final summary assertions
    # ─────────────────────────────────────────────────────────────────────────

    # 1. Campaign created with status "draft"
    assert campaign_data["status"] == "draft"

    # 2. 3+ company targets discovered
    assert len(discovered_companies) >= 3

    # 3. Strategy approved (HITL complete)
    assert approved_strategy["status"] == "approved"

    # 4. Blog article created
    assert article["word_count"] > 0

    # 5. Ad campaigns created (meta + google = 2 platforms)
    assert len(events_by_topic.get("marketing.ads.meta.created", [])) >= 1
    assert len(events_by_topic.get("marketing.ads.google.created", [])) >= 1

    # 6. Landing page deployed with a URL
    assert page_url.startswith("https://")

    # 7. Contact form submitted → 202 Accepted
    assert form_resp.status_code == 202

    # 8. Opportunity created in CRM with correct value
    assert len(opportunities) >= 1
    assert abs(opportunities[0].value - expected_value) < 0.01
