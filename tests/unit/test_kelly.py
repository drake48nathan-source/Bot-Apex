"""Tests unitaires pour KellyCriterion."""

import pytest
from src.selection.kelly import KellyCriterion


@pytest.fixture
def kelly():
    return KellyCriterion(fraction=0.25)


class TestKellyCalculate:
    def test_positive_ev_returns_positive(self, kelly):
        k = kelly.calculate(0.52, 2.10)
        assert k > 0

    def test_negative_ev_returns_zero(self, kelly):
        k = kelly.calculate(0.30, 2.10)  # EV = 0.30*2.10-1 = -0.37
        assert k == 0.0

    def test_fraction_applied(self, kelly):
        # p=0.52, odds=2.10 → raw Kelly ≈ 8.4% (below 10% cap for both fractions)
        full = KellyCriterion(fraction=1.0)
        quarter = KellyCriterion(fraction=0.25)
        full_k = full.calculate(0.52, 2.10)
        quarter_k = quarter.calculate(0.52, 2.10)
        assert quarter_k == pytest.approx(full_k * 0.25, abs=1e-6)

    def test_max_stake_cap(self, kelly):
        # Même avec une grosse edge, la mise est plafonnée à 10%
        k = kelly.calculate(0.99, 10.0)
        assert k <= kelly.MAX_STAKE_PCT

    def test_invalid_prob_returns_zero(self, kelly):
        assert kelly.calculate(0.0, 2.0) == 0.0
        assert kelly.calculate(1.0, 2.0) == 0.0

    def test_invalid_odds_returns_zero(self, kelly):
        assert kelly.calculate(0.5, 1.0) == 0.0
        assert kelly.calculate(0.5, 0.5) == 0.0


class TestKellyCalculateUnits:
    def test_units_proportional_to_bankroll(self, kelly):
        u100 = kelly.calculate_units(0.52, 2.10, bankroll=100)
        u200 = kelly.calculate_units(0.52, 2.10, bankroll=200)
        assert u200 == pytest.approx(u100 * 2, abs=1e-6)

    def test_returns_zero_for_negative_ev(self, kelly):
        assert kelly.calculate_units(0.20, 2.10, bankroll=100) == 0.0
