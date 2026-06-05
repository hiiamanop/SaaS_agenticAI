# services/inventory-service/tests/test_warehouses.py
import pytest
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_create_warehouse(client):
    resp = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A),
        "name": "Main Warehouse",
        "code": "WH-001",
        "location": "Jakarta",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Main Warehouse"
    assert data["code"] == "WH-001"
    assert data["tenant_id"] == str(TENANT_A)
    assert "id" in data


@pytest.mark.asyncio
async def test_list_warehouses(client):
    for i in range(2):
        await client.post("/warehouses/", json={
            "tenant_id": str(TENANT_A),
            "name": f"Warehouse {i}",
            "code": f"WH-{i:03d}",
        })
    resp = await client.get(f"/warehouses/?tenant_id={TENANT_A}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_warehouses_isolated_by_tenant(client):
    await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A),
        "name": "Warehouse A",
        "code": "WH-A",
    })
    await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_B),
        "name": "Warehouse B",
        "code": "WH-B",
    })
    resp_a = await client.get(f"/warehouses/?tenant_id={TENANT_A}")
    assert len(resp_a.json()) == 1
    assert resp_a.json()[0]["tenant_id"] == str(TENANT_A)
    resp_b = await client.get(f"/warehouses/?tenant_id={TENANT_B}")
    assert len(resp_b.json()) == 1
    assert resp_b.json()[0]["tenant_id"] == str(TENANT_B)
