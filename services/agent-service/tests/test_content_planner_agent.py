# tests/test_content_planner_agent.py
"""Tests for Content Planner Agent."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

TENANT_A = uuid.uuid4()
CAMPAIGN_ID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_strategy_generation():
    """Content Planner generates a strategy matrix with blog, LinkedIn, and ad content."""
    from app.agents.content_planner_agent import ContentPlannerAgent

    agent = ContentPlannerAgent(tenant_id=TENANT_A)

    with patch("app.events.publish", new=AsyncMock()):
        strategy = await agent.generate_strategy(
            campaign_id=CAMPAIGN_ID,
            industry="manufacturing",
            pain_points=["inventory management", "manual tracking", "supply chain"],
            value_proposition="AI-powered ERP that reduces stock-outs by 40%",
            target_audience="Operations Managers at mid-size manufacturers",
        )

    assert strategy["campaign_id"] == CAMPAIGN_ID
    assert strategy["industry"] == "manufacturing"
    assert strategy["status"] == "pending_approval"

    # Should produce blog articles
    assert "blog_articles" in strategy
    assert isinstance(strategy["blog_articles"], list)
    assert len(strategy["blog_articles"]) >= 1
    article = strategy["blog_articles"][0]
    assert "title" in article
    assert "focus_keyword" in article
    assert "outline" in article

    # Should produce LinkedIn posts
    assert "linkedin_posts" in strategy
    assert isinstance(strategy["linkedin_posts"], list)
    assert len(strategy["linkedin_posts"]) >= 1
    post = strategy["linkedin_posts"][0]
    assert "copy" in post
    assert "hashtags" in post

    # Should produce ad creatives
    assert "ad_creatives" in strategy
    assert isinstance(strategy["ad_creatives"], list)
    assert len(strategy["ad_creatives"]) >= 1
    creative = strategy["ad_creatives"][0]
    assert "headline" in creative
    assert "platform" in creative


@pytest.mark.asyncio
async def test_hitl_approval():
    """Strategy status changes to 'approved' after Marketing Manager approves."""
    from app.agents.content_planner_agent import ContentPlannerAgent

    agent = ContentPlannerAgent(tenant_id=TENANT_A)
    approver_id = str(uuid.uuid4())

    with patch("app.events.publish", new=AsyncMock()):
        strategy = await agent.generate_strategy(
            campaign_id=CAMPAIGN_ID,
            industry="retail",
            pain_points=["slow checkout", "inventory shrinkage"],
            value_proposition="Real-time inventory visibility across all channels",
            target_audience="Retail store managers",
        )

        assert strategy["status"] == "pending_approval"

        approved = await agent.approve_strategy(
            strategy=strategy,
            approver_id=approver_id,
        )

    assert approved["status"] == "approved"
    assert approved["approver_id"] == approver_id
    assert approved["campaign_id"] == CAMPAIGN_ID
