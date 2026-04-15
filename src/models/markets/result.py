"""Marché 1X2 — Match Result."""
from __future__ import annotations
import numpy as np
from numpy.typing import NDArray


def compute(matrix: NDArray[np.float64]) -> dict[str, float]:
    """
    Calcule les probabilités home / draw / away depuis la matrice de scores.

    Returns:
        {"home": float, "draw": float, "away": float}  — somme = 1.0
    """
    n = matrix.shape[0]
    home_win = float(sum(matrix[i][j] for i in range(n) for j in range(n) if i > j))
    draw = float(sum(matrix[i][i] for i in range(n)))
    away_win = float(sum(matrix[i][j] for i in range(n) for j in range(n) if i < j))
    total = home_win + draw + away_win
    if total == 0:
        return {"home": 1/3, "draw": 1/3, "away": 1/3}
    return {
        "home": home_win / total,
        "draw": draw / total,
        "away": away_win / total,
    }
