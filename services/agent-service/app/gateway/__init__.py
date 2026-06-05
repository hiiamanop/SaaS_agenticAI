"""Model Gateway factory — selects the provider from settings."""
from __future__ import annotations

from app.config import settings
from app.gateway.base import ModelGateway, ReorderContext
from app.gateway.mock import MockProvider

__all__ = ["ModelGateway", "ReorderContext", "get_gateway"]


def get_gateway() -> ModelGateway:
    if settings.model_provider == "ollama":
        from app.gateway.ollama import OllamaProvider
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    return MockProvider()
