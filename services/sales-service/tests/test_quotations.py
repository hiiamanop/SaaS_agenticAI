# services/sales-service/tests/test_quotations.py
import pytest
import uuid
from unittest.mock import patch, AsyncMock
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_create_quotation(client):
    resp = await client.post("/quotations/", json={
        "tenant_id": str(TENANT_A),
        "contact_id": None,
        "notes": "Test quote",
        "total_amount": "500.00",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert "quotation_number" in data
    assert data["quotation_number"].startswith("QUO-")
    assert "id" in data


@pytest.mark.asyncio
async def test_get_quotation(client):
    create = await client.post("/quotations/", json={
        "tenant_id": str(TENANT_A),
        "total_amount": "1000.00",
    })
    quotation_id = create.json()["id"]
    resp = await client.get(f"/quotations/{quotation_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == quotation_id


@pytest.mark.asyncio
async def test_update_quotation_status(client):
    create = await client.post("/quotations/", json={
        "tenant_id": str(TENANT_A),
        "total_amount": "250.00",
    })
    quotation_id = create.json()["id"]
    resp = await client.patch(f"/quotations/{quotation_id}", json={"status": "sent"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


@pytest.mark.asyncio
async def test_convert_quotation_to_order(client):
    create = await client.post("/quotations/", json={
        "tenant_id": str(TENANT_A),
        "total_amount": "750.00",
        "notes": "Quote to convert",
    })
    quotation_id = create.json()["id"]
    # Accept the quotation first
    await client.patch(f"/quotations/{quotation_id}", json={"status": "accepted"})
    # Convert to order
    resp = await client.post(f"/quotations/{quotation_id}/convert")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert data["quotation_id"] == quotation_id
    assert data["order_number"].startswith("ORD-")
