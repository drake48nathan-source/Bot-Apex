"""Marché Over/Under N.5 buts."""
from __future__ import annotations
import numpy as np
from numpy.typing import NDArray


def compute(matrix: NDArray[np.float64], line: float = 2.5) -> dict[str, float]:
    """
    Calcule les probabilités Over / Under pour un total de buts donné.

    Args:
        matrix: Matrice de scores Dixon-Coles.
        line: Ligne de totaux (ex: 2.5, 1.5, 3.5).

    Returns:
        {"over": float, "under": float}  — somme = 1.0
    """
    n = matrix.shape[0]
    threshold = int(line)  # Pour X.5, threshold = int(X)
    over = float(sum(
        matrix[i][j]
        for i in range(n) for j in range(n)
        if (i + j) > threshold
    ))
    under = float(sum(
        matrix[i][j]
        for i in range(n) for j in range(n)
        if (i + j) <= threshold
    ))
    total = over + under
    if total == 0:
        return {"over": 0.5, "under": 0.5}
    return {"over": over / total, "under": under / total}
