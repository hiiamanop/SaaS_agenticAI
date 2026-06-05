# services/crm-service/tests/test_contacts.py
import pytest
import uuid
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_create_contact(client):
    resp = await client.post("/contacts/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "Alice",
        "last_name": "Wonder",
        "email": "alice@wonder.com",
        "phone": "+62812345678",
    })
    assert resp.status_code == 201
    assert resp.json()["email"] == "alice@wonder.com"


@pytest.mark.asyncio
async def test_list_contacts(client):
    for i in range(2):
        await client.post("/contacts/", json={
            "tenant_id": str(TENANT_A),
            "first_name": f"Contact{i}",
            "last_name": "Test",
            "email": f"contact{i}@test.com",
        })
    resp = await client.get(f"/contacts/?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_update_contact(client):
    create = await client.post("/contacts/", json={
        "tenant_id": str(TENANT_A),
        "first_name": "Charlie",
        "last_name": "Brown",
        "email": "charlie@brown.com",
    })
    cid = create.json()["id"]
    resp = await client.patch(f"/contacts/{cid}", json={"phone": "+628999"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "+628999"


@pytest.mark.asyncio
async def test_get_nonexistent_contact_returns_404(client):
    resp = await client.get(f"/contacts/{uuid.uuid4()}")
    assert resp.status_code == 404
