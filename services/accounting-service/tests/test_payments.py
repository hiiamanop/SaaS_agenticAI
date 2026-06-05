from unittest.mock import AsyncMock, patch
import pytest
from tests.conftest import TENANT_A


async def _make_invoice(client):
    with patch("app.service.publish", new=AsyncMock()):
        resp = await client.post("/invoices/", json={
            "tenant_id": str(TENANT_A),
            "items": [{"product_sku": "SKU-P", "quantity": 1, "amount": "100.00"}],
        })
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_record_payment_marks_invoice_paid(client):
    inv_id = await _make_invoice(client)
    with patch("app.routers.payments.publish", new=AsyncMock()) as mock_pub:
        resp = await client.post("/payments/", json={
            "tenant_id": str(TENANT_A),
            "invoice_id": inv_id,
            "amount": "100.00",
            "method": "bank_transfer",
            "reference": "TRX-1",
        })
        assert resp.status_code == 201
        assert resp.json()["amount"] == "100.00"
        mock_pub.assert_awaited_once()
        assert mock_pub.await_args.args[0] == "accounting.payment.recorded"

    inv = await client.get(f"/invoices/{inv_id}")
    assert inv.json()["status"] == "paid"


@pytest.mark.asyncio
async def test_payment_creates_journal_entries(client, db_session):
    from app.models import JournalEntry
    from sqlmodel import select

    inv_id = await _make_invoice(client)
    with patch("app.routers.payments.publish", new=AsyncMock()):
        await client.post("/payments/", json={
            "tenant_id": str(TENANT_A),
            "invoice_id": inv_id,
            "amount": "100.00",
        })

    result = await db_session.execute(select(JournalEntry))
    entries = result.scalars().all()
    assert len(entries) == 2
    total_debit = sum(e.debit for e in entries)
    total_credit = sum(e.credit for e in entries)
    assert total_debit == total_credit == 100


@pytest.mark.asyncio
async def test_payment_invoice_not_found(client):
    import uuid
    resp = await client.post("/payments/", json={
        "tenant_id": str(TENANT_A),
        "invoice_id": str(uuid.uuid4()),
        "amount": "10.00",
    })
    assert resp.status_code == 404
