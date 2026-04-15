"""
Modèle SQLAlchemy pour une prédiction/value bet sélectionnée.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Prediction(Base):
    """Représente une prédiction (value bet) générée par le pipeline."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    model_prob: Mapped[float] = mapped_column(Float, nullable=False)
    best_bookmaker: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    best_odds: Mapped[float] = mapped_column(Float, nullable=False)
    fair_odds: Mapped[float] = mapped_column(Float, nullable=False)
    ev: Mapped[float] = mapped_column(Float, nullable=False)
    kelly_fraction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    match: Mapped["Match"] = relationship("Match", back_populates="predictions")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Prediction match_id={self.match_id} "
            f"{self.market}/{self.outcome} EV={self.ev:.3f}>"
        )
