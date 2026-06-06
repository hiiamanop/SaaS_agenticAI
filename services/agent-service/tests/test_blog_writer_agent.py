# tests/test_blog_writer_agent.py
"""Tests for Blog Writer Agent."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

TENANT_A = uuid.uuid4()


@pytest.mark.asyncio
async def test_article_generation():
    """Blog Writer produces a structured article with SEO and plagiarism metadata."""
    from app.agents.blog_writer_agent import BlogWriterAgent

    agent = BlogWriterAgent(tenant_id=TENANT_A)

    with patch("app.events.publish", new=AsyncMock()):
        article = await agent.generate_article(
            title="How to Solve Inventory Management in Manufacturing",
            focus_keyword="inventory management",
            outline=[
                "Introduction",
                "Common challenges: inventory management",
                "Our solution approach",
                "Case study",
                "Conclusion & CTA",
            ],
            industry="manufacturing",
            value_proposition="AI-powered ERP that reduces stock-outs by 40%",
        )

    assert article["title"] == "How to Solve Inventory Management in Manufacturing"
    assert article["focus_keyword"] == "inventory management"
    assert article["industry"] == "manufacturing"
    assert "content" in article
    assert isinstance(article["content"], str)
    assert len(article["content"]) > 0
    assert "word_count" in article
    assert isinstance(article["word_count"], int)
    assert "meta_description" in article
    assert len(article["meta_description"]) <= 160
    assert "tags" in article
    assert isinstance(article["tags"], list)
    assert "seo_audit" in article
    assert "plagiarism_report" in article
    assert "status" in article
    assert article["status"] in ("draft", "published", "rejected")


@pytest.mark.asyncio
async def test_plagiarism_check():
    """Blog Writer plagiarism check returns correct structure and respects mock."""
    from app.agents.blog_writer_agent import BlogWriterAgent

    agent = BlogWriterAgent(tenant_id=TENANT_A)

    sample_content = "This is a sample article about inventory management in manufacturing. " * 50

    with patch(
        "app.tools.plagiarism_checker_tool.PlagiarismCheckerTool.check_content",
        new=AsyncMock(
            return_value={
                "is_original": True,
                "similarity_score": 5.0,
                "sources": [],
                "report_url": "https://plagcheck.example.com/report/abc123",
            }
        ),
    ):
        report = await agent.check_plagiarism(content=sample_content, title="Test Article")

    assert isinstance(report, dict)
    assert "is_original" in report
    assert "similarity_score" in report
    assert "sources" in report
    assert report["is_original"] is True
    assert report["similarity_score"] == 5.0
    assert isinstance(report["sources"], list)
