# tests/test_crm_agent_extended.py
"""Tests for CRM Agent (Extended)."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

TENANT_A = uuid.uuid4()
CONTACT_ID = str(uuid.uuid4())
CAMPAIGN_ID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_message_personalization():
    """CRM Extended Agent personalises WhatsApp message template with contact data."""
    from app.agents.crm_agent_extended import CRMAgentExtended

    agent = CRMAgentExtended(tenant_id=TENANT_A)

    contact = {
        "id": CONTACT_ID,
        "name": "Budi Santoso",
        "company_name": "PT Maju Bersama",
        "whatsapp_id": "6281234567890@s.whatsapp.net",
    }
    campaign = {
        "campaign_id": CAMPAIGN_ID,
        "industry": "manufacturing",
        "pain_points": ["inventory management", "manual tracking"],
    }
    template = (
        "Halo {name}, saya dari Meetsin.Id. "
        "Banyak perusahaan {industry} seperti {company} mengalami masalah {pain_point}. "
        "Kami punya solusinya — cek di sini: {cta_url}"
    )

    with patch("app.events.publish", new=AsyncMock()):
        result = await agent.personalize_message(
            contact=contact,
            campaign=campaign,
            template=template,
        )

    assert result["contact_id"] == CONTACT_ID
    assert result["whatsapp_id"] == "6281234567890@s.whatsapp.net"
    assert "personalized_message" in result

    msg = result["personalized_message"]
    assert "Budi Santoso" in msg
    assert "manufacturing" in msg
    assert "PT Maju Bersama" in msg
    assert "inventory management" in msg
    assert "https://app.meetsin.id/lp/" in msg

    assert "template_used" in result
    assert "variables" in result
    assert result["variables"]["name"] == "Budi Santoso"


@pytest.mark.asyncio
async def test_lead_scoring():
    """CRM Extended Agent scores leads correctly based on engagement events."""
    from app.agents.crm_agent_extended import CRMAgentExtended

    agent = CRMAgentExtended(tenant_id=TENANT_A)

    contact = {"id": CONTACT_ID, "name": "Budi Santoso"}

    engagement_events = [
        {"event_type": "opened_email", "timestamp": "2026-06-01T08:00:00Z"},
        {"event_type": "clicked_link", "timestamp": "2026-06-01T08:05:00Z"},
        {"event_type": "visited_landing_page", "timestamp": "2026-06-01T08:07:00Z"},
        {"event_type": "filled_contact_form", "timestamp": "2026-06-01T08:10:00Z"},
    ]

    with patch("app.events.publish", new=AsyncMock()):
        result = await agent.score_lead(
            contact=contact,
            engagement_events=engagement_events,
        )

    assert result["contact_id"] == CONTACT_ID
    assert "score" in result
    assert isinstance(result["score"], int)
    assert 0 <= result["score"] <= 100

    # opened(5) + clicked(10) + visited_lp(15) + filled_form(30) = 60 → grade B
    assert result["score"] == 60
    assert result["grade"] == "B"

    assert "breakdown" in result
    assert result["breakdown"]["opened_email"] == 5
    assert result["breakdown"]["filled_contact_form"] == 30

    assert "recommendation" in result
    assert isinstance(result["recommendation"], str)
    assert len(result["recommendation"]) > 0
