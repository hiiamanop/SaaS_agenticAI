# services/marketing-service/tests/test_campaigns.py
import pytest
import uuid
from unittest.mock import patch, AsyncMock
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "marketing-service"


@pytest.mark.asyncio
async def test_create_campaign(client):
    resp = await client.post("/campaigns/", json={
        "tenant_id": str(TENANT_A),
        "name": "Q1 Growth Campaign",
        "industry": "SaaS",
        "target_audience": "SMB CTOs",
        "pain_points": "manual workflows, lack of automation",
        "value_proposition": "10x team productivity with AI automation",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Q1 Growth Campaign"
    assert data["status"] == "draft"
    assert "id" in data
    assert data["tenant_id"] == str(TENANT_A)


@pytest.mark.asyncio
async def test_get_campaign(client):
    create = await client.post("/campaigns/", json={
        "tenant_id": str(TENANT_A),
        "name": "Brand Awareness Campaign",
        "industry": "FinTech",
    })
    campaign_id = create.json()["id"]

    resp = await client.get(f"/campaigns/{campaign_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == campaign_id
    assert data["name"] == "Brand Awareness Campaign"
    assert data["industry"] == "FinTech"


@pytest.mark.asyncio
async def test_update_campaign_status(client):
    create = await client.post("/campaigns/", json={
        "tenant_id": str(TENANT_A),
        "name": "Pending Approval Campaign",
    })
    campaign_id = create.json()["id"]

    resp = await client.patch(f"/campaigns/{campaign_id}", json={"status": "approved"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["id"] == campaign_id


@pytest.mark.asyncio
async def test_list_campaigns_by_tenant(client):
    for i in range(3):
        await client.post("/campaigns/", json={
            "tenant_id": str(TENANT_A),
            "name": f"Campaign {i}",
        })

    resp = await client.get(f"/campaigns/?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    campaigns = resp.json()
    assert len(campaigns) == 3
    for c in campaigns:
        assert c["tenant_id"] == str(TENANT_A)


@pytest.mark.asyncio
async def test_campaigns_isolated_by_tenant(client):
    """Tenant A creates campaign; Tenant B cannot see it."""
    await client.post("/campaigns/", json={
        "tenant_id": str(TENANT_A),
        "name": "Tenant A Secret Campaign",
    })
    await client.post("/campaigns/", json={
        "tenant_id": str(TENANT_B),
        "name": "Tenant B Own Campaign",
    })

    resp_a = await client.get(f"/campaigns/?tenant_id={TENANT_A}")
    names_a = [c["name"] for c in resp_a.json()]
    assert "Tenant A Secret Campaign" in names_a
    assert "Tenant B Own Campaign" not in names_a

    resp_b = await client.get(f"/campaigns/?tenant_id={TENANT_B}")
    names_b = [c["name"] for c in resp_b.json()]
    assert "Tenant B Own Campaign" in names_b
    assert "Tenant A Secret Campaign" not in names_b
