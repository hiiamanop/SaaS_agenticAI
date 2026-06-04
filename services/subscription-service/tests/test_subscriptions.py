import pytest
import uuid


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_subscription(client):
    resp = await client.post(
        "/subscriptions/",
        json={"tenant_id": str(uuid.uuid4()), "plan": "starter"},
    )
    assert resp.status_code == 201
    assert resp.json()["plan"] == "starter"
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_get_subscription(client):
    tid = str(uuid.uuid4())
    await client.post("/subscriptions/", json={"tenant_id": tid, "plan": "business"})
    resp = await client.get(f"/subscriptions/{tid}")
    assert resp.status_code == 200
    assert resp.json()["plan"] == "business"


@pytest.mark.asyncio
async def test_invalid_plan_rejected(client):
    resp = await client.post(
        "/subscriptions/",
        json={"tenant_id": str(uuid.uuid4()), "plan": "invalid_plan"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_modules_starter(client):
    tid = str(uuid.uuid4())
    await client.post("/subscriptions/", json={"tenant_id": tid, "plan": "starter"})
    resp = await client.get(f"/subscriptions/{tid}/modules")
    assert resp.status_code == 200
    modules = resp.json()["modules"]
    assert "crm" in modules
    assert "sales" in modules
    assert "accounting" not in modules


@pytest.mark.asyncio
async def test_modules_enterprise(client):
    tid = str(uuid.uuid4())
    await client.post("/subscriptions/", json={"tenant_id": tid, "plan": "enterprise"})
    resp = await client.get(f"/subscriptions/{tid}/modules")
    modules = resp.json()["modules"]
    assert "accounting" in modules
    assert "ai_platform" in modules
