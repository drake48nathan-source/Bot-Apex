"""
Client Telegram via httpx (python-telegram-bot optionnel).

Utilise l'API Bot Telegram directement (sans dépendance lourde en Phase 1).
"""

from __future__ import annotations

from typing import Any

import httpx

from src.core.config import settings
from src.core.logging import get_logger
from src.messaging.formatters import CouponFormatter, SystemAlertFormatter

logger = get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramClient:
    """Client Telegram utilisant l'API Bot directement via httpx."""

    def __init__(self) -> None:
        self._coupon_fmt = CouponFormatter()
        self._system_fmt = SystemAlertFormatter()
        self._client: httpx.AsyncClient | None = None

        if not settings.telegram_enabled and not settings.DEMO_MODE:
            logger.warning("Telegram not configured (TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing)")

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def send_message(
        self, chat_id: str, text: str, parse_mode: str = "Markdown"
    ) -> bool:
        """Envoie un message texte à un chat Telegram."""
        if settings.DEMO_MODE:
            logger.info("DEMO_MODE: skipping Telegram send", chat_id=chat_id, length=len(text))
            return True

        if not settings.TELEGRAM_TOKEN:
            logger.warning("TELEGRAM_TOKEN not set, skipping")
            return False

        url = f"{TELEGRAM_API_BASE}/bot{settings.TELEGRAM_TOKEN}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text[:4096],
            "parse_mode": parse_mode,
        }

        client = self._get_client()
        try:
            resp = await client.post(url, json=payload)
            data = resp.json()
            if data.get("ok"):
                return True
            logger.error("Telegram API error", error=data.get("description", "Unknown"))
            return False
        except Exception as e:
            logger.error("Telegram send failed", error=str(e))
            return False

    async def send_coupon(self, bets: list[Any]) -> list[bool]:
        """Envoie le coupon à tous les chat_ids configurés."""
        text = self._coupon_fmt.format(bets)
        return await self.send_to_all(text)

    async def send_system_alert(self, message: str, level: str = "WARNING") -> bool:
        """Envoie une alerte système à l'admin Telegram."""
        chat_id = settings.ADMIN_TELEGRAM_CHAT_ID or settings.TELEGRAM_CHAT_ID
        if not chat_id:
            logger.warning("No admin Telegram chat configured")
            return False
        text = self._system_fmt.format(message, level)
        return await self.send_message(chat_id, text)

    async def send_to_all(self, text: str) -> list[bool]:
        """Envoie à tous les chat_ids configurés."""
        if not settings.TELEGRAM_CHAT_ID:
            return []
        chat_ids = [c.strip() for c in settings.TELEGRAM_CHAT_ID.split(",") if c.strip()]
        results = []
        for chat_id in chat_ids:
            ok = await self.send_message(chat_id, text)
            results.append(ok)
        return results

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "TelegramClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
