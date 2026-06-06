"""CRM Agent — Extended.

Extends the base CRM agent with marketing-specific capabilities:
personalised WhatsApp message generation and engagement-based lead scoring.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.events import publish
from app.tools.baileys_whatsapp_tool import BaileysWhatsAppTool

logger = logging.getLogger(__name__)

# Engagement score weights
_WEIGHTS: dict[str, int] = {
    "opened_email": 5,
    "clicked_link": 10,
    "visited_landing_page": 15,
    "filled_contact_form": 30,
    "attended_demo": 40,
    "replied_whatsapp": 20,
    "downloaded_asset": 10,
}

# Lead grade thresholds
_GRADE_THRESHOLDS = [
    (80, "A"),
    (60, "B"),
    (40, "C"),
    (20, "D"),
    (0,  "F"),
]


class CRMAgentExtended:
    """Marketing-aware CRM agent for lead personalisation and scoring."""

    def __init__(
        self,
        tenant_id: uuid.UUID,
        whatsapp_sidecar_url: str = "http://localhost:3001",
    ) -> None:
        self.tenant_id = tenant_id
        self.wa_tool = BaileysWhatsAppTool(sidecar_url=whatsapp_sidecar_url)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def personalize_message(
        self,
        contact: dict[str, Any],
        campaign: dict[str, Any],
        template: str,
    ) -> dict[str, Any]:
        """Generate a personalised WhatsApp message for ``contact``.

        ``template`` may contain placeholders:
        - {name}, {company}, {industry}, {pain_point}, {cta_url}

        Returns a dict with:
        - contact_id (str)
        - whatsapp_id (str | None)
        - personalized_message (str)
        - template_used (str)
        - variables (dict)
        """
        logger.info(
            "CRMAgentExtended.personalize_message tenant=%s contact=%s",
            self.tenant_id,
            contact.get("id"),
        )

        pain_point = ""
        if campaign.get("pain_points"):
            pain_point = campaign["pain_points"][0]

        cta_url = (
            f"https://app.meetsin.id/lp/{campaign.get('campaign_id', 'demo')}"
            f"?ref={contact.get('id', 'unknown')}"
        )

        variables = {
            "name": contact.get("name", "there"),
            "company": contact.get("company_name", "your company"),
            "industry": campaign.get("industry", "your industry"),
            "pain_point": pain_point,
            "cta_url": cta_url,
        }

        personalized = template.format(**variables)

        return {
            "contact_id": str(contact.get("id", "")),
            "whatsapp_id": contact.get("whatsapp_id"),
            "personalized_message": personalized,
            "template_used": template,
            "variables": variables,
        }

    async def score_lead(
        self,
        contact: dict[str, Any],
        engagement_events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Score a lead based on their engagement history.

        ``engagement_events`` is a list of dicts with keys:
        - event_type (str)  — one of the keys in ``_WEIGHTS``
        - timestamp (str)
        - metadata (dict, optional)

        Returns a dict with:
        - contact_id (str)
        - score (int 0-100)
        - grade ("A" | "B" | "C" | "D" | "F")
        - breakdown (dict)  — per-event-type contribution
        - recommendation (str)
        """
        logger.info(
            "CRMAgentExtended.score_lead tenant=%s contact=%s events=%d",
            self.tenant_id,
            contact.get("id"),
            len(engagement_events),
        )

        breakdown: dict[str, int] = {}
        raw_score = 0

        for event in engagement_events:
            etype = event.get("event_type", "")
            weight = _WEIGHTS.get(etype, 0)
            breakdown[etype] = breakdown.get(etype, 0) + weight
            raw_score += weight

        score = min(raw_score, 100)

        grade = "F"
        for threshold, letter in _GRADE_THRESHOLDS:
            if score >= threshold:
                grade = letter
                break

        recommendation = self._get_recommendation(grade)

        result: dict[str, Any] = {
            "contact_id": str(contact.get("id", "")),
            "score": score,
            "grade": grade,
            "breakdown": breakdown,
            "recommendation": recommendation,
        }

        await publish(
            "marketing.lead.scored",
            "marketing.lead.scored",
            str(self.tenant_id),
            {
                "tenant_id": str(self.tenant_id),
                "contact_id": str(contact.get("id", "")),
                "score": score,
                "grade": grade,
            },
        )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_recommendation(grade: str) -> str:
        recommendations = {
            "A": "Hot lead — assign to sales immediately for personal outreach.",
            "B": "Warm lead — send targeted follow-up sequence + demo invite.",
            "C": "Nurture lead — continue educational content drip campaign.",
            "D": "Cold lead — low-frequency nurture; re-evaluate in 30 days.",
            "F": "Unengaged — flag for re-qualification or archive.",
        }
        return recommendations.get(grade, "Review manually.")
