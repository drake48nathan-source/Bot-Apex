"""Marché Double Chance (1X, X2, 12)."""
from __future__ import annotations
import numpy as np
from numpy.typing import NDArray


def compute(matrix: NDArray[np.float64]) -> dict[str, float]:
    """
    Calcule les probabilités pour les trois outcomes Double Chance.

    1X = home win OR draw
    X2 = draw OR away win
    12 = home win OR away win (no draw)

    Returns:
        {"1X": float, "X2": float, "12": float}
    """
    n = matrix.shape[0]
    home_win = float(sum(matrix[i][j] for i in range(n) for j in range(n) if i > j))
    draw = float(sum(matrix[i][i] for i in range(n)))
    away_win = float(sum(matrix[i][j] for i in range(n) for j in range(n) if i < j))

    return {
        "1X": min(1.0, home_win + draw),
        "X2": min(1.0, draw + away_win),
        "12": min(1.0, home_win + away_win),
    }
