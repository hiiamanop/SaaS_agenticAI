import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_tenant(client):
    resp = await client.post(
        "/tenants/",
        json={"name": "Acme Corp", "slug": "acme-corp", "email": "admin@acme.com"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Corp"
    assert data["slug"] == "acme-corp"
    assert "id" in data
    assert "tenant_id" in data


@pytest.mark.asyncio
async def test_duplicate_slug_returns_409(client):
    payload = {"name": "Acme", "slug": "acme", "email": "a@a.com"}
    await client.post("/tenants/", json=payload)
    resp = await client.post("/tenants/", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_tenant(client):
    create = await client.post(
        "/tenants/",
        json={"name": "Beta", "slug": "beta", "email": "b@b.com"},
    )
    tid = create.json()["tenant_id"]
    resp = await client.get(f"/tenants/{tid}")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "beta"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_404(client):
    import uuid
    resp = await client.get(f"/tenants/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_tenant(client):
    create = await client.post(
        "/tenants/",
        json={"name": "Gamma", "slug": "gamma", "email": "g@g.com"},
    )
    tid = create.json()["tenant_id"]
    resp = await client.patch(f"/tenants/{tid}", json={"name": "Gamma Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Gamma Updated"
