import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel
from app.models import InvoiceStatus, PaymentMethod


class VendorCreate(BaseModel):
    tenant_id: uuid.UUID
    name: str
    email: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None


class VendorRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    email: Optional[str]
    tax_id: Optional[str]
    payment_terms: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class InvoiceLineItemCreate(BaseModel):
    po_item_id: Optional[uuid.UUID] = None
    product_sku: Optional[str] = None
    quantity: int = 1
    amount: Decimal = Decimal("0.00")


class InvoiceLineItemRead(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    po_item_id: Optional[uuid.UUID]
    product_sku: Optional[str]
    quantity: int
    amount: Decimal
    created_at: datetime
    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    tenant_id: uuid.UUID
    vendor_id: Optional[uuid.UUID] = None
    po_id: Optional[uuid.UUID] = None
    items: List[InvoiceLineItemCreate] = []


class InvoiceRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    invoice_number: str
    po_id: Optional[uuid.UUID]
    vendor_id: Optional[uuid.UUID]
    total_amount: Decimal
    status: InvoiceStatus
    created_at: datetime
    items: List[InvoiceLineItemRead] = []
    model_config = {"from_attributes": True}


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None


class PaymentCreate(BaseModel):
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    method: PaymentMethod = PaymentMethod.bank_transfer
    reference: Optional[str] = None


class PaymentRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    method: PaymentMethod
    reference: Optional[str]
    payment_date: datetime
    created_at: datetime
    model_config = {"from_attributes": True}
