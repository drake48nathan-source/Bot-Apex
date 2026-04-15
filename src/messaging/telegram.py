"""
Client Telegram via python-telegram-bot.

Canal de fallback si WhatsApp échoue.
Utilisé aussi pour les alertes système admin (erreurs pipeline, etc.).

Usage:
    client = TelegramClient()
    await client.send_coupon(bets)
    await client.send_system_alert("Pipeline échoué: timeout API-Football")
"""

from __future__ import annotations

from typing import Any


class TelegramClient:
    """
    Client Telegram utilisant python-telegram-bot (asyncio).

    Un seul bot token est utilisé.
    Les messages peuvent être envoyés à plusieurs chat_ids (groupes ou privés).
    """

    def __init__(self) -> None:
        """
        Initialise le client avec le token et les chat_ids depuis Settings.

        Si TELEGRAM_TOKEN est vide, le client est en mode désactivé
        (toutes les méthodes logent un warning et retournent silencieusement).
        """
        raise NotImplementedError

    async def send_message(
        self, chat_id: str, text: str, parse_mode: str = "HTML"
    ) -> bool:
        """
        Envoie un message texte à un chat Telegram.

        Args:
            chat_id: ID du chat ou du groupe (str ou int).
            text: Corps du message. Supporte HTML ou Markdown selon parse_mode.
            parse_mode: 'HTML' ou 'MarkdownV2'. HTML recommandé (plus simple).

        Returns:
            True si envoyé avec succès, False sinon.
        """
        raise NotImplementedError

    async def send_coupon(self, bets: list[Any]) -> list[bool]:
        """
        Envoie le coupon quotidien à tous les chat_ids configurés.

        Réutilise CouponFormatter (mêmes messages que WhatsApp).

        Args:
            bets: Liste de SelectedBet.

        Returns:
            Liste de bool, un par chat_id (True = succès).
        """
        raise NotImplementedError

    async def send_system_alert(self, message: str) -> bool:
        """
        Envoie une alerte système à l'admin Telegram (ADMIN_TELEGRAM_CHAT_ID).

        Utilisé pour les notifications d'erreur pipeline (plus fiable que WhatsApp
        pour les alertes système car pas de fenêtre de 24h).

        Args:
            message: Texte de l'alerte (prefixé automatiquement par "⚠️ SYSTÈME :")

        Returns:
            True si envoyé avec succès.
        """
        raise NotImplementedError

    async def send_to_all(self, text: str) -> list[bool]:
        """
        Envoie un message à tous les chat_ids configurés en parallèle.

        Args:
            text: Texte du message.

        Returns:
            Liste de bool, un par chat_id.
        """
        raise NotImplementedError
