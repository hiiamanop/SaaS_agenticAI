# services/crm-service/tests/test_leads.py
import pytest
import uuid
from unittest.mock import patch, AsyncMock
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_lead(client):
    resp = await client.post("/leads/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@acme.com",
        "company": "Acme Corp",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "John"
    assert data["status"] == "new"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_lead(client):
    create = await client.post("/leads/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@beta.com",
    })
    lead_id = create.json()["id"]
    resp = await client.get(f"/leads/{lead_id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "jane@beta.com"


@pytest.mark.asyncio
async def test_list_leads_by_tenant(client):
    for i in range(3):
        await client.post("/leads/", json={
            "tenant_id": str(TENANT_A),
            "first_name": f"Lead{i}",
            "last_name": "Test",
            "email": f"lead{i}@test.com",
        })
    resp = await client.get(f"/leads/?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_qualify_lead_publishes_event(client):
    create = await client.post("/leads/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "Bob",
        "last_name": "Builder",
        "email": "bob@build.com",
    })
    lead_id = create.json()["id"]

    with patch("app.routers.leads.publish", new=AsyncMock()) as mock_publish:
        resp = await client.patch(f"/leads/{lead_id}", json={"status": "qualified"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "qualified"
        mock_publish.assert_awaited_once()
        assert mock_publish.call_args[0][0] == "crm.lead.qualified"


@pytest.mark.asyncio
async def test_get_nonexistent_lead_returns_404(client):
    resp = await client.get(f"/leads/{uuid.uuid4()}")
    assert resp.status_code == 404
