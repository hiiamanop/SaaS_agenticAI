import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class QuotationStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class Quotation(SQLModel, table=True):
    __tablename__ = "quotations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    quotation_number: str = Field(max_length=50, index=True)
    contact_id: Optional[uuid.UUID] = Field(default=None, index=True)
    status: QuotationStatus = Field(default=QuotationStatus.draft)
    total_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OrderStatus(str, Enum):
    draft = "draft"
    confirmed = "confirmed"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    order_number: str = Field(max_length=50, index=True)
    quotation_id: Optional[uuid.UUID] = Field(default=None, index=True)
    contact_id: Optional[uuid.UUID] = Field(default=None, index=True)
    status: OrderStatus = Field(default=OrderStatus.draft)
    total_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    order_id: uuid.UUID = Field(index=True)
    product_sku: str = Field(max_length=100)
    product_name: str = Field(max_length=200)
    quantity: int = Field(default=1)
    unit_price: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    total_price: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    created_at: datetime = Field(default_factory=datetime.utcnow)
