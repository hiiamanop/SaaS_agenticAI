# services/crm-service/tests/test_tenant_isolation.py
"""Critical: Tenant A must never see Tenant B data."""
import pytest
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_leads_isolated_between_tenants(client):
    await client.post("/leads/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "TenantA", "last_name": "Lead", "email": "a@tenanta.com",
    })
    await client.post("/leads/", json={
        "tenant_id": str(TENANT_B),
        "first_name": "TenantB", "last_name": "Lead", "email": "b@tenantb.com",
    })

    resp_a = await client.get(f"/leads/?tenant_id={TENANT_A}")
    emails_a = [lead["email"] for lead in resp_a.json()]
    assert "a@tenanta.com" in emails_a
    assert "b@tenantb.com" not in emails_a

    resp_b = await client.get(f"/leads/?tenant_id={TENANT_B}")
    emails_b = [lead["email"] for lead in resp_b.json()]
    assert "b@tenantb.com" in emails_b
    assert "a@tenanta.com" not in emails_b


@pytest.mark.asyncio
async def test_contacts_isolated_between_tenants(client):
    await client.post("/contacts/", json={
        "tenant_id": str(TENANT_A), "first_name": "A", "last_name": "X", "email": "ax@a.com"
    })
    await client.post("/contacts/", json={
        "tenant_id": str(TENANT_B), "first_name": "B", "last_name": "Y", "email": "by@b.com"
    })

    resp_a = await client.get(f"/contacts/?tenant_id={TENANT_A}")
    emails_a = [c["email"] for c in resp_a.json()]
    assert "ax@a.com" in emails_a
    assert "by@b.com" not in emails_a
