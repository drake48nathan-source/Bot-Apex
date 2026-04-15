"""Kelly Criterion fractionné pour le dimensionnement des mises."""

from __future__ import annotations

from src.core.config import settings


class KellyCriterion:
    """Calcule les mises optimales selon le Kelly Criterion."""

    MAX_STAKE_PCT: float = 0.10  # 10% de bankroll maximum par pari

    def __init__(self, fraction: float | None = None) -> None:
        self.fraction = fraction if fraction is not None else settings.KELLY_FRACTION

    def calculate(self, model_prob: float, odds: float) -> float:
        """
        Fraction de bankroll à miser (fraction-Kelly).

        f* = (p * b - q) / b  où b = odds - 1, q = 1 - p
        stake = f* × fraction

        Returns:
            Fraction [0, MAX_STAKE_PCT]. 0.0 si EV négatif.
        """
        if model_prob <= 0 or model_prob >= 1 or odds <= 1.0:
            return 0.0
        b = odds - 1.0
        q = 1.0 - model_prob
        full_kelly = (model_prob * b - q) / b
        if full_kelly <= 0:
            return 0.0
        return min(full_kelly * self.fraction, self.MAX_STAKE_PCT)

    def calculate_units(
        self, model_prob: float, odds: float, bankroll: float | None = None
    ) -> float:
        """Retourne la mise en unités absolues."""
        if bankroll is None:
            bankroll = settings.BANKROLL_UNITS
        return self.calculate(model_prob, odds) * bankroll

    def full_kelly(self, model_prob: float, odds: float) -> float:
        """Kelly complet sans fraction (informatif seulement)."""
        if model_prob <= 0 or model_prob >= 1 or odds <= 1.0:
            return 0.0
        b = odds - 1.0
        q = 1.0 - model_prob
        return max(0.0, (model_prob * b - q) / b)
