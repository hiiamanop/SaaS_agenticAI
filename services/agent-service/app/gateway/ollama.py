"""Ollama provider — calls a local Ollama model with JSON-structured output."""
from __future__ import annotations

import json
import logging

import httpx

from app.gateway.base import ModelGateway, ReorderContext

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a procurement reorder agent for an ERP system. Given the current "
    "stock position for a product, decide how many units to reorder.\n"
    "Rules:\n"
    "- Order enough to bring projected on-hand COMFORTABLY ABOVE the reorder "
    "point. Target roughly twice the reorder point as a safety buffer.\n"
    "- recommended_qty MUST be a positive integer and must never leave stock at "
    "or below the reorder point.\n"
    "- urgency: 'critical' when available is 0, 'high' when available is well "
    "below the reorder point, otherwise 'normal'.\n"
    "Respond ONLY with JSON matching exactly: {\"product_sku\": str, "
    "\"recommended_qty\": int, \"urgency\": \"normal\"|\"high\"|\"critical\", "
    "\"reason\": str}."
)


def _coerce_qty(value, *, floor: int) -> int:
    """Best-effort parse of the model's quantity into a sane positive int.

    LLM output is untrusted: it may return a string, float, null, or something
    below the reorder point. Clamp to at least ``floor`` (reorder_point + 1) so
    a reorder never tops up to a level that immediately re-triggers low stock.
    """
    try:
        qty = int(float(value))
    except (TypeError, ValueError):
        qty = floor
    return max(qty, floor)


_VALID_URGENCY = {"normal", "high", "critical"}


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

        # The model is instructed to emit JSON, but never trust it: fall back to
        # a deterministic recommendation if it returns malformed / non-JSON text.
        try:
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("model returned non-object JSON")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Ollama returned unparseable output (%s); falling back. Raw: %.200r",
                exc, content,
            )
            parsed = {}

        floor = ctx.reorder_point + 1
        urgency = str(parsed.get("urgency", "")).lower()
        if urgency not in _VALID_URGENCY:
            urgency = "critical" if ctx.qty_available <= 0 else "normal"

        return {
            "product_sku": parsed.get("product_sku") or ctx.product_sku,
            "recommended_qty": _coerce_qty(parsed.get("recommended_qty"), floor=floor),
            "urgency": urgency,
            "reason": str(parsed.get("reason") or "")[:500],
        }
