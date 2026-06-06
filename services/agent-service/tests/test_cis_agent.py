# tests/test_cis_agent.py
"""Tests for Company Intelligence Scout (CIS) agent."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

TENANT_A = uuid.uuid4()


@pytest.mark.asyncio
async def test_discover_companies():
    """CIS agent discovers companies using Google Maps tool."""
    from app.agents.cis_agent import CISAgent

    agent = CISAgent(tenant_id=TENANT_A)

    with patch(
        "app.tools.google_maps_tool.GoogleMapsTool.search_companies",
        new=AsyncMock(
            return_value=[
                {
                    "company_name": "PT Maju Bersama",
                    "industry": "manufacturing",
                    "website": "https://majubersama.id",
                    "phone": "+6281234567890",
                }
            ]
        ),
    ):
        results = await agent.discover_companies(
            industry="manufacturing",
            location="Jakarta",
            limit=10,
        )

    assert isinstance(results, list)
    assert len(results) >= 1
    assert results[0]["company_name"] == "PT Maju Bersama"
    assert results[0]["industry"] == "manufacturing"


@pytest.mark.asyncio
async def test_validate_whatsapp():
    """CIS agent validates WhatsApp contacts via Baileys tool."""
    from app.agents.cis_agent import CISAgent

    agent = CISAgent(tenant_id=TENANT_A)

    with patch(
        "app.tools.baileys_whatsapp_tool.BaileysWhatsAppTool.validate_number",
        new=AsyncMock(
            return_value={
                "phone": "+6281234567890",
                "is_valid": True,
                "whatsapp_id": "6281234567890@s.whatsapp.net",
                "name": "John Doe",
            }
        ),
    ):
        result = await agent.validate_whatsapp_contact(phone="+6281234567890")

    assert result["is_valid"] is True
    assert "whatsapp_id" in result
    assert result["phone"] == "+6281234567890"


@pytest.mark.asyncio
async def test_score_relevance():
    """CIS agent scores company relevance against campaign pain points."""
    from app.agents.cis_agent import CISAgent

    agent = CISAgent(tenant_id=TENANT_A)

    company = {
        "company_name": "PT Maju Bersama",
        "industry": "manufacturing",
        "website": "https://majubersama.id",
        "employees": 150,
    }
    pain_points = ["inventory management", "manual tracking", "supply chain"]

    score = await agent.score_relevance(company=company, pain_points=pain_points)

    assert isinstance(score, dict)
    assert "score" in score
    assert "reasons" in score
    assert 0 <= score["score"] <= 100
    assert isinstance(score["reasons"], list)
