import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlalchemy import String
from sqlmodel import SQLModel, Field


class RequisitionStatus(str, Enum):
    draft = "draft"
    approved = "approved"
    rejected = "rejected"


class Requisition(SQLModel, table=True):
    __tablename__ = "requisitions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    product_sku: str = Field(max_length=100, index=True)
    quantity: int = Field(default=1)
    reason: Optional[str] = None
    status: RequisitionStatus = Field(default=RequisitionStatus.draft, sa_type=String)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PurchaseOrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    received = "received"
    cancelled = "cancelled"


class PurchaseOrder(SQLModel, table=True):
    __tablename__ = "purchase_orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    order_number: str = Field(max_length=50, index=True)
    requisition_id: Optional[uuid.UUID] = Field(default=None, index=True)
    vendor_id: Optional[uuid.UUID] = Field(default=None, index=True)
    total_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    status: PurchaseOrderStatus = Field(default=PurchaseOrderStatus.pending, sa_type=String)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PurchaseOrderItem(SQLModel, table=True):
    __tablename__ = "purchase_order_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    purchase_order_id: uuid.UUID = Field(index=True)
    product_sku: str = Field(max_length=100)
    quantity: int = Field(default=1)
    unit_price: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    total_price: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    created_at: datetime = Field(default_factory=datetime.utcnow)
