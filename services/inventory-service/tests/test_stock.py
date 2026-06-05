# services/inventory-service/tests/test_stock.py
import uuid
import pytest
from tests.conftest import TENANT_A, TENANT_B


@pytest.mark.asyncio
async def test_create_stock(client):
    # First create a warehouse
    wh_resp = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A),
        "name": "Main Warehouse",
        "code": "WH-001",
    })
    wh_id = wh_resp.json()["id"]

    resp = await client.post("/stock/", json={
        "tenant_id": str(TENANT_A),
        "warehouse_id": wh_id,
        "product_sku": "SKU-001",
        "product_name": "Widget A",
        "qty_on_hand": 100,
        "reorder_point": 10,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["product_sku"] == "SKU-001"
    assert data["qty_on_hand"] == 100
    assert data["qty_available"] == 100
    assert data["qty_reserved"] == 0


@pytest.mark.asyncio
async def test_get_stock(client):
    wh_resp = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A),
        "name": "WH",
        "code": "WH-002",
    })
    wh_id = wh_resp.json()["id"]

    create = await client.post("/stock/", json={
        "tenant_id": str(TENANT_A),
        "warehouse_id": wh_id,
        "product_sku": "SKU-002",
        "product_name": "Widget B",
        "qty_on_hand": 50,
    })
    stock_id = create.json()["id"]
    resp = await client.get(f"/stock/{stock_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == stock_id


@pytest.mark.asyncio
async def test_list_stock_by_warehouse(client):
    wh_resp = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A),
        "name": "WH",
        "code": "WH-003",
    })
    wh_id = wh_resp.json()["id"]

    for i in range(3):
        await client.post("/stock/", json={
            "tenant_id": str(TENANT_A),
            "warehouse_id": wh_id,
            "product_sku": f"SKU-{i:03d}",
            "product_name": f"Product {i}",
            "qty_on_hand": 10 * (i + 1),
        })

    resp = await client.get(f"/stock/?warehouse_id={wh_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_reserve_stock(client):
    wh_resp = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A),
        "name": "WH",
        "code": "WH-004",
    })
    wh_id = wh_resp.json()["id"]

    create = await client.post("/stock/", json={
        "tenant_id": str(TENANT_A),
        "warehouse_id": wh_id,
        "product_sku": "SKU-RESERVE",
        "product_name": "Item",
        "qty_on_hand": 100,
    })
    stock_id = create.json()["id"]

    resp = await client.post(f"/stock/{stock_id}/reserve", json={"quantity": 20})
    assert resp.status_code == 200
    data = resp.json()
    assert data["qty_available"] == 80
    assert data["qty_reserved"] == 20


@pytest.mark.asyncio
async def test_release_stock(client):
    wh_resp = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A),
        "name": "WH",
        "code": "WH-005",
    })
    wh_id = wh_resp.json()["id"]

    create = await client.post("/stock/", json={
        "tenant_id": str(TENANT_A),
        "warehouse_id": wh_id,
        "product_sku": "SKU-RELEASE",
        "product_name": "Item",
        "qty_on_hand": 100,
    })
    stock_id = create.json()["id"]

    # Reserve first
    await client.post(f"/stock/{stock_id}/reserve", json={"quantity": 30})
    # Then release
    resp = await client.post(f"/stock/{stock_id}/release", json={"quantity": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert data["qty_available"] == 80
    assert data["qty_reserved"] == 20


@pytest.mark.asyncio
async def test_stock_movement_recorded(client):
    wh_resp = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A),
        "name": "WH",
        "code": "WH-006",
    })
    wh_id = wh_resp.json()["id"]

    create = await client.post("/stock/", json={
        "tenant_id": str(TENANT_A),
        "warehouse_id": wh_id,
        "product_sku": "SKU-MOVEMENT",
        "product_name": "Item",
        "qty_on_hand": 100,
    })
    stock_id = create.json()["id"]

    await client.post(f"/stock/{stock_id}/reserve", json={"quantity": 15, "reference": "ORD-001"})

    resp = await client.get(f"/stock/{stock_id}/movements")
    assert resp.status_code == 200
    movements = resp.json()
    assert len(movements) >= 1
    assert movements[0]["movement_type"] == "reservation"
    assert movements[0]["quantity"] == 15


@pytest.mark.asyncio
async def test_stock_isolated_by_tenant(client):
    # Create warehouse and stock for TENANT_A
    wh_a = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_A),
        "name": "WH-A",
        "code": "WH-TA",
    })
    wh_a_id = wh_a.json()["id"]
    await client.post("/stock/", json={
        "tenant_id": str(TENANT_A),
        "warehouse_id": wh_a_id,
        "product_sku": "SKU-A",
        "product_name": "Product A",
        "qty_on_hand": 50,
    })

    # Create warehouse and stock for TENANT_B
    wh_b = await client.post("/warehouses/", json={
        "tenant_id": str(TENANT_B),
        "name": "WH-B",
        "code": "WH-TB",
    })
    wh_b_id = wh_b.json()["id"]
    await client.post("/stock/", json={
        "tenant_id": str(TENANT_B),
        "warehouse_id": wh_b_id,
        "product_sku": "SKU-B",
        "product_name": "Product B",
        "qty_on_hand": 75,
    })

    # TENANT_A sees only their stock
    resp_a = await client.get(f"/stock/?tenant_id={TENANT_A}")
    assert len(resp_a.json()) == 1
    assert resp_a.json()[0]["tenant_id"] == str(TENANT_A)
