"""
Modèle SQLAlchemy pour un match de football.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Match(Base):
    """Représente un match dans la base de données."""

    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("external_id", name="uq_matches_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    sport: Mapped[str] = mapped_column(String(32), nullable=False, default="football")
    league: Mapped[str] = mapped_column(String(128), nullable=False)
    home_team: Mapped[str] = mapped_column(String(128), nullable=False)
    away_team: Mapped[str] = mapped_column(String(128), nullable=False)
    kickoff_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    predictions: Mapped[list["Prediction"]] = relationship(  # noqa: F821
        "Prediction", back_populates="match", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Match {self.home_team} vs {self.away_team} ({self.league})>"
