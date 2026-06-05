# services/sales-service/app/schemas.py
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel
from app.models import QuotationStatus, OrderStatus


class QuotationCreate(BaseModel):
    tenant_id: uuid.UUID
    contact_id: Optional[uuid.UUID] = None
    total_amount: Decimal = Decimal("0.00")
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


class QuotationRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    quotation_number: str
    contact_id: Optional[uuid.UUID]
    status: QuotationStatus
    total_amount: Decimal
    valid_until: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class QuotationUpdate(BaseModel):
    status: Optional[QuotationStatus] = None
    total_amount: Optional[Decimal] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    contact_id: Optional[uuid.UUID] = None


class OrderItemCreate(BaseModel):
    product_sku: str
    product_name: str
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")


class OrderItemRead(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    product_sku: str
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    created_at: datetime
    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    tenant_id: uuid.UUID
    contact_id: Optional[uuid.UUID] = None
    quotation_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    items: List[OrderItemCreate] = []


class OrderRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    order_number: str
    quotation_id: Optional[uuid.UUID]
    contact_id: Optional[uuid.UUID]
    status: OrderStatus
    total_amount: Decimal
    notes: Optional[str]
    created_at: datetime
    items: List[OrderItemRead] = []
    model_config = {"from_attributes": True}


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None
    contact_id: Optional[uuid.UUID] = None
