"""
Sélection finale des value bets pour le coupon quotidien.

Le ValueBetSelector applique des filtres et classe les paris selon leur valeur.
Il est le dernier composant avant la messagerie.

Pipeline de sélection :
    1. Recevoir toutes les prédictions du jour (table predictions)
    2. Filtrer : EV > EV_THRESHOLD, MIN_ODDS ≤ odds ≤ MAX_ODDS
    3. Calculer le Kelly pour chaque pari qualifié
    4. Filtrer : Kelly ≥ MIN_KELLY (évite les mises trop faibles)
    5. Classer par EV décroissant
    6. Garder les MAX_BETS_PER_DAY meilleurs paris
    7. Retourner la liste des SelectedBet

Usage:
    selector = ValueBetSelector()
    selected = selector.select_daily_bets(predictions, odds_data)
    # → [SelectedBet, SelectedBet, ...]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SelectedBet:
    """
    Un pari sélectionné pour inclusion dans le coupon quotidien.

    Contient toutes les informations nécessaires pour le formatage du message
    et la sauvegarde en base de données.
    """

    match_name: str               # "Arsenal vs Chelsea"
    league: str                   # "EPL"
    kickoff_utc: Any              # datetime UTC
    market: str                   # "h2h"
    outcome: str                  # "home"
    outcome_label: str            # "Arsenal" (label lisible pour le message)
    bookmaker: str                # "bet365"
    odds: float                   # 2.10
    model_prob: float             # 0.52
    fair_odds: float              # 2.25 (après démarginisation)
    ev: float                     # 0.092 (+9.2%)
    kelly_pct: float              # 0.032 (3.2% de bankroll)
    confidence: str               # "high"
    prediction_id: int | None = None  # ID en base pour le tracking

    @property
    def ev_pct(self) -> str:
        """Retourne l'EV formaté en % (ex: '+9.2%')."""
        return f"+{self.ev * 100:.1f}%" if self.ev > 0 else f"{self.ev * 100:.1f}%"

    @property
    def kelly_pct_str(self) -> str:
        """Retourne le Kelly formaté en % (ex: '3.2%')."""
        return f"{self.kelly_pct * 100:.1f}%"


class ValueBetSelector:
    """
    Sélectionne et classe les meilleurs value bets du jour.

    Paramètres de sélection configurés depuis Settings :
    - EV_THRESHOLD : EV minimum pour sélection (+5% par défaut)
    - MIN_ODDS : Cote minimum (1.50)
    - MAX_ODDS : Cote maximum (5.00)
    - MAX_BETS_PER_DAY : Nombre maximum de paris dans le coupon (5)
    - KELLY_FRACTION : Fraction Kelly appliquée (0.25)
    """

    MIN_KELLY_PCT: float = 0.005  # 0.5% minimum de bankroll recommandé

    def __init__(self) -> None:
        """Initialise le selector avec les paramètres depuis Settings."""
        raise NotImplementedError

    def select_daily_bets(
        self,
        predictions: list[Any],
        odds_by_match: dict[str, list[dict]],
    ) -> list[SelectedBet]:
        """
        Sélectionne les meilleurs value bets du jour à partir des prédictions.

        Args:
            predictions: Liste d'objets Prediction depuis la base de données.
            odds_by_match: Dict {match_external_id: [{"bookmaker": ..., "outcomes": [...]}]}
                          Cotes actuelles depuis The Odds API.

        Returns:
            Liste de SelectedBet triée par EV décroissant, max MAX_BETS_PER_DAY.
        """
        raise NotImplementedError

    def _apply_filters(self, candidates: list[SelectedBet]) -> list[SelectedBet]:
        """
        Applique les filtres de sélection sur les candidats.

        Filtres appliqués (dans l'ordre) :
        1. EV ≥ EV_THRESHOLD
        2. MIN_ODDS ≤ odds ≤ MAX_ODDS
        3. Kelly ≥ MIN_KELLY_PCT

        Args:
            candidates: Liste non filtrée de paris candidats.

        Returns:
            Liste filtrée (peut être vide si aucun pari ne passe).
        """
        raise NotImplementedError

    def _score_bet(self, bet: SelectedBet) -> float:
        """
        Calcule un score composite pour le classement des paris.

        Score = EV × 0.7 + Kelly × 0.3
        (EV est le critère principal, Kelly évite les mises trop risquées)

        Args:
            bet: Pari candidat.

        Returns:
            Score composite (plus élevé = meilleur pari).
        """
        raise NotImplementedError

    def _assign_confidence(self, ev: float, model_prob: float, n_historical_matches: int) -> str:
        """
        Attribue un niveau de confiance basé sur plusieurs facteurs.

        Logique :
        - 'high' : EV > 10% ET n_historical_matches > 50
        - 'medium' : EV entre 5% et 10%, ou n_historical_matches entre 20 et 50
        - 'low' : EV entre 3% et 5% ou données insuffisantes

        Args:
            ev: Expected value du pari.
            model_prob: Probabilité modèle.
            n_historical_matches: Nombre de matchs historiques ayant servi à calibrer.

        Returns:
            'low', 'medium', ou 'high'.
        """
        raise NotImplementedError
