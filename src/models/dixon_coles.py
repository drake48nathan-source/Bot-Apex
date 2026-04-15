"""
Modèle de prédiction Dixon-Coles pour le football.

Référence académique : Dixon, M.J. & Coles, S.G. (1997).
"Modelling Association Football Scores and Inefficiencies in the Football Betting Market."
Journal of the Royal Statistical Society, Series C, 46(2), 265-280.

Le modèle fait les hypothèses suivantes :
- Le nombre de buts marqués par chaque équipe suit une distribution de Poisson
- Les paramètres d'attaque (alpha) et de défense (beta) sont propres à chaque équipe
- Un avantage à domicile (gamma) est global à toutes les équipes
- Une correction (rho) est appliquée pour les scores faibles (0-0, 1-0, 0-1, 1-1)
  qui sont sous/sur-représentés par rapport à une distribution Poisson pure
- Les matchs récents sont pondérés plus fortement via un paramètre de décroissance (xi)

Paramètres du modèle :
- alpha_i  : force d'attaque de l'équipe i (>0)
- beta_i   : force défensive de l'équipe i (>0, petit = bonne défense)
- gamma    : facteur d'avantage à domicile (>1 typiquement)
- rho      : paramètre de correction Dixon-Coles (typiquement -0.1 à -0.2)

Prédiction :
    lambda_home = alpha_home * beta_away * gamma
    lambda_away = alpha_away * beta_home

    P(home=i, away=j) = tau(i,j,rho) * Poisson(i, lambda_home) * Poisson(j, lambda_away)

Usage:
    model = DixonColesModel()
    model.fit(historical_matches_df)
    score_matrix = model.predict_score_matrix("Arsenal", "Chelsea")
    # score_matrix[2][1] = P(Arsenal 2 - Chelsea 1)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass
class TeamParams:
    """
    Paramètres Dixon-Coles calibrés pour une équipe.

    Attributes:
        team_name: Nom de l'équipe (doit correspondre aux noms dans les matchs).
        attack: Force offensive alpha_i. Valeur > 1 = bonne attaque, < 1 = faible.
        defense: Force défensive beta_i. Valeur < 1 = bonne défense, > 1 = faible.
    """

    team_name: str
    attack: float
    defense: float


@dataclass
class ModelFitResult:
    """
    Résultat de la calibration du modèle.

    Attributes:
        team_params: Dictionnaire {team_name: TeamParams} pour chaque équipe.
        home_advantage: Facteur d'avantage à domicile (gamma).
        rho: Paramètre de correction Dixon-Coles.
        log_likelihood: Log-vraisemblance finale (meilleur = plus proche de 0).
        n_matches: Nombre de matchs utilisés pour l'entraînement.
        convergence: True si l'optimiseur scipy a convergé normalement.
        brier_score: Score de Brier sur les données de validation (si disponibles).
        log_loss: Log-loss sur les données de validation (si disponibles).
    """

    team_params: dict[str, TeamParams] = field(default_factory=dict)
    home_advantage: float = 1.0
    rho: float = -0.1
    log_likelihood: float = 0.0
    n_matches: int = 0
    convergence: bool = False
    brier_score: float | None = None
    log_loss: float | None = None


class DixonColesModel:
    """
    Implémentation du modèle Dixon-Coles pour la prédiction de scores football.

    Ce modèle doit être calibré (fit) avant de pouvoir faire des prédictions.
    Les paramètres calibrés peuvent être sauvegardés/chargés depuis la base de données.
    """

    MAX_GOALS: int = 10
    """Score maximum considéré dans la matrice de probabilités (0 à MAX_GOALS)."""

    def __init__(self, xi: float = 0.0018) -> None:
        """
        Initialise le modèle avec le paramètre de décroissance temporelle.

        Args:
            xi: Paramètre de décroissance temporelle ξ. Un match joué il y a
                T jours a un poids de exp(-xi * T). Valeur typique : 0.0018
                (les matchs de plus de 3 ans ont un poids quasi nul).
        """
        self.xi = xi
        self._fit_result: ModelFitResult | None = None

    @property
    def is_fitted(self) -> bool:
        """Retourne True si le modèle a été calibré."""
        return self._fit_result is not None

    def fit(self, matches: list[dict[str, Any]], reference_date: str | None = None) -> ModelFitResult:
        """
        Calibre le modèle Dixon-Coles sur des données historiques de matchs.

        Utilise scipy.optimize.minimize (méthode L-BFGS-B) pour maximiser
        la log-vraisemblance pondérée par la décroissance temporelle.

        Args:
            matches: Liste de dicts avec les clés :
                - "home_team" (str) : nom équipe domicile
                - "away_team" (str) : nom équipe extérieure
                - "home_score" (int) : buts marqués à domicile
                - "away_score" (int) : buts encaissés à domicile
                - "date" (str | datetime) : date du match
            reference_date: Date de référence pour la décroissance temporelle.
                           Si None, utilise la date du jour.

        Returns:
            ModelFitResult avec les paramètres calibrés et les métriques.

        Raises:
            ValueError: Si `matches` est vide ou si les données sont mal formées.
            RuntimeError: Si l'optimisation scipy échoue à converger.
        """
        raise NotImplementedError

    def predict_score_matrix(
        self, home_team: str, away_team: str
    ) -> NDArray[np.float64]:
        """
        Calcule la matrice de probabilités de scores pour un match.

        Retourne une matrice (MAX_GOALS+1) x (MAX_GOALS+1) où l'élément [i][j]
        représente la probabilité que l'équipe domicile marque i buts et
        l'équipe extérieure marque j buts.

        La correction Dixon-Coles (tau) est appliquée pour les scores faibles.
        La somme de tous les éléments de la matrice est égale à 1.0.

        Args:
            home_team: Nom de l'équipe domicile (doit être dans les paramètres calibrés).
            away_team: Nom de l'équipe extérieure (doit être dans les paramètres calibrés).

        Returns:
            Matrice numpy de forme (MAX_GOALS+1, MAX_GOALS+1) avec dtype float64.

        Raises:
            RuntimeError: Si le modèle n'a pas encore été calibré (is_fitted == False).
            KeyError: Si home_team ou away_team n'est pas dans les équipes calibrées.
        """
        raise NotImplementedError

    def _compute_lambda(self, home_team: str, away_team: str) -> tuple[float, float]:
        """
        Calcule les taux de Poisson (lambda) pour les deux équipes.

        lambda_home = alpha_home * beta_away * gamma
        lambda_away = alpha_away * beta_home

        Args:
            home_team: Nom de l'équipe domicile.
            away_team: Nom de l'équipe extérieure.

        Returns:
            Tuple (lambda_home, lambda_away).
        """
        raise NotImplementedError

    @staticmethod
    def _tau(home_goals: int, away_goals: int, rho: float, lambda_h: float, lambda_a: float) -> float:
        """
        Facteur de correction Dixon-Coles pour les scores faibles.

        Corrige la déviation par rapport à la distribution de Poisson pure
        pour les quatre scores faibles : 0-0, 1-0, 0-1, 1-1.

        La formule exacte est :
            tau(0,0) = 1 - lambda_h * lambda_a * rho
            tau(1,0) = 1 + lambda_a * rho
            tau(0,1) = 1 + lambda_h * rho
            tau(1,1) = 1 - rho
            tau(i,j) = 1 pour tous les autres scores

        Args:
            home_goals: Buts de l'équipe domicile.
            away_goals: Buts de l'équipe extérieure.
            rho: Paramètre de correction (typiquement négatif).
            lambda_h: Taux Poisson équipe domicile.
            lambda_a: Taux Poisson équipe extérieure.

        Returns:
            Facteur tau (float) à appliquer à la probabilité Poisson.
        """
        raise NotImplementedError

    def _log_likelihood(self, params: NDArray[np.float64], matches: list[dict], weights: NDArray[np.float64]) -> float:
        """
        Calcule la log-vraisemblance négative du modèle (à minimiser).

        Utilisée par scipy.optimize.minimize comme fonction objectif.
        Applique les poids temporels pour donner plus d'importance aux matchs récents.

        Args:
            params: Vecteur de paramètres aplati [alpha_1, ..., alpha_n, beta_1, ..., beta_n, gamma, rho].
            matches: Liste des matchs historiques.
            weights: Vecteur de poids temporels (exp(-xi * days_ago)).

        Returns:
            Log-vraisemblance négative (float). Plus proche de 0 = meilleur modèle.
        """
        raise NotImplementedError

    def _compute_temporal_weights(
        self, matches: list[dict], reference_date: Any
    ) -> NDArray[np.float64]:
        """
        Calcule les poids de décroissance temporelle pour chaque match.

        weight_i = exp(-xi * days_since_match_i)

        Les matchs récents ont un poids proche de 1.0.
        Les matchs anciens ont un poids proche de 0.0.

        Args:
            matches: Liste des matchs avec leurs dates.
            reference_date: Date de référence pour le calcul de l'ancienneté.

        Returns:
            Tableau numpy de poids, de même longueur que `matches`.
        """
        raise NotImplementedError

    def save_params(self, db_session: Any, league: str, version: str = "v1") -> None:
        """
        Sauvegarde les paramètres calibrés en base de données (table model_params).

        Sérialise le ModelFitResult en JSON et l'enregistre avec les métadonnées
        (league, version, métriques de validation).

        Args:
            db_session: Session SQLAlchemy active.
            league: Identifiant de la ligue (ex: "EPL").
            version: Version du modèle pour le versioning.

        Raises:
            RuntimeError: Si le modèle n'est pas calibré.
        """
        raise NotImplementedError

    @classmethod
    def load_params(cls, db_session: Any, league: str) -> "DixonColesModel":
        """
        Charge les paramètres calibrés depuis la base de données.

        Cherche la version active (is_active=True) pour la ligue donnée.
        Retourne une instance DixonColesModel pré-calibrée, prête pour predict_score_matrix().

        Args:
            db_session: Session SQLAlchemy active.
            league: Identifiant de la ligue (ex: "EPL").

        Returns:
            Instance DixonColesModel avec _fit_result chargé.

        Raises:
            ValueError: Si aucun paramètre actif n'est trouvé pour cette ligue.
        """
        raise NotImplementedError

    def get_team_strengths(self) -> dict[str, dict[str, float]]:
        """
        Retourne un classement des équipes par force offensive et défensive.

        Utile pour le debugging et l'analyse.

        Returns:
            Dict {team_name: {"attack": float, "defense": float, "overall": float}}
            Trié par "overall" décroissant.
        """
        raise NotImplementedError
