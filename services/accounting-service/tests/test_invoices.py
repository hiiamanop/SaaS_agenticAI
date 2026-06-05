import uuid
from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_vendor(client):
    resp = await client.post("/vendors/", json={
        "tenant_id": str(TENANT_A),
        "name": "Acme Supplies",
        "email": "billing@acme.test",
        "tax_id": "TAX-001",
        "payment_terms": "net30",
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "Acme Supplies"


@pytest.mark.asyncio
async def test_create_invoice_publishes_event(client):
    with patch("app.service.publish", new=AsyncMock()) as mock_pub:
        resp = await client.post("/invoices/", json={
            "tenant_id": str(TENANT_A),
            "items": [
                {"product_sku": "SKU-1", "quantity": 2, "amount": "20.00"},
                {"product_sku": "SKU-2", "quantity": 1, "amount": "30.00"},
            ],
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["total_amount"] == "50.00"
        assert body["status"] == "pending"
        assert len(body["items"]) == 2
        assert body["invoice_number"].startswith("INV-")
        mock_pub.assert_awaited_once()
        assert mock_pub.await_args.args[0] == "accounting.invoice.created"


@pytest.mark.asyncio
async def test_get_invoice(client):
    create = await client.post("/invoices/", json={
        "tenant_id": str(TENANT_A),
        "items": [{"product_sku": "SKU-G", "quantity": 1, "amount": "9.99"}],
    })
    inv_id = create.json()["id"]
    resp = await client.get(f"/invoices/{inv_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == inv_id


@pytest.mark.asyncio
async def test_get_invoice_not_found(client):
    resp = await client.get(f"/invoices/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_invoice(client):
    create = await client.post("/invoices/", json={
        "tenant_id": str(TENANT_A),
        "items": [{"product_sku": "SKU-AP", "quantity": 1, "amount": "5.00"}],
    })
    inv_id = create.json()["id"]
    resp = await client.patch(f"/invoices/{inv_id}", json={"status": "approved"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
