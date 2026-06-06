"""Company Intelligence Scout (CIS) Agent.

Discovers target companies via Google Maps, validates WhatsApp contacts,
and scores company relevance against campaign pain points.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.events import publish
from app.tools.google_maps_tool import GoogleMapsTool
from app.tools.baileys_whatsapp_tool import BaileysWhatsAppTool

logger = logging.getLogger(__name__)

# Keywords that indicate an industry match for scoring
_INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "manufacturing": ["produksi", "pabrik", "manufaktur", "supply chain", "inventory"],
    "retail": ["toko", "retail", "ecommerce", "penjualan", "stok"],
    "services": ["jasa", "konsultan", "layanan", "support"],
    "food": ["makanan", "restoran", "catering", "kuliner"],
}


class CISAgent:
    """Company Intelligence Scout autonomous agent."""

    def __init__(
        self,
        tenant_id: uuid.UUID,
        maps_api_key: str = "",
        whatsapp_sidecar_url: str = "http://localhost:3001",
    ) -> None:
        self.tenant_id = tenant_id
        self.maps_tool = GoogleMapsTool(api_key=maps_api_key)
        self.wa_tool = BaileysWhatsAppTool(sidecar_url=whatsapp_sidecar_url)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def discover_companies(
        self,
        industry: str,
        location: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Use Google Maps to discover companies in the target industry/location."""
        logger.info(
            "CISAgent.discover_companies tenant=%s industry=%s location=%s",
            self.tenant_id,
            industry,
            location,
        )
        results = await self.maps_tool.search_companies(
            industry=industry, location=location, limit=limit
        )
        await publish(
            "marketing.contacts.discovered",
            "marketing.contacts.discovered",
            str(self.tenant_id),
            {
                "tenant_id": str(self.tenant_id),
                "industry": industry,
                "location": location,
                "count": len(results),
            },
        )
        return results

    async def validate_whatsapp_contact(self, phone: str) -> dict[str, Any]:
        """Validate that ``phone`` has an active WhatsApp account."""
        logger.info(
            "CISAgent.validate_whatsapp_contact tenant=%s phone=%s",
            self.tenant_id,
            phone,
        )
        result = await self.wa_tool.validate_number(phone=phone)
        return result

    async def score_relevance(
        self,
        company: dict[str, Any],
        pain_points: list[str],
    ) -> dict[str, Any]:
        """Score how relevant ``company`` is to the campaign ``pain_points``.

        Returns a dict with:
        - score (int 0-100)
        - reasons (list[str])
        """
        score = 0
        reasons: list[str] = []

        industry = (company.get("industry") or "").lower()
        employees = company.get("employees", 0)

        # Industry match: up to 50 points
        matched_keywords = _INDUSTRY_KEYWORDS.get(industry, [])
        for pain in pain_points:
            pain_lower = pain.lower()
            if any(kw in pain_lower for kw in matched_keywords) or industry in pain_lower:
                score += 10
                reasons.append(f"Industry '{industry}' matches pain point '{pain}'")
                if score >= 50:
                    break

        # Company size signal: up to 30 points
        if employees >= 100:
            score += 30
            reasons.append(f"Mid-to-large company ({employees} employees) — higher budget likelihood")
        elif employees >= 20:
            score += 15
            reasons.append(f"Small-to-mid company ({employees} employees)")

        # Website presence: up to 20 points
        if company.get("website"):
            score += 20
            reasons.append("Has a corporate website — digital-ready")

        score = min(score, 100)

        if not reasons:
            reasons.append("No strong relevance signals found")

        return {"score": score, "reasons": reasons}
