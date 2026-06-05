import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlalchemy import String
from sqlmodel import SQLModel, Field


class Vendor(SQLModel, table=True):
    __tablename__ = "vendors"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    name: str = Field(max_length=200)
    email: Optional[str] = Field(default=None, max_length=200)
    tax_id: Optional[str] = Field(default=None, max_length=100)
    payment_terms: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InvoiceStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    paid = "paid"
    cancelled = "cancelled"


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    invoice_number: str = Field(max_length=50, index=True)
    po_id: Optional[uuid.UUID] = Field(default=None, index=True)
    vendor_id: Optional[uuid.UUID] = Field(default=None, index=True)
    total_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    status: InvoiceStatus = Field(default=InvoiceStatus.pending, sa_type=String)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InvoiceLineItem(SQLModel, table=True):
    __tablename__ = "invoice_line_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    invoice_id: uuid.UUID = Field(index=True)
    po_item_id: Optional[uuid.UUID] = Field(default=None, index=True)
    product_sku: Optional[str] = Field(default=None, max_length=100)
    quantity: int = Field(default=1)
    amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaymentMethod(str, Enum):
    bank_transfer = "bank_transfer"
    check = "check"
    credit_card = "credit_card"


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    invoice_id: uuid.UUID = Field(index=True)
    amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    method: PaymentMethod = Field(default=PaymentMethod.bank_transfer, sa_type=String)
    reference: Optional[str] = Field(default=None, max_length=200)
    payment_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class JournalEntry(SQLModel, table=True):
    __tablename__ = "journal_entries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    account_code: str = Field(max_length=50)
    debit: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    credit: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    reference_id: Optional[uuid.UUID] = Field(default=None, index=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
