"""Tests unitaires pour ValueCalculator."""

import pytest
from src.selection.value_calculator import ValueCalculator


@pytest.fixture
def calc():
    return ValueCalculator()


class TestDemarginPower:
    def test_probabilities_sum_to_one(self, calc):
        result = calc.demargin_power([2.10, 3.50, 3.20])
        assert abs(sum(result.true_probs) - 1.0) < 1e-6

    def test_overround_positive(self, calc):
        result = calc.demargin_power([2.10, 3.50, 3.20])
        assert result.overround > 0

    def test_fair_odds_greater_than_bookie_odds(self, calc):
        result = calc.demargin_power([2.10, 3.50, 3.20])
        for fair, bookie in zip(result.fair_odds, [2.10, 3.50, 3.20]):
            assert fair >= bookie  # Fair odds >= bookie odds (marge retirée)

    def test_two_outcomes(self, calc):
        result = calc.demargin_power([1.85, 1.95])
        assert abs(sum(result.true_probs) - 1.0) < 1e-6

    def test_invalid_odds_raises(self, calc):
        with pytest.raises(ValueError):
            calc.demargin_power([0.5, 2.0])

    def test_single_outcome_no_crash(self, calc):
        # Une seule cote → pas de marge calculable
        result = calc.demargin_power([2.10])
        assert len(result.true_probs) == 1

    def test_method_label(self, calc):
        result = calc.demargin_power([2.10, 3.50, 3.20])
        assert result.method in ("power", "additive")


class TestCalculateEV:
    def test_positive_ev(self, calc):
        ev = calc.calculate_ev(0.52, 2.10)
        assert ev == pytest.approx(0.092, abs=1e-3)
        assert ev > 0

    def test_negative_ev(self, calc):
        ev = calc.calculate_ev(0.30, 2.10)
        assert ev < 0

    def test_zero_ev(self, calc):
        ev = calc.calculate_ev(1 / 2.10, 2.10)
        assert abs(ev) < 1e-4

    def test_invalid_prob_raises(self, calc):
        with pytest.raises(ValueError):
            calc.calculate_ev(0.0, 2.10)
        with pytest.raises(ValueError):
            calc.calculate_ev(1.0, 2.10)

    def test_invalid_odds_raises(self, calc):
        with pytest.raises(ValueError):
            calc.calculate_ev(0.5, 0.9)


class TestComputeOverround:
    def test_typical_h2h(self, calc):
        vig = calc.compute_overround([2.10, 3.50, 3.20])
        assert 0.05 < vig < 0.15  # Marge typique 5-15%

    def test_50_50_market(self, calc):
        vig = calc.compute_overround([1.90, 1.90])
        assert vig == pytest.approx(2 / 1.90 - 1, abs=1e-6)

    def test_empty_odds_returns_zero(self, calc):
        assert calc.compute_overround([]) == 0.0


class TestEdgeCases:
    """Edge cases pour les branches rarement couvertes."""

    def test_demargin_power_fair_odds_no_margin(self, calc):
        """Overround <= 0 → retourne les implied directement (ligne 52)."""
        # Cotes exactement fair : 1/0.5 + 1/0.5 = 2.0 → sum implied = 1.0
        result = calc.demargin_power([2.0, 2.0])
        # Overround = 0, so method still runs but hits the <= 0 branch
        assert abs(sum(result.true_probs) - 1.0) < 1e-6

    def test_demargin_additive_invalid_odds_raises(self, calc):
        """demargin_additive avec cote ≤ 1.0 doit lever ValueError (ligne 87)."""
        with pytest.raises(ValueError):
            calc.demargin_additive([0.5, 2.0])

    def test_demargin_additive_empty_raises(self, calc):
        """demargin_additive avec liste vide doit lever ValueError (ligne 87)."""
        with pytest.raises(ValueError):
            calc.demargin_additive([])

    def test_calculate_ev_from_fair_odds(self, calc):
        """calculate_ev_from_fair_odds appelle calculate_ev (ligne 120)."""
        ev = calc.calculate_ev_from_fair_odds(0.52, 2.10)
        assert ev == pytest.approx(0.092, abs=1e-3)


class TestKellyDefaultBankroll:
    def test_calculate_units_uses_default_bankroll(self):
        """calculate_units sans bankroll utilise settings.BANKROLL_UNITS (ligne 40)."""
        from src.selection.kelly import KellyCriterion
        kelly = KellyCriterion(fraction=0.25)
        # Should not raise, uses default bankroll from settings
        units = kelly.calculate_units(0.52, 2.10)
        assert units >= 0


class TestBestOddsAcrossBookmakers:
    """Tests pour best_odds_across_bookmakers."""

    @pytest.fixture
    def bookmakers_data(self):
        return [
            {
                "key": "bet365",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.10},
                            {"name": "Chelsea", "price": 3.50},
                            {"name": "Draw", "price": 3.20},
                        ],
                    }
                ],
            },
            {
                "key": "unibet",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.20},
                            {"name": "Chelsea", "price": 3.40},
                            {"name": "Draw", "price": 3.10},
                        ],
                    }
                ],
            },
        ]

    def test_finds_best_price(self, calc, bookmakers_data):
        bookie, price = calc.best_odds_across_bookmakers("Arsenal", bookmakers_data)
        assert price == 2.20  # unibet offers better
        assert bookie == "unibet"

    def test_finds_draw(self, calc, bookmakers_data):
        bookie, price = calc.best_odds_across_bookmakers("Draw", bookmakers_data)
        assert price == 3.20
        assert bookie == "bet365"

    def test_case_insensitive_match(self, calc, bookmakers_data):
        bookie, price = calc.best_odds_across_bookmakers("arsenal", bookmakers_data)
        assert price == 2.20

    def test_unknown_outcome_raises(self, calc, bookmakers_data):
        with pytest.raises(ValueError, match="No odds found"):
            calc.best_odds_across_bookmakers("UnknownTeam", bookmakers_data)

    def test_empty_bookmakers_raises(self, calc):
        with pytest.raises(ValueError):
            calc.best_odds_across_bookmakers("Arsenal", [])

    def test_outcome_with_description(self, calc):
        data = [
            {
                "key": "bet365",
                "markets": [
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "description": "2.5", "price": 1.90},
                            {"name": "Under", "description": "2.5", "price": 1.95},
                        ],
                    }
                ],
            }
        ]
        bookie, price = calc.best_odds_across_bookmakers("Over 2.5", data)
        assert bookie == "bet365"
        assert price == 1.90
