"""
Démarginisation des cotes et calcul d'expected value.
"""

from __future__ import annotations

from dataclasses import dataclass

from scipy.optimize import brentq

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DeMarginResult:
    true_probs: list[float]
    fair_odds: list[float]
    overround: float
    method: str


class ValueCalculator:
    """Calcule la value des paris sportifs."""

    def demargin_power(self, odds: list[float]) -> DeMarginResult:
        """
        Retire la marge bookmaker via la méthode 'power'.

        Trouve k tel que : sum((1/odd_i)^k) = 1
        true_prob_i = (1/odd_i)^k
        """
        if not odds or any(o <= 1.0 for o in odds):
            raise ValueError(f"All odds must be > 1.0, got: {odds}")

        if len(odds) < 2:
            # Pas assez d'outcomes pour calculer une marge → retourner sans modification
            implied = [1.0 / o for o in odds]
            return DeMarginResult(
                true_probs=implied,
                fair_odds=odds[:],
                overround=0.0,
                method="power",
            )

        implied = [1.0 / o for o in odds]
        overround = sum(implied) - 1.0

        if overround <= 0:
            # Pas de marge → retourner les implied directement
            return DeMarginResult(
                true_probs=implied,
                fair_odds=odds,
                overround=0.0,
                method="power",
            )

        def equation(k: float) -> float:
            return sum(p ** k for p in implied) - 1.0

        try:
            k = brentq(equation, 0.1, 3.0, xtol=1e-8)
        except ValueError:
            # Fallback sur la méthode additive
            logger.warning("Power method failed, falling back to additive")
            return self.demargin_additive(odds)

        true_probs = [p ** k for p in implied]
        # Normaliser pour s'assurer que sum = 1.0
        total = sum(true_probs)
        true_probs = [p / total for p in true_probs]
        fair_odds = [1.0 / p if p > 0 else 999.0 for p in true_probs]

        return DeMarginResult(
            true_probs=true_probs,
            fair_odds=fair_odds,
            overround=overround,
            method="power",
        )

    def demargin_additive(self, odds: list[float]) -> DeMarginResult:
        """
        Retire la marge bookmaker via la méthode additive (soustraction uniforme).
        """
        if not odds or any(o <= 1.0 for o in odds):
            raise ValueError(f"All odds must be > 1.0, got: {odds}")

        implied = [1.0 / o for o in odds]
        overround = sum(implied) - 1.0
        n = len(odds)
        margin_per_outcome = overround / n

        true_probs = [max(0.001, p - margin_per_outcome) for p in implied]
        total = sum(true_probs)
        true_probs = [p / total for p in true_probs]
        fair_odds = [1.0 / p if p > 0 else 999.0 for p in true_probs]

        return DeMarginResult(
            true_probs=true_probs,
            fair_odds=fair_odds,
            overround=overround,
            method="additive",
        )

    def calculate_ev(self, model_prob: float, bookmaker_odds: float) -> float:
        """
        EV = model_prob × bookmaker_odds − 1

        Exemple : P=0.52, cote=2.10 → EV = 0.092 (+9.2%)
        """
        if not (0 < model_prob < 1):
            raise ValueError(f"model_prob must be in ]0, 1[, got {model_prob}")
        if bookmaker_odds <= 1.0:
            raise ValueError(f"bookmaker_odds must be > 1.0, got {bookmaker_odds}")
        return model_prob * bookmaker_odds - 1.0

    def calculate_ev_from_fair_odds(self, model_prob: float, fair_odds: float) -> float:
        """EV par rapport aux cotes fair (plus conservateur)."""
        return self.calculate_ev(model_prob, fair_odds)

    def best_odds_across_bookmakers(
        self, outcome_name: str, bookmakers_data: list[dict]
    ) -> tuple[str, float]:
        """
        Trouve la meilleure cote pour un outcome parmi tous les bookmakers.

        Args:
            outcome_name: Nom de l'outcome à chercher (ex: "Arsenal", "Over 2.5").
            bookmakers_data: Liste de bookmakers au format The Odds API.

        Returns:
            (bookmaker_key, best_price)
        """
        best_price = 0.0
        best_bookie = ""

        for bookie in bookmakers_data:
            bookie_key = bookie.get("key", "")
            for market in bookie.get("markets", []):
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name", "")
                    desc = outcome.get("description", "")
                    # Match sur le nom ou la description
                    full_name = f"{name} {desc}".strip() if desc else name
                    if (
                        outcome_name.lower() in name.lower()
                        or outcome_name.lower() in full_name.lower()
                    ):
                        price = float(outcome.get("price", 0))
                        if price > best_price:
                            best_price = price
                            best_bookie = bookie_key

        if best_price == 0.0:
            raise ValueError(f"No odds found for outcome '{outcome_name}'")

        return best_bookie, best_price

    def compute_overround(self, odds: list[float]) -> float:
        """Calcule la marge du bookmaker : sum(1/odd) - 1."""
        if not odds:
            return 0.0
        return sum(1.0 / o for o in odds if o > 1.0) - 1.0
