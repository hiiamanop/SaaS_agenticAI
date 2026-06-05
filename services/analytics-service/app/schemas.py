import uuid
from datetime import date
from decimal import Decimal
from typing import List
from pydantic import BaseModel


class RevenueDailyRead(BaseModel):
    day: date
    order_count: int
    revenue_total: Decimal
    model_config = {"from_attributes": True}


class ProcurementSpendRead(BaseModel):
    tenant_id: uuid.UUID
    po_count: int
    po_total: Decimal
    invoice_count: int
    invoice_total: Decimal
    paid_total: Decimal
    model_config = {"from_attributes": True}


class InventorySignalRead(BaseModel):
    product_sku: str
    qty_reserved_total: int
    low_stock_events: int
    model_config = {"from_attributes": True}


class OverviewRead(BaseModel):
    tenant_id: uuid.UUID
    order_count: int
    revenue_total: Decimal
    po_count: int
    po_total: Decimal
    invoice_total: Decimal
    paid_total: Decimal
    low_stock_skus: int
    revenue_daily: List[RevenueDailyRead] = []
