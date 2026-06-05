# services/inventory-service/app/schemas.py
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models import MovementType


class WarehouseCreate(BaseModel):
    tenant_id: uuid.UUID
    name: str
    code: str
    location: Optional[str] = None


class WarehouseRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    code: str
    location: Optional[str]
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class StockCreate(BaseModel):
    tenant_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_sku: str
    product_name: str
    qty_on_hand: int = 0
    reorder_point: int = 0


class StockRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_sku: str
    product_name: str
    qty_on_hand: int
    qty_reserved: int
    qty_available: int
    reorder_point: int
    created_at: datetime
    model_config = {"from_attributes": True}


class StockAdjust(BaseModel):
    quantity: int
    reference: Optional[str] = None
    notes: Optional[str] = None


class StockMovementRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    stock_id: uuid.UUID
    movement_type: MovementType
    quantity: int
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}
