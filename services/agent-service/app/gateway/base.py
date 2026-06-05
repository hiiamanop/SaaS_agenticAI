"""Model Gateway abstraction.

Every provider returns a structured reorder recommendation so the rest of the
service is independent of the underlying LLM (Ollama in dev, mock in tests).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ReorderContext:
    product_sku: str
    qty_available: int
    reorder_point: int


class ModelGateway(ABC):
    name: str = "base"

    @abstractmethod
    async def recommend_reorder(self, ctx: ReorderContext) -> dict:
        """Return a dict: {product_sku, recommended_qty, urgency, reason}."""
        raise NotImplementedError
