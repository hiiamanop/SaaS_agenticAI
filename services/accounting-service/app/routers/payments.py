import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Payment, Invoice, InvoiceStatus, JournalEntry
from app.schemas import PaymentCreate, PaymentRead
from app.events import publish

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def record_payment(body: PaymentCreate, db: AsyncSession = Depends(get_db)):
    # Validate invoice exists for this tenant
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == body.invoice_id,
            Invoice.tenant_id == body.tenant_id,
        )
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    payment = Payment(
        tenant_id=body.tenant_id,
        invoice_id=body.invoice_id,
        amount=body.amount,
        method=body.method,
        reference=body.reference,
    )
    db.add(payment)

    # Mark invoice paid and record double-entry journal lines
    invoice.status = InvoiceStatus.paid
    db.add(invoice)

    db.add(JournalEntry(
        tenant_id=body.tenant_id,
        account_code="2000",  # Accounts Payable
        debit=body.amount,
        credit=0,
        reference_id=payment.id,
        description=f"Payment for invoice {invoice.invoice_number}",
    ))
    db.add(JournalEntry(
        tenant_id=body.tenant_id,
        account_code="1000",  # Cash
        debit=0,
        credit=body.amount,
        reference_id=payment.id,
        description=f"Payment for invoice {invoice.invoice_number}",
    ))

    await db.commit()
    await db.refresh(payment)

    await publish(
        "accounting.payment.recorded",
        "accounting.payment.recorded",
        str(body.tenant_id),
        {
            "payment_id": str(payment.id),
            "invoice_id": str(body.invoice_id),
            "tenant_id": str(body.tenant_id),
            "amount": str(payment.amount),
            "method": body.method.value,
        },
    )
    return payment


@router.get("/", response_model=list[PaymentRead])
async def list_payments(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.tenant_id == tenant_id))
    return result.scalars().all()
