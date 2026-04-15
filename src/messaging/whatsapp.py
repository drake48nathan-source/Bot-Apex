"""
Client WhatsApp via WaAPI (WhatsApp Web API).
Instance : #88855 — Compte BetForge (+229 51303765)
Doc API  : https://waapi.app/api-doc
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from src.core.config import settings
from src.core.logging import get_logger
from src.messaging.formatters import AlertFormatter, CouponFormatter

logger = get_logger(__name__)


@dataclass
class SendResult:
    success: bool
    recipient: str
    message_id: str = ""
    error_code: int | None = None
    error_message: str = ""
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __bool__(self) -> bool:
        return self.success


class WhatsAppClient:
    """
    Envoie des messages WhatsApp via l'API REST WaAPI.
    Endpoint : POST /api/v1/instances/{instanceId}/client/action/send-message
    Auth     : Bearer token dans le header Authorization.
    """

    BASE_URL = "https://waapi.app/api/v1"

    def __init__(self) -> None:
        self._instance_id = settings.WAAPI_INSTANCE_ID
        self._token = settings.WAAPI_TOKEN
        self._recipient = settings.WAAPI_RECIPIENT
        self._timeout = httpx.Timeout(30.0)

    async def send_text(self, chat_id: str, text: str) -> SendResult:
        """Envoie un message texte brut a un chat_id WaAPI (ex: 2290XXXXXXXXX@c.us)."""
        if not self._is_configured():
            logger.warning("WhatsApp desactive — variables WAAPI_* manquantes")
            return SendResult(success=False, recipient=chat_id, error_message="not_configured")

        url = f"{self.BASE_URL}/instances/{self._instance_id}/client/action/send-message"
        payload = {"chatId": chat_id, "message": text}
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                msg_id = (
                    data.get("data", {}).get("id", "")
                    or data.get("id", "")
                    or "sent"
                )
                logger.info("WhatsApp OK", chat_id=chat_id, msg_id=msg_id)
                return SendResult(success=True, recipient=chat_id, message_id=str(msg_id))

            logger.error(
                "WhatsApp erreur HTTP",
                status=response.status_code,
                body=response.text[:300],
            )
            return SendResult(
                success=False,
                recipient=chat_id,
                error_code=response.status_code,
                error_message=response.text[:200],
            )

        except httpx.TimeoutException as exc:
            logger.error("WhatsApp timeout", error=str(exc))
            return SendResult(success=False, recipient=chat_id, error_message="timeout")
        except Exception as exc:
            logger.error("WhatsApp exception", error=str(exc))
            return SendResult(success=False, recipient=chat_id, error_message=str(exc))

    async def send_coupon(self, predictions: list[Any]) -> SendResult:
        """Formate et envoie le coupon du jour."""
        text = CouponFormatter.format(predictions)
        return await self.send_text(self._recipient, text)

    async def send_alert(self, message: str, level: str = "info") -> SendResult:
        """Envoie une alerte admin."""
        text = AlertFormatter.format(message, level)
        return await self.send_text(self._recipient, text)

    async def send_raw(self, text: str, chat_id: str | None = None) -> SendResult:
        """Envoie un message texte libre."""
        target = chat_id or self._recipient
        return await self.send_text(target, text)

    def _is_configured(self) -> bool:
        return bool(self._instance_id and self._token and self._recipient)

    @property
    def is_enabled(self) -> bool:
        return self._is_configured() and not settings.DEMO_MODE

    async def health_check(self) -> dict[str, Any]:
        """Verifie que l'instance WaAPI est Ready."""
        if not self._is_configured():
            return {"status": "disabled", "reason": "not_configured"}

        url = f"{self.BASE_URL}/instances/{self._instance_id}/client/status"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return {"status": "ok", "data": response.json()}
            return {"status": "error", "code": response.status_code}
        except Exception as exc:
            return {"status": "error", "reason": str(exc)}


# Singleton exporte
whatsapp_client = WhatsAppClient()
