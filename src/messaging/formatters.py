"""
Formateurs de messages pour WhatsApp et Telegram.

Trois types de messages sont générés :
1. Coupon quotidien : liste des top value bets du jour
2. Alerte value bet : notification d'un seul pari de haute valeur
3. Analyse match : rapport détaillé d'un match avec stats et prédictions

Les messages sont formatés avec du texte unicode (compatible WhatsApp et Telegram).
Les caractères spéciaux Telegram (MarkdownV2) sont échappés automatiquement.

Limite WhatsApp : 4096 caractères. Les messages trop longs sont tronqués intelligemment.

Usage:
    formatter = CouponFormatter()
    text = formatter.format(bets=[bet1, bet2, bet3], date=datetime.utcnow())

    alert_fmt = AlertFormatter()
    text = alert_fmt.format(bet=bet1)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class CouponFormatter:
    """Formate le coupon quotidien de value bets."""

    MAX_LENGTH: int = 4096  # Limite WhatsApp

    def format(self, bets: list[Any], date: datetime | None = None) -> str:
        """
        Génère le message texte du coupon quotidien.

        Format généré (voir WHATSAPP_SETUP.md pour l'exemple complet) :
            🎯 APEX BOT — Coupon du DD/MM/YYYY
            [séparateur]
            N. Équipe A vs Équipe B
               Marché : [label]
               Cote : X.XX @ [bookmaker]
               EV : +X.X% | Kelly : X.X%
               Confiance : [étoiles]
            [séparateur]
            📈 EV moyen : +X.X%
            ⚠️ Paris à titre informatif uniquement

        Args:
            bets: Liste de SelectedBet (ou dicts équivalents) à inclure.
            date: Date du coupon (datetime UTC). Utilise utcnow() si None.

        Returns:
            Texte formaté, max 4096 caractères. Tronqué si besoin.
        """
        raise NotImplementedError

    def _format_single_bet(self, bet: Any, index: int) -> str:
        """
        Formate un seul pari pour inclusion dans le coupon.

        Args:
            bet: SelectedBet ou dict avec les champs requis.
            index: Numéro du pari dans le coupon (1-based).

        Returns:
            Bloc de texte pour ce pari (5-7 lignes).
        """
        raise NotImplementedError

    def _confidence_stars(self, confidence: str) -> str:
        """
        Convertit le niveau de confiance en étoiles unicode.

        'low' → '⭐'
        'medium' → '⭐⭐'
        'high' → '⭐⭐⭐'
        """
        raise NotImplementedError

    def _market_label(self, market: str, outcome: str) -> str:
        """
        Retourne un label lisible pour un marché/outcome.

        Exemples :
            ('h2h', 'home') → 'Victoire [équipe domicile]'
            ('totals', 'over_2.5') → 'Plus de 2.5 buts'
            ('btts', 'yes') → 'Les deux équipes marquent'
            ('double_chance', '1X') → 'Domicile ou Nul'

        Args:
            market: Clé du marché ('h2h', 'totals', 'btts', etc.).
            outcome: Outcome spécifique.

        Returns:
            Label français lisible.
        """
        raise NotImplementedError


class AlertFormatter:
    """Formate les alertes value bet unitaires (temps réel ou seuil EV élevé)."""

    def format(self, bet: Any, trigger_reason: str = "value_bet") -> str:
        """
        Génère le message d'alerte pour un seul pari.

        Format généré :
            ⚡ ALERTE VALUE BET
            [match + horaire]
            [marché + cote + EV + Kelly]
            [raison de l'alerte]

        Args:
            bet: SelectedBet ou dict avec les informations du pari.
            trigger_reason: Raison de l'alerte ('value_bet', 'line_movement', 'high_ev').

        Returns:
            Texte de l'alerte, max 1000 caractères.
        """
        raise NotImplementedError


class AnalysisFormatter:
    """Formate l'analyse complète d'un match (stats + prédictions + value bets)."""

    def format(
        self,
        match: Any,
        predictions: list[Any],
        selected_bets: list[Any],
        team_stats: dict[str, Any] | None = None,
    ) -> str:
        """
        Génère l'analyse complète d'un match.

        Format généré :
            🔍 ANALYSE — Équipe A vs Équipe B
            [date + heure + stade]
            [prédictions modèle : victoires, nul, O/U, BTTS]
            [forme récente des deux équipes]
            [H2H]
            [value bets détectés]
            [avertissement]

        Args:
            match: Objet Match SQLAlchemy.
            predictions: Liste de Prediction pour ce match.
            selected_bets: Value bets sélectionnés pour ce match.
            team_stats: Stats supplémentaires des équipes (optionnel).

        Returns:
            Texte de l'analyse, max 4096 caractères.
        """
        raise NotImplementedError

    def _format_form(self, form_string: str) -> str:
        """
        Formate la forme récente en caractères colorés unicode.

        'WWDLW' → 'W W D L W' avec émoticônes si possible.

        Args:
            form_string: Chaîne de 5 résultats ('W', 'D', 'L').

        Returns:
            Chaîne formatée pour l'affichage.
        """
        raise NotImplementedError
