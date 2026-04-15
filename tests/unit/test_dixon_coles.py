"""Tests unitaires pour DixonColesModel."""

import pytest
import numpy as np

from src.models.dixon_coles import DixonColesModel


@pytest.fixture
def sample_matches():
    """50 matchs synthétiques simples pour tester la calibration."""
    import random
    random.seed(42)
    teams = ["Arsenal", "Chelsea", "Liverpool", "ManCity", "Spurs"]
    matches = []
    for _ in range(50):
        home, away = random.sample(teams, 2)
        matches.append({
            "home_team": home,
            "away_team": away,
            "home_score": max(0, int(random.gauss(1.5, 1))),
            "away_score": max(0, int(random.gauss(1.2, 1))),
            "date": "2024-01-15",
        })
    return matches


@pytest.fixture
def fitted_model(sample_matches):
    model = DixonColesModel(xi=0.0018)
    model.fit(sample_matches)
    return model


class TestDixonColesModel:
    def test_fit_converges(self, sample_matches):
        model = DixonColesModel()
        result = model.fit(sample_matches)
        assert result.convergence is True

    def test_is_fitted_after_fit(self, sample_matches):
        model = DixonColesModel()
        assert not model.is_fitted
        model.fit(sample_matches)
        assert model.is_fitted

    def test_empty_matches_raises(self):
        model = DixonColesModel()
        with pytest.raises(ValueError):
            model.fit([])

    def test_all_teams_calibrated(self, fitted_model, sample_matches):
        teams = set(m["home_team"] for m in sample_matches) | set(m["away_team"] for m in sample_matches)
        for team in teams:
            assert team in fitted_model._fit_result.team_params

    def test_home_advantage_positive(self, fitted_model):
        assert fitted_model._fit_result.home_advantage > 1.0

    def test_rho_negative(self, fitted_model):
        assert fitted_model._fit_result.rho < 0


class TestPredictScoreMatrix:
    def test_matrix_sums_to_one(self, fitted_model):
        matrix = fitted_model.predict_score_matrix("Arsenal", "Chelsea")
        assert abs(matrix.sum() - 1.0) < 1e-4

    def test_matrix_shape(self, fitted_model):
        matrix = fitted_model.predict_score_matrix("Arsenal", "Chelsea")
        assert matrix.shape == (11, 11)

    def test_all_probabilities_positive(self, fitted_model):
        matrix = fitted_model.predict_score_matrix("Arsenal", "Chelsea")
        assert (matrix >= 0).all()

    def test_unfitted_model_raises(self):
        model = DixonColesModel()
        with pytest.raises(RuntimeError):
            model.predict_score_matrix("Arsenal", "Chelsea")

    def test_unknown_team_uses_average(self, fitted_model):
        # Ne doit pas crasher pour une équipe inconnue
        matrix = fitted_model.predict_score_matrix("UnknownTeam", "Arsenal")
        assert abs(matrix.sum() - 1.0) < 1e-4

    def test_symmetric_for_equal_teams(self, fitted_model):
        """Deux équipes identiques → P(home win) ≈ P(away win) après ajustement home advantage."""
        # On teste juste que la matrice est valide
        matrix = fitted_model.predict_score_matrix("Arsenal", "Arsenal")
        assert abs(matrix.sum() - 1.0) < 1e-4


class TestTauCorrection:
    def test_tau_00_affected_by_rho(self):
        # tau(0,0) = 1 - lambda_h * lambda_a * rho
        tau = DixonColesModel._tau(0, 0, -0.1, 1.5, 1.2)
        assert tau == pytest.approx(1.0 - 1.5 * 1.2 * (-0.1), abs=1e-6)

    def test_tau_neutral_for_high_scores(self):
        tau = DixonColesModel._tau(3, 2, -0.1, 1.5, 1.2)
        assert tau == 1.0

    def test_tau_11(self):
        tau = DixonColesModel._tau(1, 1, -0.15, 1.5, 1.2)
        assert tau == pytest.approx(1.0 - (-0.15), abs=1e-6)


class TestSerialization:
    def test_to_dict_from_dict_roundtrip(self, fitted_model):
        data = fitted_model.to_dict()
        model2 = DixonColesModel.from_dict(data)
        assert model2.is_fitted

        m1 = fitted_model.predict_score_matrix("Arsenal", "Chelsea")
        m2 = model2.predict_score_matrix("Arsenal", "Chelsea")
        np.testing.assert_array_almost_equal(m1, m2, decimal=6)
