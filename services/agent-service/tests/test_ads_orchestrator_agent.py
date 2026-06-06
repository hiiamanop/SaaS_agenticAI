# tests/test_ads_orchestrator_agent.py
"""Tests for Ads Orchestrator Agent."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

TENANT_A = uuid.uuid4()
CAMPAIGN_ID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_ad_creation_meta():
    """Ads Orchestrator creates a Meta (Facebook/Instagram) campaign correctly."""
    from app.agents.ads_orchestrator_agent import AdsOrchestratorAgent

    agent = AdsOrchestratorAgent(tenant_id=TENANT_A)

    with patch("app.events.publish", new=AsyncMock()):
        campaign = await agent.create_meta_campaign(
            campaign_id=CAMPAIGN_ID,
            headline="Fix Inventory Problems Today",
            body="AI-powered ERP designed for manufacturers. Reduce stock-outs by 40%.",
            daily_budget_usd=25.0,
            target_interests=["manufacturing", "supply chain", "ERP software"],
        )

    assert campaign["campaign_id"] == CAMPAIGN_ID
    assert campaign["platform"] == "meta"
    assert campaign["daily_budget_usd"] == 25.0
    assert campaign["status"] == "ready_to_launch"

    # Creative
    assert "creative" in campaign
    creative = campaign["creative"]
    assert creative["platform"] == "meta"
    assert len(creative["headline"]) <= 40  # Meta headline limit
    assert "body" in creative
    assert "cta" in creative

    # Targeting
    assert "targeting" in campaign
    targeting = campaign["targeting"]
    assert targeting["platform"] == "meta"
    assert "interests" in targeting
    assert "manufacturing" in targeting["interests"]

    # Tracking
    assert "tracking" in campaign
    tracking = campaign["tracking"]
    assert tracking["utm_source"] == "meta"
    assert tracking["utm_campaign"] == CAMPAIGN_ID


@pytest.mark.asyncio
async def test_ad_creation_google():
    """Ads Orchestrator creates a Google Search campaign correctly."""
    from app.agents.ads_orchestrator_agent import AdsOrchestratorAgent

    agent = AdsOrchestratorAgent(tenant_id=TENANT_A)

    with patch("app.events.publish", new=AsyncMock()):
        campaign = await agent.create_google_campaign(
            campaign_id=CAMPAIGN_ID,
            headline="ERP for Manufacturers",
            body="Reduce stock-outs by 40% with AI-powered inventory management.",
            daily_budget_usd=40.0,
            keywords=["manufacturing ERP", "inventory management software", "supply chain system"],
        )

    assert campaign["campaign_id"] == CAMPAIGN_ID
    assert campaign["platform"] == "google"
    assert campaign["daily_budget_usd"] == 40.0
    assert campaign["status"] == "ready_to_launch"

    # Creative checks
    creative = campaign["creative"]
    assert creative["platform"] == "google"
    assert len(creative["headline"]) <= 30  # Google headline limit
    assert "format" in creative

    # Targeting checks
    targeting = campaign["targeting"]
    assert targeting["platform"] == "google"
    assert "keywords" in targeting
    assert "manufacturing ERP" in targeting["keywords"]
    assert targeting["geo"] == "ID"

    # Tracking
    assert campaign["tracking"]["utm_source"] == "google"
    assert campaign["tracking"]["utm_medium"] == "paid"
