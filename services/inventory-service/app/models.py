import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import String
from sqlmodel import SQLModel, Field


class MovementType(str, Enum):
    receipt = "receipt"
    issue = "issue"
    reservation = "reservation"
    release = "release"
    adjustment = "adjustment"
    transfer = "transfer"


class Warehouse(SQLModel, table=True):
    __tablename__ = "warehouses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    name: str = Field(max_length=200)
    code: str = Field(max_length=50, index=True)
    location: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Stock(SQLModel, table=True):
    __tablename__ = "stock"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    warehouse_id: uuid.UUID = Field(index=True)
    product_sku: str = Field(max_length=100, index=True)
    product_name: str = Field(max_length=200)
    qty_on_hand: int = Field(default=0)
    qty_reserved: int = Field(default=0)
    qty_available: int = Field(default=0)
    reorder_point: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StockMovement(SQLModel, table=True):
    __tablename__ = "stock_movements"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    stock_id: uuid.UUID = Field(index=True)
    movement_type: MovementType = Field(sa_type=String)
    quantity: int
    reference: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
