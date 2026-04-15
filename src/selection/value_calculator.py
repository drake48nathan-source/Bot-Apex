"""
Calcul de la value (expected value) des paris.

Ce module est responsable de deux tâches distinctes :

1. Démarginisation des cotes bookmakers
   Les bookmakers intègrent une marge (vig/overround) dans leurs cotes,
   rendant la somme des probabilités implicites supérieure à 1.
   La démarginisation retire cette marge pour obtenir les "cotes fair".

   Deux méthodes sont implémentées :
   - Power method (recommandée) : plus précise, distribue la marge proportionnellement
   - Additive method : plus simple, soustrait la marge uniformément

2. Calcul de l'expected value (EV)
   EV = probabilité_modèle × cote_bookmaker - 1

   Un pari est un value bet si EV > seuil (défaut: +5%).
   Ex: P(modèle) = 0.52, cote = 2.10 → EV = 0.52 × 2.10 - 1 = +9.2%

Ce module ne dépend d'aucun autre module du projet (pur calcul mathématique).
Il peut et doit être testé exhaustivement en isolation.

Usage:
    calc = ValueCalculator()
    true_probs = calc.demargin_power([2.10, 3.50, 3.20])
    # → [0.455, 0.270, 0.275]

    ev = calc.calculate_ev(model_prob=0.52, bookmaker_odds=2.10)
    # → 0.092 (+9.2%)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeMarginResult:
    """
    Résultat de la démarginisation d'un ensemble de cotes.

    Attributes:
        true_probs: Probabilités vraies après retrait de la marge [0,1].
        fair_odds: Cotes fair correspondantes (1 / true_prob pour chaque outcome).
        overround: Marge du bookmaker (ex: 0.075 = 7.5% de vig).
        method: Méthode utilisée : 'power' ou 'additive'.
    """

    true_probs: list[float]
    fair_odds: list[float]
    overround: float
    method: str


class ValueCalculator:
    """
    Calculateur de value pour les paris sportifs.

    Stateless : toutes les méthodes peuvent être appelées sur n'importe quelle
    instance sans état préalable. Peut être utilisé comme singleton.
    """

    def demargin_power(self, odds: list[float]) -> DeMarginResult:
        """
        Démarginise les cotes via la méthode 'power' (recommandée).

        Principe :
        - Les probs implicites sont p_i = 1/odd_i
        - La somme sum(p_i) = 1 + overround (> 1 à cause de la marge)
        - On cherche k tel que sum(p_i^k) = 1
        - Les vraies probabilités sont true_prob_i = p_i^k

        La méthode power distribue la marge proportionnellement à la taille
        de la probabilité implicite (ce qui est plus réaliste que la méthode additive).

        Implémentation : scipy.optimize.brentq pour trouver k dans ]0, 2[.

        Args:
            odds: Liste de cotes décimales (ex: [2.10, 3.50, 3.20]).
                  Toutes les valeurs doivent être > 1.0.
                  La liste doit contenir au moins 2 éléments.

        Returns:
            DeMarginResult avec method='power'.

        Raises:
            ValueError: Si une cote est <= 1.0 ou si la liste est vide.
            RuntimeError: Si brentq ne converge pas (ne devrait pas arriver).
        """
        raise NotImplementedError

    def demargin_additive(self, odds: list[float]) -> DeMarginResult:
        """
        Démarginise les cotes via la méthode additive (simple).

        Principe :
        - Les probs implicites sont p_i = 1/odd_i
        - overround = sum(p_i) - 1
        - true_prob_i = p_i - overround/n (soustraction uniforme)

        Plus simple que la méthode power mais moins précise : suppose que
        la marge est distribuée uniformément sur tous les outcomes.

        Args:
            odds: Liste de cotes décimales.

        Returns:
            DeMarginResult avec method='additive'.

        Raises:
            ValueError: Si une cote est <= 1.0 ou si les true_probs résultantes
                       ne sont pas toutes positives.
        """
        raise NotImplementedError

    def calculate_ev(self, model_prob: float, bookmaker_odds: float) -> float:
        """
        Calcule l'expected value (EV) d'un pari.

        Formule : EV = model_prob × bookmaker_odds - 1

        Interprétation :
        - EV > 0 : pari value bet (espérance positive)
        - EV = 0 : pari à l'équilibre (ni bon ni mauvais)
        - EV < 0 : pari perdant à long terme

        Exemple :
        - P(modèle) = 0.52, cote = 2.10
        - EV = 0.52 × 2.10 - 1 = 1.092 - 1 = 0.092 = +9.2%

        Args:
            model_prob: Probabilité estimée par le modèle [0, 1].
            bookmaker_odds: Cote décimale du bookmaker (> 1.0).

        Returns:
            Expected value en décimal (0.09 = +9%). Peut être négatif.

        Raises:
            ValueError: Si model_prob n'est pas dans ]0, 1[ ou si odds <= 1.0.
        """
        raise NotImplementedError

    def calculate_ev_from_fair_odds(self, model_prob: float, fair_odds: float) -> float:
        """
        Calcule l'EV en comparant la probabilité modèle aux cotes fair (démarginisées).

        Plus conservateur que calculate_ev() car compare au vrai prix.
        À utiliser pour valider que l'edge n'est pas dû à la marge bookmaker.

        Args:
            model_prob: Probabilité estimée par le modèle.
            fair_odds: Cote fair après démarginisation (> 1.0).

        Returns:
            EV en décimal.
        """
        raise NotImplementedError

    def best_odds_across_bookmakers(
        self, outcome: str, bookmakers_data: list[dict]
    ) -> tuple[str, float]:
        """
        Trouve la meilleure cote disponible pour un outcome donné parmi plusieurs bookmakers.

        Args:
            outcome: Nom de l'outcome (ex: "Arsenal", "Over 2.5", "Draw").
            bookmakers_data: Liste de dicts issus de The Odds API :
                [{"key": "bet365", "outcomes": [{"name": "Arsenal", "price": 2.10}, ...]}]

        Returns:
            Tuple (bookmaker_key, best_odds) avec la meilleure cote trouvée.

        Raises:
            ValueError: Si aucune cote n'est trouvée pour l'outcome donné.
        """
        raise NotImplementedError

    def compute_overround(self, odds: list[float]) -> float:
        """
        Calcule la marge du bookmaker (overround) pour un ensemble de cotes.

        overround = sum(1/odd_i) - 1

        Exemple : [2.10, 3.50, 3.20] → 1/2.10 + 1/3.50 + 1/3.20 - 1 = 0.075 = 7.5%

        Args:
            odds: Liste de cotes décimales représentant les outcomes d'un même événement.

        Returns:
            Overround en décimal (0.075 = 7.5%).
        """
        raise NotImplementedError
