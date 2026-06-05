import pytest
from app.config import settings
from app.gateway import get_gateway, ReorderContext
from app.gateway.mock import MockProvider


@pytest.mark.asyncio
async def test_gateway_selects_mock_when_configured():
    # conftest's force_mock_provider pins this for the whole suite
    assert settings.model_provider == "mock"
    assert isinstance(get_gateway(), MockProvider)


@pytest.mark.asyncio
async def test_gateway_selects_ollama_when_configured(monkeypatch):
    from app.gateway.ollama import OllamaProvider

    monkeypatch.setattr(settings, "model_provider", "ollama")
    gw = get_gateway()
    assert isinstance(gw, OllamaProvider)
    assert gw.model == settings.ollama_model


@pytest.mark.asyncio
async def test_mock_recommends_buffer_to_double_reorder_point():
    gw = MockProvider()
    out = await gw.recommend_reorder(ReorderContext("SKU-1", qty_available=2, reorder_point=10))
    # target = 20, recommended = 20 - 2 = 18
    assert out["product_sku"] == "SKU-1"
    assert out["recommended_qty"] == 18
    assert out["urgency"] == "high"
    assert "reorder" in out["reason"].lower()


@pytest.mark.asyncio
async def test_mock_never_below_reorder_point():
    gw = MockProvider()
    out = await gw.recommend_reorder(ReorderContext("SKU-2", qty_available=15, reorder_point=10))
    # target 20 - 15 = 5, but floor is reorder_point 10
    assert out["recommended_qty"] == 10


@pytest.mark.asyncio
async def test_mock_critical_when_empty():
    gw = MockProvider()
    out = await gw.recommend_reorder(ReorderContext("SKU-3", qty_available=0, reorder_point=8))
    assert out["urgency"] == "critical"
    assert out["recommended_qty"] == 16


# --- Ollama output hardening (model output is untrusted) -------------------

@pytest.mark.parametrize("value,floor,expected", [
    ("18", 11, 18),      # numeric string
    (18.9, 11, 18),      # float -> truncated int
    (None, 11, 11),      # missing -> floor
    ("abc", 11, 11),     # garbage -> floor
    (-5, 11, 11),        # negative -> floor
    (3, 11, 11),         # below floor -> floor
    ([], 11, 11),        # wrong type -> floor
])
def test_ollama_coerce_qty_clamps_untrusted_output(value, floor, expected):
    from app.gateway.ollama import _coerce_qty
    assert _coerce_qty(value, floor=floor) == expected


async def _fake_post_returning(content: str):
    """Build an httpx.AsyncClient stub whose /api/chat returns ``content``."""
    from unittest.mock import AsyncMock, MagicMock

    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={"message": {"content": content}})
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


@pytest.mark.asyncio
async def test_ollama_falls_back_on_non_json(monkeypatch):
    import httpx
    from app.gateway.ollama import OllamaProvider

    client = await _fake_post_returning("sorry, I cannot help with that")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: client)

    gw = OllamaProvider("http://x", "llama3.1:8b")
    out = await gw.recommend_reorder(ReorderContext("SKU-X", qty_available=0, reorder_point=10))
    # Non-JSON -> deterministic fallback, schema still holds
    assert out["product_sku"] == "SKU-X"
    assert out["recommended_qty"] > 10            # never <= reorder_point
    assert out["urgency"] == "critical"           # available 0
    assert isinstance(out["reason"], str)


@pytest.mark.asyncio
async def test_ollama_repairs_invalid_fields(monkeypatch):
    import httpx
    from app.gateway.ollama import OllamaProvider

    # Valid JSON but a too-small qty and a bogus urgency
    client = await _fake_post_returning(
        '{"product_sku": "SKU-Y", "recommended_qty": 2, "urgency": "meh", "reason": "x"}'
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: client)

    gw = OllamaProvider("http://x", "llama3.1:8b")
    out = await gw.recommend_reorder(ReorderContext("SKU-Y", qty_available=5, reorder_point=10))
    assert out["recommended_qty"] == 11           # clamped to reorder_point + 1
    assert out["urgency"] == "normal"             # invalid urgency repaired
