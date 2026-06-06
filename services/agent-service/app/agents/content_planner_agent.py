"""Content Planner Agent.

Analyses industry pain points and generates a content strategy matrix
(blog articles, LinkedIn posts, ad creatives) for a marketing campaign.
HITL checkpoint: strategy requires Marketing Manager approval before execution.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.events import publish

logger = logging.getLogger(__name__)


class ContentPlannerAgent:
    """Content strategy planning agent with HITL approval gate."""

    def __init__(self, tenant_id: uuid.UUID) -> None:
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def generate_strategy(
        self,
        campaign_id: str,
        industry: str,
        pain_points: list[str],
        value_proposition: str,
        target_audience: str,
    ) -> dict[str, Any]:
        """Generate a content strategy matrix for the campaign.

        Returns a dict with:
        - campaign_id
        - industry
        - blog_articles (list[dict])  — title + focus_keyword + outline
        - linkedin_posts (list[dict]) — copy + hashtags
        - ad_creatives  (list[dict]) — headline + body + cta + platform
        - status: "pending_approval"
        """
        logger.info(
            "ContentPlannerAgent.generate_strategy tenant=%s campaign=%s",
            self.tenant_id,
            campaign_id,
        )

        blog_articles = [
            {
                "title": f"How to Solve {pain} in the {industry.title()} Industry",
                "focus_keyword": pain,
                "outline": [
                    "Introduction",
                    f"Common challenges: {pain}",
                    "Our solution approach",
                    "Case study",
                    "Conclusion & CTA",
                ],
            }
            for pain in pain_points[:3]
        ]

        linkedin_posts = [
            {
                "copy": (
                    f"Struggling with {pain}? "
                    f"{value_proposition} — designed for {target_audience}. "
                    "Learn more in our latest article."
                ),
                "hashtags": [
                    f"#{industry.replace(' ', '')}",
                    "#B2BMarketing",
                    "#DigitalTransformation",
                ],
            }
            for pain in pain_points[:2]
        ]

        ad_creatives = [
            {
                "headline": f"Fix {pain} Today",
                "body": value_proposition,
                "cta": "Get Free Demo",
                "platform": platform,
            }
            for pain in pain_points[:2]
            for platform in ["meta", "google"]
        ]

        strategy: dict[str, Any] = {
            "campaign_id": campaign_id,
            "industry": industry,
            "blog_articles": blog_articles,
            "linkedin_posts": linkedin_posts,
            "ad_creatives": ad_creatives,
            "status": "pending_approval",
        }

        # Publish HITL event — waits for Marketing Manager approval
        await publish(
            "marketing.campaign.strategy.proposed",
            "marketing.campaign.strategy.proposed",
            str(self.tenant_id),
            {
                "tenant_id": str(self.tenant_id),
                "campaign_id": campaign_id,
                "article_count": len(blog_articles),
                "post_count": len(linkedin_posts),
                "ad_count": len(ad_creatives),
            },
        )

        return strategy

    async def approve_strategy(
        self,
        strategy: dict[str, Any],
        approver_id: str,
    ) -> dict[str, Any]:
        """Mark a strategy as approved (HITL approval step).

        In production the Marketing Manager calls this endpoint after
        reviewing the proposed strategy in the UI.
        """
        strategy["status"] = "approved"
        strategy["approver_id"] = approver_id

        await publish(
            "marketing.campaign.strategy.approved",
            "marketing.campaign.strategy.approved",
            str(self.tenant_id),
            {
                "tenant_id": str(self.tenant_id),
                "campaign_id": strategy.get("campaign_id"),
                "approver_id": approver_id,
            },
        )
        return strategy
