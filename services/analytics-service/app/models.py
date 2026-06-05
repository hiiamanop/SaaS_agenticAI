import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlmodel import SQLModel, Field


class RevenueDaily(SQLModel, table=True):
    """One row per (tenant_id, day) — sales revenue read model."""
    __tablename__ = "revenue_daily"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    day: date = Field(index=True)
    order_count: int = Field(default=0)
    revenue_total: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=16)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProcurementSpend(SQLModel, table=True):
    """One row per tenant — procurement + accounting spend read model."""
    __tablename__ = "procurement_spend"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True, unique=True)
    po_count: int = Field(default=0)
    po_total: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=16)
    invoice_count: int = Field(default=0)
    invoice_total: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=16)
    paid_total: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=16)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InventorySignal(SQLModel, table=True):
    """One row per (tenant_id, product_sku) — reservation + low-stock signals."""
    __tablename__ = "inventory_signals"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(index=True)
    product_sku: str = Field(max_length=100, index=True)
    qty_reserved_total: int = Field(default=0)
    low_stock_events: int = Field(default=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
