"""Marché Both Teams to Score (BTTS)."""
from __future__ import annotations
import numpy as np
from numpy.typing import NDArray


def compute(matrix: NDArray[np.float64]) -> dict[str, float]:
    """
    Calcule P(BTTS Yes) et P(BTTS No).

    BTTS Yes = les deux équipes marquent au moins 1 but (i > 0 ET j > 0).

    Returns:
        {"yes": float, "no": float}  — somme = 1.0
    """
    n = matrix.shape[0]
    # P(BTTS No) = P(home scores 0) + P(away scores 0) - P(0-0)
    btts_no = float(
        matrix[0, :].sum()    # home ne marque pas
        + matrix[:, 0].sum()  # away ne marque pas
        - matrix[0, 0]        # 0-0 compté deux fois
    )
    btts_yes = 1.0 - btts_no
    btts_yes = max(0.0, min(1.0, btts_yes))
    btts_no = 1.0 - btts_yes
    return {"yes": btts_yes, "no": btts_no}
