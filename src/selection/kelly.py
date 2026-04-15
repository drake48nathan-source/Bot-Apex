"""
Kelly Criterion pour le dimensionnement des mises.

Le Kelly Criterion détermine la fraction optimale de la bankroll à miser
pour maximiser la croissance géométrique à long terme.

Formule complète :
    f* = (b*p - q) / b
    où :
        b = cote - 1 (gain net si gagné)
        p = probabilité de gagner selon le modèle
        q = 1 - p (probabilité de perdre)

    Simplifié : f* = (p * odds - 1) / (odds - 1)

En pratique, on utilise une fraction du Kelly (quarter-Kelly par défaut)
pour réduire la variance et les drawdowns :
    stake = f* × kelly_fraction × bankroll

Usage:
    kelly = KellyCriterion(fraction=0.25)
    stake_pct = kelly.calculate(model_prob=0.52, odds=2.10)
    # → 0.032 (3.2% de bankroll)
    stake_units = kelly.calculate_units(model_prob=0.52, odds=2.10, bankroll=100)
    # → 3.2 unités
"""

from __future__ import annotations


class KellyCriterion:
    """Calcule les mises optimales selon le Kelly Criterion fractionné."""

    def __init__(self, fraction: float = 0.25) -> None:
        """
        Initialise avec la fraction Kelly à appliquer.

        Args:
            fraction: Fraction du Kelly complet à utiliser (0.25 = quart-Kelly).
                     Range recommandé : 0.1 à 0.5. Full Kelly (1.0) est trop agressif.
        """
        raise NotImplementedError

    def calculate(self, model_prob: float, odds: float) -> float:
        """
        Calcule la fraction optimale de bankroll à miser.

        Formule : f = (p * odds - 1) / (odds - 1) × fraction

        Si f ≤ 0 : pas de value (EV négatif), retourner 0.
        La valeur est plafonnée à max_stake_pct (défaut : 10%) pour la sécurité.

        Args:
            model_prob: Probabilité de victoire selon le modèle [0, 1].
            odds: Cote décimale du bookmaker (> 1.0).

        Returns:
            Fraction de bankroll à miser [0, max_stake_pct].
            Retourne 0.0 si EV négatif ou si les inputs sont invalides.
        """
        raise NotImplementedError

    def calculate_units(
        self, model_prob: float, odds: float, bankroll: float
    ) -> float:
        """
        Calcule la mise en unités monétaires absolues.

        Args:
            model_prob: Probabilité modèle [0, 1].
            odds: Cote décimale.
            bankroll: Taille totale de la bankroll en unités.

        Returns:
            Nombre d'unités à miser. Retourne 0.0 si EV négatif.
        """
        raise NotImplementedError

    def full_kelly(self, model_prob: float, odds: float) -> float:
        """
        Calcule le Kelly complet (sans fraction).

        À utiliser uniquement pour l'affichage informatif.
        Ne jamais utiliser directement pour les mises réelles.

        Args:
            model_prob: Probabilité modèle.
            odds: Cote décimale.

        Returns:
            Fraction Kelly complète (peut dépasser 1.0 théoriquement).
        """
        raise NotImplementedError
