"""
Modèle de prédiction Dixon-Coles pour le football.

Référence : Dixon & Coles (1997). Modèle Poisson bivarié avec correction rho
pour les scores faibles et décroissance temporelle xi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize
from scipy.stats import poisson

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TeamParams:
    team_name: str
    attack: float
    defense: float


@dataclass
class ModelFitResult:
    team_params: dict[str, TeamParams] = field(default_factory=dict)
    home_advantage: float = 1.35
    rho: float = -0.10
    log_likelihood: float = 0.0
    n_matches: int = 0
    convergence: bool = False
    brier_score: float | None = None
    log_loss: float | None = None


class DixonColesModel:
    """
    Implémentation du modèle Dixon-Coles.

    Usage:
        model = DixonColesModel()
        model.fit(historical_matches)
        matrix = model.predict_score_matrix("Arsenal", "Chelsea")
        # matrix[2][1] = P(Arsenal 2 – Chelsea 1)
    """

    MAX_GOALS: int = 10

    def __init__(self, xi: float = 0.0018) -> None:
        self.xi = xi
        self._fit_result: ModelFitResult | None = None

    @property
    def is_fitted(self) -> bool:
        return self._fit_result is not None

    # ─── Calibration ──────────────────────────────────────────────────────────

    def fit(
        self,
        matches: list[dict[str, Any]],
        reference_date: str | datetime | date | None = None,
    ) -> ModelFitResult:
        """
        Calibre le modèle sur des matchs historiques.

        Args:
            matches: [{"home_team", "away_team", "home_score", "away_score", "date"}, ...]
            reference_date: Date de référence pour la décroissance temporelle.
        """
        if not matches:
            raise ValueError("matches list is empty")

        # Référence temporelle
        if reference_date is None:
            ref = date.today()
        elif isinstance(reference_date, datetime):
            ref = reference_date.date()
        elif isinstance(reference_date, str):
            ref = date.fromisoformat(reference_date[:10])
        else:
            ref = reference_date

        # Teams
        teams = sorted(set(
            [m["home_team"] for m in matches] + [m["away_team"] for m in matches]
        ))
        n_teams = len(teams)
        team_idx = {t: i for i, t in enumerate(teams)}

        # Poids temporels
        weights = self._compute_temporal_weights(matches, ref)

        logger.info(
            "Fitting Dixon-Coles",
            n_matches=len(matches),
            n_teams=n_teams,
            xi=self.xi,
        )

        # Paramètres initiaux : attack=1, defense=1, gamma=1.35, rho=-0.1
        # Layout : [alpha_0..alpha_n-1, beta_0..beta_n-1, gamma, rho]
        x0 = np.ones(2 * n_teams + 2)
        x0[-2] = 1.35   # gamma (home advantage)
        x0[-1] = -0.10  # rho

        # Bornes
        bounds = (
            [(0.01, 10.0)] * n_teams      # attack ≥ 0.01
            + [(0.01, 10.0)] * n_teams    # defense ≥ 0.01
            + [(1.0, 3.0)]                # gamma ∈ [1, 3]
            + [(-0.9, 0.0)]               # rho ∈ [-0.9, 0]
        )

        result = minimize(
            fun=self._neg_log_likelihood,
            x0=x0,
            args=(matches, weights, team_idx, n_teams),
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 1000, "ftol": 1e-9},
        )

        # Parse les paramètres optimisés
        attacks = result.x[:n_teams]
        defenses = result.x[n_teams: 2 * n_teams]
        gamma = float(result.x[-2])
        rho = float(result.x[-1])

        team_params = {
            team: TeamParams(team_name=team, attack=float(attacks[i]), defense=float(defenses[i]))
            for team, i in team_idx.items()
        }

        self._fit_result = ModelFitResult(
            team_params=team_params,
            home_advantage=gamma,
            rho=rho,
            log_likelihood=float(-result.fun),
            n_matches=len(matches),
            convergence=result.success,
        )

        logger.info(
            "Dixon-Coles fitted",
            convergence=result.success,
            log_likelihood=round(float(-result.fun), 2),
            gamma=round(gamma, 3),
            rho=round(rho, 3),
        )

        return self._fit_result

    # ─── Prédiction ───────────────────────────────────────────────────────────

    def predict_score_matrix(
        self, home_team: str, away_team: str
    ) -> NDArray[np.float64]:
        """
        Retourne la matrice de probabilités de scores (MAX_GOALS+1) × (MAX_GOALS+1).

        matrix[i][j] = P(home scores i goals, away scores j goals)
        sum(matrix) = 1.0
        """
        if not self.is_fitted or self._fit_result is None:
            raise RuntimeError("Model not fitted. Call fit() first.")

        fr = self._fit_result

        # Si une équipe est inconnue, utiliser des paramètres moyens
        def get_params(team: str) -> TeamParams:
            if team in fr.team_params:
                return fr.team_params[team]
            avg_attack = np.mean([p.attack for p in fr.team_params.values()])
            avg_defense = np.mean([p.defense for p in fr.team_params.values()])
            logger.warning("Unknown team, using average params", team=team)
            return TeamParams(team, float(avg_attack), float(avg_defense))

        home_p = get_params(home_team)
        away_p = get_params(away_team)

        lambda_h = home_p.attack * away_p.defense * fr.home_advantage
        lambda_a = away_p.attack * home_p.defense

        matrix = np.zeros((self.MAX_GOALS + 1, self.MAX_GOALS + 1), dtype=np.float64)

        for i in range(self.MAX_GOALS + 1):
            for j in range(self.MAX_GOALS + 1):
                tau = self._tau(i, j, fr.rho, lambda_h, lambda_a)
                matrix[i][j] = (
                    tau
                    * poisson.pmf(i, lambda_h)
                    * poisson.pmf(j, lambda_a)
                )

        # Normalisation (la somme devrait être très proche de 1 déjà)
        total = matrix.sum()
        if total > 0:
            matrix /= total

        return matrix

    # ─── Méthodes privées ─────────────────────────────────────────────────────

    @staticmethod
    def _tau(
        home_goals: int, away_goals: int, rho: float, lambda_h: float, lambda_a: float
    ) -> float:
        """Facteur de correction Dixon-Coles pour les scores faibles."""
        if home_goals == 0 and away_goals == 0:
            return 1.0 - lambda_h * lambda_a * rho
        if home_goals == 1 and away_goals == 0:
            return 1.0 + lambda_a * rho
        if home_goals == 0 and away_goals == 1:
            return 1.0 + lambda_h * rho
        if home_goals == 1 and away_goals == 1:
            return 1.0 - rho
        return 1.0

    def _neg_log_likelihood(
        self,
        params: NDArray[np.float64],
        matches: list[dict[str, Any]],
        weights: NDArray[np.float64],
        team_idx: dict[str, int],
        n_teams: int,
    ) -> float:
        """Log-vraisemblance négative pondérée (à minimiser)."""
        attacks = params[:n_teams]
        defenses = params[n_teams: 2 * n_teams]
        gamma = params[-2]
        rho = params[-1]

        total = 0.0
        for match, w in zip(matches, weights):
            hi = team_idx.get(match["home_team"], -1)
            ai = team_idx.get(match["away_team"], -1)
            if hi < 0 or ai < 0:
                continue

            lambda_h = attacks[hi] * defenses[ai] * gamma
            lambda_a = attacks[ai] * defenses[hi]
            hg = int(match["home_score"])
            ag = int(match["away_score"])

            tau = self._tau(hg, ag, rho, lambda_h, lambda_a)
            if tau <= 0:
                return 1e10  # Pénalité

            log_p = (
                np.log(tau)
                + poisson.logpmf(hg, lambda_h)
                + poisson.logpmf(ag, lambda_a)
            )
            total += w * log_p

        return -total  # On minimise le négatif

    def _compute_temporal_weights(
        self, matches: list[dict[str, Any]], ref: date
    ) -> NDArray[np.float64]:
        """Calcule exp(-xi * jours) pour chaque match."""
        weights = np.ones(len(matches))
        for i, m in enumerate(matches):
            try:
                match_date_str = str(m.get("date", ""))[:10]
                if match_date_str:
                    match_date = date.fromisoformat(match_date_str)
                    days_ago = max(0, (ref - match_date).days)
                    weights[i] = np.exp(-self.xi * days_ago)
            except Exception:
                weights[i] = 0.5
        return weights

    def to_dict(self) -> dict[str, Any]:
        """Sérialise les paramètres en dict (pour sauvegarde JSON)."""
        if not self._fit_result:
            raise RuntimeError("Model not fitted")
        fr = self._fit_result
        return {
            "xi": self.xi,
            "home_advantage": fr.home_advantage,
            "rho": fr.rho,
            "log_likelihood": fr.log_likelihood,
            "n_matches": fr.n_matches,
            "convergence": fr.convergence,
            "team_params": {
                name: {"attack": p.attack, "defense": p.defense}
                for name, p in fr.team_params.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DixonColesModel":
        """Reconstruit un modèle depuis un dict sérialisé."""
        model = cls(xi=data.get("xi", 0.0018))
        team_params = {
            name: TeamParams(name, v["attack"], v["defense"])
            for name, v in data.get("team_params", {}).items()
        }
        model._fit_result = ModelFitResult(
            team_params=team_params,
            home_advantage=data.get("home_advantage", 1.35),
            rho=data.get("rho", -0.10),
            log_likelihood=data.get("log_likelihood", 0.0),
            n_matches=data.get("n_matches", 0),
            convergence=data.get("convergence", True),
        )
        return model

    def get_team_strengths(self) -> dict[str, dict[str, float]]:
        """Retourne un classement des équipes par force."""
        if not self._fit_result:
            return {}
        result = {}
        for name, p in self._fit_result.team_params.items():
            result[name] = {
                "attack": round(p.attack, 3),
                "defense": round(p.defense, 3),
                "overall": round(p.attack / p.defense, 3),
            }
        return dict(sorted(result.items(), key=lambda x: -x[1]["overall"]))
