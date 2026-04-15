"""
Client WhatsApp via Meta Cloud API.

Responsabilités :
- Envoyer des messages texte libres (dans la fenêtre de 24h)
- Envoyer des messages template (hors fenêtre de 24h, nécessite approbation Meta)
- Gérer les erreurs API : token expiré, quota, numéro invalide
- Logger chaque envoi avec statut dans la table `alerts`

Architecture :
    WhatsAppClient
    ├── send_text_message(to, text)       → message libre
    ├── send_template_message(to, ...)    → message template approuvé
    ├── send_coupon(bets)                 → coupon quotidien (délègue à formatters)
    ├── send_alert(bet)                   → alerte value bet unitaire
    └── send_to_all_recipients(text)      → broadcast à tous les destinataires configurés

Gestion des erreurs Meta Cloud API :
    Code 131047 → message hors fenêtre 24h → basculer en template
    Code 131056 → quota atteint → retry dans 1h
    Code 100    → numéro invalide → skip et log
    Code 190    → token expiré → tenter refresh et retry

Usage:
    client = WhatsAppClient()
    await client.send_coupon([bet1, bet2, bet3])
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class WhatsAppMessage:
    """
    Représente un message WhatsApp à envoyer.

    Attributes:
        to: Numéro destinataire en format international (+33612345678).
        message_type: Type de message : 'text' ou 'template'.
        text: Corps du message texte (pour message_type='text').
        template_name: Nom du template Meta approuvé (pour message_type='template').
        template_params: Paramètres du template (pour message_type='template').
    """

    to: str
    message_type: str = "text"
    text: str = ""
    template_name: str = ""
    template_params: list[dict] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.template_params is None:
            self.template_params = []


@dataclass
class SendResult:
    """
    Résultat d'un envoi de message WhatsApp.

    Attributes:
        success: True si le message a été accepté par l'API Meta.
        message_id: ID du message WhatsApp (wamid.xxx) si succès.
        error_code: Code d'erreur Meta si échec.
        error_message: Message d'erreur human-readable si échec.
        recipient: Numéro destinataire.
    """

    success: bool
    recipient: str
    message_id: str = ""
    error_code: int | None = None
    error_message: str = ""


class WhatsAppClient:
    """
    Client pour l'API Meta WhatsApp Cloud.

    Une seule instance doit être créée par processus (singleton via le scheduler).
    Le client httpx est partagé entre tous les appels pour la performance.
    """

    GRAPH_API_BASE = "https://graph.facebook.com"

    def __init__(self) -> None:
        """
        Initialise le client en chargeant la configuration depuis settings.

        Configure :
        - L'URL de base (graph.facebook.com/{version}/{phone_number_id}/messages)
        - Les headers d'autorisation avec le token Bearer
        - Le client httpx avec timeout de 10 secondes
        """
        raise NotImplementedError

    async def send_text_message(self, to: str, text: str) -> SendResult:
        """
        Envoie un message texte libre à un numéro WhatsApp.

        Utilise le type 'text' de l'API Meta. Nécessite que le destinataire
        ait envoyé un message dans les dernières 24h (fenêtre de service).
        Hors fenêtre, retourner une erreur 131047 → utiliser send_template_message().

        Args:
            to: Numéro en format international (ex: "+33612345678").
            text: Corps du message (max 4096 caractères). Troncature automatique si dépassé.

        Returns:
            SendResult avec success=True et le message_id si accepté.

        Raises:
            Ne lève pas d'exception : toutes les erreurs sont capturées et
            retournées dans SendResult avec success=False.
        """
        raise NotImplementedError

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "fr",
        components: list[dict[str, Any]] | None = None,
    ) -> SendResult:
        """
        Envoie un message template Meta approuvé.

        Les templates sont définis dans Meta Business Manager et doivent être
        approuvés (délai 24-48h). Utilisé pour les messages hors fenêtre 24h.

        Args:
            to: Numéro destinataire en format international.
            template_name: Nom exact du template approuvé (ex: "daily_coupon").
            language_code: Code langue du template (ex: "fr", "en").
            components: Paramètres du template (variables {{1}}, {{2}}, etc.).
                       Format : [{"type": "body", "parameters": [{"type": "text", "text": "val"}]}]

        Returns:
            SendResult avec success=True si accepté.
        """
        raise NotImplementedError

    async def send_coupon(self, bets: list[dict[str, Any]]) -> list[SendResult]:
        """
        Envoie le coupon quotidien de value bets à tous les destinataires configurés.

        Délègue le formatage à CouponFormatter.format_daily_coupon().
        Envoie à chaque numéro dans settings.whatsapp_recipients_list.
        Sauvegarde chaque envoi dans la table `alerts`.

        Args:
            bets: Liste de dicts représentant les value bets du jour.
                  Chaque dict doit avoir : match, market, outcome, odds, ev, kelly.

        Returns:
            Liste de SendResult, un par destinataire.
        """
        raise NotImplementedError

    async def send_alert(self, bet: dict[str, Any]) -> list[SendResult]:
        """
        Envoie une alerte value bet unitaire (ex: mouvement de cotes détecté).

        Utilisé pour les alertes temps réel (Phase 3), pas pour le coupon quotidien.

        Args:
            bet: Dict représentant un value bet avec toutes les informations nécessaires.

        Returns:
            Liste de SendResult, un par destinataire.
        """
        raise NotImplementedError

    async def send_to_all_recipients(self, text: str, message_type: str = "coupon") -> list[SendResult]:
        """
        Envoie un message texte à tous les destinataires configurés en parallèle.

        Utilise asyncio.gather() pour envoyer simultanément à tous les destinataires.
        Les erreurs sur un destinataire n'affectent pas les autres.

        Args:
            text: Texte du message (max 4096 chars, tronqué si besoin).
            message_type: Type de message pour la sauvegarde en base ('coupon', 'alert', 'analysis').

        Returns:
            Liste de SendResult, un par destinataire dans WHATSAPP_RECIPIENTS.
        """
        raise NotImplementedError

    def _build_text_payload(self, to: str, text: str) -> dict[str, Any]:
        """
        Construit le payload JSON pour un message texte.

        Args:
            to: Numéro destinataire.
            text: Corps du message.

        Returns:
            Dict prêt à être envoyé à l'API Meta.
        """
        raise NotImplementedError

    def _build_template_payload(
        self, to: str, template_name: str, language_code: str, components: list[dict]
    ) -> dict[str, Any]:
        """
        Construit le payload JSON pour un message template.

        Args:
            to: Numéro destinataire.
            template_name: Nom du template.
            language_code: Code langue.
            components: Paramètres du template.

        Returns:
            Dict prêt à être envoyé à l'API Meta.
        """
        raise NotImplementedError

    async def _post_message(self, payload: dict[str, Any]) -> SendResult:
        """
        Effectue l'appel POST à l'API Meta et parse la réponse.

        Gère les codes d'erreur Meta spécifiques :
        - 190 (token expiré) : log critique, pas de retry automatique
        - 131047 (hors fenêtre) : retourne erreur avec suggestion template
        - 131056 (quota) : log warning, pas de retry ici (géré au niveau appelant)
        - 100 (numéro invalide) : log et skip

        Args:
            payload: Corps du message JSON.

        Returns:
            SendResult parsé depuis la réponse API.
        """
        raise NotImplementedError

    async def close(self) -> None:
        """Ferme le client httpx proprement. Appeler à la fin du programme."""
        raise NotImplementedError
