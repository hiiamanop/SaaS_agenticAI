import pytest
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_requisition(client):
    resp = await client.post("/requisitions/", json={
        "tenant_id": str(TENANT_A),
        "product_sku": "SKU-100",
        "quantity": 5,
        "reason": "low stock",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["product_sku"] == "SKU-100"
    assert body["quantity"] == 5
    assert body["status"] == "draft"


@pytest.mark.asyncio
async def test_list_requisitions(client):
    await client.post("/requisitions/", json={
        "tenant_id": str(TENANT_A), "product_sku": "SKU-1", "quantity": 1,
    })
    await client.post("/requisitions/", json={
        "tenant_id": str(TENANT_A), "product_sku": "SKU-2", "quantity": 2,
    })
    resp = await client.get(f"/requisitions/?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_requisition(client):
    create = await client.post("/requisitions/", json={
        "tenant_id": str(TENANT_A), "product_sku": "SKU-G", "quantity": 3,
    })
    req_id = create.json()["id"]
    resp = await client.get(f"/requisitions/{req_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == req_id


@pytest.mark.asyncio
async def test_get_requisition_not_found(client):
    import uuid
    resp = await client.get(f"/requisitions/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_requisition(client):
    create = await client.post("/requisitions/", json={
        "tenant_id": str(TENANT_A), "product_sku": "SKU-AP", "quantity": 4,
    })
    req_id = create.json()["id"]
    resp = await client.patch(f"/requisitions/{req_id}", json={"status": "approved"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
