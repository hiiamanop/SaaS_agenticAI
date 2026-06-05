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
