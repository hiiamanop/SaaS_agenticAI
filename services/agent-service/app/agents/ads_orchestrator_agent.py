"""Ads Orchestrator Agent.

Creates ad creatives and targeting configurations for Meta, Google, and
LinkedIn, sets daily budgets, and publishes campaign launch events.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from app.events import publish

logger = logging.getLogger(__name__)

Platform = Literal["meta", "google", "linkedin"]

_PLATFORM_SPECS: dict[str, dict[str, Any]] = {
    "meta": {
        "max_headline_chars": 40,
        "max_body_chars": 125,
        "supported_formats": ["image", "video", "carousel"],
        "cta_options": ["LEARN_MORE", "GET_QUOTE", "CONTACT_US", "SIGN_UP"],
    },
    "google": {
        "max_headline_chars": 30,
        "max_body_chars": 90,
        "supported_formats": ["responsive_search", "display"],
        "cta_options": ["Learn More", "Get a Quote", "Contact Us"],
    },
    "linkedin": {
        "max_headline_chars": 70,
        "max_body_chars": 600,
        "supported_formats": ["single_image", "document", "video"],
        "cta_options": ["Learn More", "Register", "Download"],
    },
}


class AdsOrchestratorAgent:
    """Multi-platform ad campaign orchestrator."""

    def __init__(self, tenant_id: uuid.UUID) -> None:
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def create_ad_campaign(
        self,
        campaign_id: str,
        platform: Platform,
        headline: str,
        body: str,
        cta: str,
        daily_budget_usd: float,
        targeting: dict[str, Any],
        creative_assets: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create an ad campaign for the specified ``platform``.

        Returns a dict with:
        - campaign_id, platform
        - creative (dict)  — platform-specific creative JSON
        - targeting (dict)
        - daily_budget_usd
        - tracking (dict)  — UTM params + pixel config
        - status: "draft" | "ready_to_launch"
        """
        logger.info(
            "AdsOrchestratorAgent.create_ad_campaign tenant=%s platform=%s",
            self.tenant_id,
            platform,
        )

        spec = _PLATFORM_SPECS.get(platform, {})

        # Truncate to platform limits
        headline_limit = spec.get("max_headline_chars", 100)
        body_limit = spec.get("max_body_chars", 500)
        headline_trimmed = headline[:headline_limit]
        body_trimmed = body[:body_limit]

        creative = self._build_creative(
            platform=platform,
            headline=headline_trimmed,
            body=body_trimmed,
            cta=cta,
            assets=creative_assets or [],
            spec=spec,
        )

        tracking = self._build_tracking(campaign_id=campaign_id, platform=platform)

        ad_campaign: dict[str, Any] = {
            "campaign_id": campaign_id,
            "platform": platform,
            "creative": creative,
            "targeting": targeting,
            "daily_budget_usd": daily_budget_usd,
            "tracking": tracking,
            "status": "ready_to_launch",
        }

        await publish(
            f"marketing.ads.{platform}.created",
            f"marketing.ads.{platform}.created",
            str(self.tenant_id),
            {
                "tenant_id": str(self.tenant_id),
                "campaign_id": campaign_id,
                "platform": platform,
                "daily_budget_usd": daily_budget_usd,
            },
        )
        return ad_campaign

    async def create_meta_campaign(
        self,
        campaign_id: str,
        headline: str,
        body: str,
        daily_budget_usd: float = 20.0,
        target_interests: list[str] | None = None,
    ) -> dict[str, Any]:
        """Convenience wrapper for Meta (Facebook/Instagram) campaigns."""
        targeting = {
            "platform": "meta",
            "interests": target_interests or [],
            "age_min": 25,
            "age_max": 55,
            "geo": "ID",
        }
        return await self.create_ad_campaign(
            campaign_id=campaign_id,
            platform="meta",
            headline=headline,
            body=body,
            cta="LEARN_MORE",
            daily_budget_usd=daily_budget_usd,
            targeting=targeting,
        )

    async def create_google_campaign(
        self,
        campaign_id: str,
        headline: str,
        body: str,
        daily_budget_usd: float = 30.0,
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """Convenience wrapper for Google Search / Display campaigns."""
        targeting = {
            "platform": "google",
            "keywords": keywords or [],
            "match_type": "broad",
            "geo": "ID",
            "language": "id",
        }
        return await self.create_ad_campaign(
            campaign_id=campaign_id,
            platform="google",
            headline=headline,
            body=body,
            cta="Learn More",
            daily_budget_usd=daily_budget_usd,
            targeting=targeting,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_creative(
        platform: str,
        headline: str,
        body: str,
        cta: str,
        assets: list[dict[str, Any]],
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "platform": platform,
            "format": spec.get("supported_formats", ["image"])[0],
            "headline": headline,
            "body": body,
            "cta": cta,
            "assets": assets,
        }

    @staticmethod
    def _build_tracking(campaign_id: str, platform: str) -> dict[str, Any]:
        return {
            "utm_source": platform,
            "utm_medium": "paid",
            "utm_campaign": campaign_id,
            "pixel_events": ["PageView", "Lead", "Purchase"],
        }
