"""Deterministic mock provider — used in all unit tests and as the default.

Reorders up to twice the reorder point, never below the reorder point.
"""
from __future__ import annotations

from app.gateway.base import ModelGateway, ReorderContext


class MockProvider(ModelGateway):
    name = "mock"

    async def recommend_reorder(self, ctx: ReorderContext) -> dict:
        target = ctx.reorder_point * 2
        recommended_qty = max(target - ctx.qty_available, ctx.reorder_point)

        if ctx.qty_available <= 0:
            urgency = "critical"
        elif ctx.qty_available < ctx.reorder_point / 2:
            urgency = "high"
        else:
            urgency = "normal"

        return {
            "product_sku": ctx.product_sku,
            "recommended_qty": int(recommended_qty),
            "urgency": urgency,
            "reason": (
                f"Available {ctx.qty_available} is at/below reorder point "
                f"{ctx.reorder_point}; reorder {int(recommended_qty)} units to "
                f"restore a {target}-unit buffer."
            ),
        }
