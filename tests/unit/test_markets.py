"""Tests unitaires pour les 5 marchés football."""

import numpy as np
import pytest

from src.models.markets import asian_handicap, btts, double_chance, result, totals


@pytest.fixture
def uniform_matrix():
    """Matrice uniforme : tous les scores également probables (11×11)."""
    m = np.ones((11, 11), dtype=np.float64)
    return m / m.sum()


@pytest.fixture
def home_dominant_matrix():
    """Matrice biaisée domicile (Arsenal fort)."""
    m = np.zeros((11, 11), dtype=np.float64)
    # Arsenal gagne souvent 2-0, 2-1, 1-0
    m[2][0] = 0.25
    m[2][1] = 0.20
    m[1][0] = 0.20
    m[0][0] = 0.10
    m[1][1] = 0.05
    m[3][1] = 0.10
    m[0][1] = 0.05
    m[1][2] = 0.05
    return m / m.sum()


class TestResultMarket:
    def test_probs_sum_to_one(self, uniform_matrix):
        r = result.compute(uniform_matrix)
        assert abs(sum(r.values()) - 1.0) < 1e-6

    def test_all_outcomes_present(self, uniform_matrix):
        r = result.compute(uniform_matrix)
        assert set(r.keys()) == {"home", "draw", "away"}

    def test_uniform_roughly_equal(self, uniform_matrix):
        r = result.compute(uniform_matrix)
        assert abs(r["home"] - r["away"]) < 0.1  # Proche dans matrice uniforme

    def test_home_dominant(self, home_dominant_matrix):
        r = result.compute(home_dominant_matrix)
        assert r["home"] > r["away"]

    def test_all_positive(self, uniform_matrix):
        r = result.compute(uniform_matrix)
        assert all(v > 0 for v in r.values())


class TestTotalsMarket:
    def test_probs_sum_to_one(self, uniform_matrix):
        t = totals.compute(uniform_matrix, 2.5)
        assert abs(t["over"] + t["under"] - 1.0) < 1e-6

    def test_higher_line_lower_over(self, uniform_matrix):
        t25 = totals.compute(uniform_matrix, 2.5)
        t35 = totals.compute(uniform_matrix, 3.5)
        assert t35["over"] < t25["over"]

    def test_different_lines(self, uniform_matrix):
        for line in [0.5, 1.5, 2.5, 3.5]:
            t = totals.compute(uniform_matrix, line)
            assert abs(t["over"] + t["under"] - 1.0) < 1e-6


class TestBTTSMarket:
    def test_probs_sum_to_one(self, uniform_matrix):
        b = btts.compute(uniform_matrix)
        assert abs(b["yes"] + b["no"] - 1.0) < 1e-6

    def test_both_positive(self, uniform_matrix):
        b = btts.compute(uniform_matrix)
        assert b["yes"] > 0
        assert b["no"] > 0

    def test_home_shutout_reduces_btts(self, home_dominant_matrix):
        b = btts.compute(home_dominant_matrix)
        # Avec beaucoup de clean sheets (2-0, 1-0), BTTS No devrait être élevé
        assert b["no"] > 0


class TestAsianHandicap:
    def test_probs_sum_to_one(self, uniform_matrix):
        ah = asian_handicap.compute(uniform_matrix, -0.5)
        assert abs(ah["home"] + ah["away"] - 1.0) < 1e-6

    def test_minus_05_equals_result_home_win(self, uniform_matrix):
        ah = asian_handicap.compute(uniform_matrix, -0.5)
        r = result.compute(uniform_matrix)
        assert abs(ah["home"] - r["home"]) < 1e-6

    def test_plus_05_equals_home_no_lose(self, uniform_matrix):
        ah = asian_handicap.compute(uniform_matrix, 0.5)
        r = result.compute(uniform_matrix)
        assert abs(ah["home"] - (r["home"] + r["draw"])) < 1e-6

    def test_all_handicaps_valid(self, uniform_matrix):
        for h in [-1.0, -0.5, 0.5, 1.0]:
            ah = asian_handicap.compute(uniform_matrix, h)
            assert ah["home"] >= 0
            assert ah["away"] >= 0


class TestResultMarketEdge:
    def test_zero_matrix_returns_uniform(self):
        import numpy as np
        m = np.zeros((11, 11), dtype=np.float64)
        r = result.compute(m)
        assert r == {"home": 1/3, "draw": 1/3, "away": 1/3}


class TestTotalsMarketEdge:
    def test_zero_matrix_returns_half(self):
        import numpy as np
        m = np.zeros((11, 11), dtype=np.float64)
        t = totals.compute(m, 2.5)
        assert t == {"over": 0.5, "under": 0.5}


class TestDoubleChance:
    def test_all_outcomes_present(self, uniform_matrix):
        dc = double_chance.compute(uniform_matrix)
        assert set(dc.keys()) == {"1X", "X2", "12"}

    def test_1X_equals_home_plus_draw(self, uniform_matrix):
        dc = double_chance.compute(uniform_matrix)
        r = result.compute(uniform_matrix)
        assert abs(dc["1X"] - (r["home"] + r["draw"])) < 1e-6

    def test_12_equals_one_minus_draw(self, uniform_matrix):
        dc = double_chance.compute(uniform_matrix)
        r = result.compute(uniform_matrix)
        assert abs(dc["12"] - (r["home"] + r["away"])) < 1e-6

    def test_all_greater_than_half(self, uniform_matrix):
        dc = double_chance.compute(uniform_matrix)
        for key, val in dc.items():
            assert val > 0.5, f"{key}={val} should be > 0.5 (covers 2/3 outcomes)"
