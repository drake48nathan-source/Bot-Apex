"""Marché Asian Handicap."""
from __future__ import annotations
import numpy as np
from numpy.typing import NDArray


def compute(matrix: NDArray[np.float64], handicap: float = -0.5) -> dict[str, float]:
    """
    Calcule les probabilités pour un Asian Handicap donné (côté domicile).

    Pour AH -0.5 (home doit gagner) :  P(home win)
    Pour AH +0.5 (home ne doit pas perdre) : P(home win) + P(draw)
    Pour AH -1.0 (home gagne par 2+) avec push si 1-but d'écart.
    Pour AH +1.0 (home perd pas ou perd par 1 max) avec push si 1-but d'écart.

    Args:
        matrix: Matrice de scores Dixon-Coles.
        handicap: Handicap en buts côté domicile (ex: -0.5, +0.5, -1.0, +1.0).

    Returns:
        {"home": float, "away": float}  — somme ≈ 1.0 (push réduit les deux)
    """
    n = matrix.shape[0]

    if handicap == -0.5:
        # Home doit gagner
        home = float(sum(matrix[i][j] for i in range(n) for j in range(n) if i > j))
        away = 1.0 - home
    elif handicap == 0.5:
        # Home doit ne pas perdre
        home = float(sum(matrix[i][j] for i in range(n) for j in range(n) if i >= j))
        away = 1.0 - home
    elif handicap == -1.0:
        # Home gagne par 2+ : win. Home gagne par 1 : push (demi-remboursement)
        win = float(sum(matrix[i][j] for i in range(n) for j in range(n) if (i - j) > 1))
        push = float(sum(matrix[i][j] for i in range(n) for j in range(n) if (i - j) == 1))
        home = win + 0.5 * push
        away = 1.0 - win - push + 0.5 * push  # loss + half push
    elif handicap == 1.0:
        # Away gagne par 2+ : away wins. Away gagne par 1 : push
        win_away = float(sum(matrix[i][j] for i in range(n) for j in range(n) if (j - i) > 1))
        push = float(sum(matrix[i][j] for i in range(n) for j in range(n) if (j - i) == 1))
        away = win_away + 0.5 * push
        home = 1.0 - win_away - push + 0.5 * push
    else:
        # Générique pour les handicaps entiers
        win_h = float(sum(matrix[i][j] for i in range(n) for j in range(n) if (i - j) > abs(handicap)))
        home = win_h
        away = 1.0 - home

    return {"home": max(0.0, min(1.0, home)), "away": max(0.0, min(1.0, away))}
