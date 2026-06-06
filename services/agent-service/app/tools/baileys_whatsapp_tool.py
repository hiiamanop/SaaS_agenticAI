"""Baileys WhatsApp tool for contact validation and messaging."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class BaileysWhatsAppTool:
    """Stub for Baileys WhatsApp API integration.

    In production this uses a running Baileys node.js sidecar to interact
    with the WhatsApp Business API.
    """

    def __init__(self, sidecar_url: str = "http://localhost:3001") -> None:
        self.sidecar_url = sidecar_url

    async def validate_number(self, phone: str) -> dict[str, Any]:
        """Validate that ``phone`` is a registered WhatsApp number.

        Returns dict with:
        - phone, is_valid, whatsapp_id, name
        """
        logger.info("BaileysWhatsAppTool.validate_number phone=%s", phone)
        # Production: POST to Baileys sidecar /validate
        # Stub; tests patch this method.
        return {
            "phone": phone,
            "is_valid": False,
            "whatsapp_id": None,
            "name": None,
        }

    async def send_message(
        self,
        whatsapp_id: str,
        message: str,
        media_url: str | None = None,
    ) -> dict[str, Any]:
        """Send a WhatsApp message to ``whatsapp_id``."""
        logger.info(
            "BaileysWhatsAppTool.send_message to=%s media=%s", whatsapp_id, media_url
        )
        return {"status": "queued", "whatsapp_id": whatsapp_id}
