"""Ollama provider — calls a local Ollama model with JSON-structured output."""
from __future__ import annotations

import json
import logging

import httpx

from app.gateway.base import ModelGateway, ReorderContext

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a procurement reorder agent for an ERP system. Given current stock "
    "for a product, decide how many units to reorder. Respond ONLY with JSON "
    "matching: {\"product_sku\": str, \"recommended_qty\": int, "
    "\"urgency\": \"normal\"|\"high\"|\"critical\", \"reason\": str}."
)


class OllamaProvider(ModelGateway):
    name = "ollama"

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def recommend_reorder(self, ctx: ReorderContext) -> dict:
        prompt = (
            f"product_sku={ctx.product_sku}, qty_available={ctx.qty_available}, "
            f"reorder_point={ctx.reorder_point}. How many units should we reorder?"
        )
        payload = {
            "model": self.model,
            "format": "json",
            "stream": False,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            content = resp.json()["message"]["content"]

        parsed = json.loads(content)
        # Coerce / validate the fields we rely on
        return {
            "product_sku": parsed.get("product_sku", ctx.product_sku),
            "recommended_qty": int(parsed.get("recommended_qty", ctx.reorder_point)),
            "urgency": parsed.get("urgency", "normal"),
            "reason": parsed.get("reason", ""),
        }
