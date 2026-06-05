import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel
from app.models import RequisitionStatus, PurchaseOrderStatus


class RequisitionCreate(BaseModel):
    tenant_id: uuid.UUID
    product_sku: str
    quantity: int = 1
    reason: Optional[str] = None


class RequisitionRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    product_sku: str
    quantity: int
    reason: Optional[str]
    status: RequisitionStatus
    created_at: datetime
    model_config = {"from_attributes": True}


class RequisitionUpdate(BaseModel):
    status: Optional[RequisitionStatus] = None
    quantity: Optional[int] = None
    reason: Optional[str] = None


class PurchaseOrderItemCreate(BaseModel):
    product_sku: str
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")


class PurchaseOrderItemRead(BaseModel):
    id: uuid.UUID
    purchase_order_id: uuid.UUID
    product_sku: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    created_at: datetime
    model_config = {"from_attributes": True}


class PurchaseOrderCreate(BaseModel):
    tenant_id: uuid.UUID
    vendor_id: Optional[uuid.UUID] = None
    requisition_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    items: List[PurchaseOrderItemCreate] = []


class PurchaseOrderRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    order_number: str
    requisition_id: Optional[uuid.UUID]
    vendor_id: Optional[uuid.UUID]
    status: PurchaseOrderStatus
    total_amount: Decimal
    notes: Optional[str]
    created_at: datetime
    items: List[PurchaseOrderItemRead] = []
    model_config = {"from_attributes": True}


class PurchaseOrderUpdate(BaseModel):
    status: Optional[PurchaseOrderStatus] = None
    vendor_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
