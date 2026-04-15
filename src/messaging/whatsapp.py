"""
Client WhatsApp via Meta Cloud API.
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


class WhatsAppClient:
    """Client pour l'API Meta WhatsApp Cloud."""

    def __init__(self) -> None:
        self._coupon_fmt = CouponFormatter()
        self._alert_fmt = AlertFormatter()
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
                timeout=10.0,
            )
        return self._client

    async def send_text_message(self, to: str, text: str) -> SendResult:
        """Envoie un message texte à un numéro WhatsApp."""
        if settings.DEMO_MODE or not settings.whatsapp_enabled:
            logger.info("DEMO_MODE/disabled: skipping WhatsApp send", to=to, length=len(text))
            return SendResult(success=True, recipient=to, message_id="demo_msg_id")

        payload = self._build_text_payload(to, text)
        return await self._post_message(payload, to)

    async def send_coupon(self, bets: list[Any]) -> list[SendResult]:
        """Envoie le coupon à tous les destinataires configurés."""
        text = self._coupon_fmt.format(bets)
        return await self.send_to_all(text, message_type="daily_coupon")

    async def send_alert(self, bet: Any, trigger_reason: str = "value_bet") -> list[SendResult]:
        """Envoie une alerte value bet à tous les destinataires."""
        text = self._alert_fmt.format(bet, trigger_reason)
        return await self.send_to_all(text, message_type="value_bet")

    async def send_to_all(self, text: str, message_type: str = "text") -> list[SendResult]:
        """Envoie un message à tous les destinataires configurés."""
        recipients = [settings.WHATSAPP_RECIPIENT_NUMBER] if settings.WHATSAPP_RECIPIENT_NUMBER else []
        if not recipients:
            logger.warning("No WhatsApp recipients configured")
            return []

        results: list[SendResult] = []
        for recipient in recipients:
            result = await self.send_text_message(recipient, text)
            results.append(result)
            if result.success:
                logger.info("WhatsApp sent", to=recipient, type=message_type)
            else:
                logger.error(
                    "WhatsApp send failed",
                    to=recipient,
                    error_code=result.error_code,
                    error_message=result.error_message,
                )
        return results

    def _build_text_payload(self, to: str, text: str) -> dict[str, Any]:
        # Tronquer si nécessaire
        if len(text) > 4096:
            text = text[:4076] + "\n...[tronqué]"
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

    async def _post_message(self, payload: dict[str, Any], recipient: str) -> SendResult:
        """POST vers l'API Meta et parse la réponse."""
        url = settings.whatsapp_base_url
        client = self._get_client()
        try:
            resp = await client.post(url, json=payload)
            data = resp.json()

            if resp.status_code == 200:
                messages = data.get("messages", [{}])
                msg_id = messages[0].get("id", "") if messages else ""
                return SendResult(success=True, recipient=recipient, message_id=msg_id)

            # Gestion des erreurs Meta
            error = data.get("error", {})
            code = error.get("code", resp.status_code)
            message = error.get("message", str(data))

            # Alertes spécifiques
            if code == 190:
                logger.critical("WhatsApp token expired! Renew WHATSAPP_TOKEN.")
            elif code == 131047:
                logger.warning("Message outside 24h window, use template instead.")
            elif code == 131056:
                logger.warning("WhatsApp quota reached, retry later.")

            return SendResult(
                success=False,
                recipient=recipient,
                error_code=code,
                error_message=message,
            )
        except httpx.TimeoutException:
            return SendResult(
                success=False,
                recipient=recipient,
                error_code=-1,
                error_message="Request timeout",
            )
        except Exception as e:
            return SendResult(
                success=False,
                recipient=recipient,
                error_code=-1,
                error_message=str(e),
            )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "WhatsAppClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
