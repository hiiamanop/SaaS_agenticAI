# tests/test_landing_page_agent.py
"""Tests for Landing Page Agent."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

TENANT_A = uuid.uuid4()
CAMPAIGN_ID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_page_generation():
    """Landing Page Agent generates a valid HTML page with correct structure."""
    from app.agents.landing_page_agent import LandingPageAgent

    agent = LandingPageAgent(tenant_id=TENANT_A, base_url="https://app.meetsin.id")

    with patch("app.events.publish", new=AsyncMock()):
        page = await agent.generate_page(
            campaign_id=CAMPAIGN_ID,
            headline="Transform Your Manufacturing Operations",
            subheadline="AI-powered ERP that reduces stock-outs by 40%",
            value_proposition="Real-time inventory visibility for mid-size manufacturers",
            benefits=[
                "Reduce stock-outs by 40%",
                "Cut manual data entry by 80%",
                "Real-time supply chain visibility",
                "Integrates with existing systems",
            ],
            cta_text="Get Free Demo",
        )

    assert page["campaign_id"] == CAMPAIGN_ID
    assert page["status"] == "generated"

    # HTML structure
    assert "html" in page
    html = page["html"]
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
    assert "Transform Your Manufacturing Operations" in html
    assert "AI-powered ERP" in html
    assert "Get Free Demo" in html
    assert "<form" in html
    assert "</html>" in html

    # CSS
    assert "css" in page
    assert len(page["css"]) > 0

    # Form fields
    assert "form_fields" in page
    assert isinstance(page["form_fields"], list)
    assert len(page["form_fields"]) > 0

    # Page URL
    assert "page_url" in page
    assert page["page_url"].startswith("https://app.meetsin.id/lp/")


@pytest.mark.asyncio
async def test_form_creation():
    """Landing Page Agent generates a standalone contact form with correct fields."""
    from app.agents.landing_page_agent import LandingPageAgent

    agent = LandingPageAgent(tenant_id=TENANT_A)

    custom_fields = [
        {"name": "full_name", "label": "Full Name", "type": "text", "required": True},
        {"name": "email", "label": "Work Email", "type": "email", "required": True},
        {"name": "phone", "label": "WhatsApp Number", "type": "tel", "required": True},
        {"name": "company", "label": "Company Name", "type": "text", "required": True},
    ]

    form = await agent.generate_contact_form(
        campaign_id=CAMPAIGN_ID,
        fields=custom_fields,
        submit_endpoint="/api/leads",
    )

    assert form["campaign_id"] == CAMPAIGN_ID
    assert "form_html" in form
    assert "fields" in form
    assert "submit_endpoint" in form

    form_html = form["form_html"]
    assert "<form" in form_html
    assert 'method="POST"' in form_html
    assert 'action="/api/leads"' in form_html
    assert f'data-campaign-id="{CAMPAIGN_ID}"' in form_html

    # All field names appear in the HTML
    for field in custom_fields:
        assert field["name"] in form_html
        assert field["label"] in form_html

    # Hidden campaign_id field
    assert f'value="{CAMPAIGN_ID}"' in form_html

    # Submit button
    assert 'type="submit"' in form_html

    assert form["submit_endpoint"] == "/api/leads"
    assert len(form["fields"]) == len(custom_fields)
