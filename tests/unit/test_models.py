"""Tests unitaires pour les modèles SQLAlchemy et Kelly."""

from __future__ import annotations

import os
import pytest
from datetime import datetime, timezone

os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


# ─── Match properties ─────────────────────────────────────────────────────────

class TestMatchProperties:
    """Test the pure-Python property logic on Match without a DB session.

    We call the property functions directly on a SimpleNamespace to avoid
    SQLAlchemy ORM instrumentation overhead.
    """

    def _match_props(self):
        """Return the unbound property functions from Match."""
        from src.data.models.match import Match
        return (
            Match.is_finished.fget,
            Match.result.fget,
            Match.total_goals.fget,
        )

    def _make(self, status="scheduled", home_score=None, away_score=None,
              home_team="Arsenal", away_team="Chelsea"):
        from types import SimpleNamespace
        return SimpleNamespace(
            home_team=home_team,
            away_team=away_team,
            kickoff_utc=datetime(2024, 12, 15, 15, 0, tzinfo=timezone.utc),
            status=status,
            home_score=home_score,
            away_score=away_score,
        )

    def test_is_finished_scheduled(self):
        is_finished, _, _ = self._match_props()
        m = self._make(status="scheduled")
        assert is_finished(m) is False

    def test_is_finished_finished(self):
        is_finished, _, _ = self._match_props()
        m = self._make(status="finished")
        assert is_finished(m) is True

    def test_result_scheduled_is_none(self):
        _, result, _ = self._match_props()
        m = self._make(status="scheduled")
        # is_finished must be callable on m, so patch it
        m.is_finished = False
        assert result(m) is None

    def test_result_home_win(self):
        _, result, _ = self._match_props()
        m = self._make(status="finished", home_score=2, away_score=1)
        m.is_finished = True
        assert result(m) == "home"

    def test_result_away_win(self):
        _, result, _ = self._match_props()
        m = self._make(status="finished", home_score=0, away_score=2)
        m.is_finished = True
        assert result(m) == "away"

    def test_result_draw(self):
        _, result, _ = self._match_props()
        m = self._make(status="finished", home_score=1, away_score=1)
        m.is_finished = True
        assert result(m) == "draw"

    def test_result_missing_scores_is_none(self):
        _, result, _ = self._match_props()
        m = self._make(status="finished", home_score=None, away_score=None)
        m.is_finished = True
        assert result(m) is None

    def test_total_goals_finished(self):
        _, _, total_goals = self._match_props()
        m = self._make(home_score=2, away_score=1)
        assert total_goals(m) == 3

    def test_total_goals_draw(self):
        _, _, total_goals = self._match_props()
        m = self._make(home_score=1, away_score=1)
        assert total_goals(m) == 2

    def test_total_goals_missing_scores(self):
        _, _, total_goals = self._match_props()
        m = self._make(home_score=None, away_score=None)
        assert total_goals(m) is None


# ─── KellyCriterion.full_kelly ────────────────────────────────────────────────

class TestKellyFullKelly:
    """Tests pour la méthode full_kelly (informatif)."""

    @pytest.fixture
    def kelly(self):
        from src.selection.kelly import KellyCriterion
        return KellyCriterion(fraction=0.25)

    def test_full_kelly_positive_ev(self, kelly):
        k = kelly.full_kelly(0.55, 2.10)
        assert k > 0

    def test_full_kelly_negative_ev(self, kelly):
        k = kelly.full_kelly(0.30, 2.10)
        assert k == 0.0

    def test_full_kelly_no_fraction_applied(self, kelly):
        """full_kelly ne multiplie pas par la fraction."""
        k = kelly.full_kelly(0.52, 2.10)
        fractioned = kelly.calculate(0.52, 2.10)
        # full_kelly > fractioned (car fraction=0.25)
        assert k > fractioned

    def test_full_kelly_invalid_prob(self, kelly):
        assert kelly.full_kelly(0.0, 2.10) == 0.0

    def test_full_kelly_invalid_odds(self, kelly):
        assert kelly.full_kelly(0.5, 0.5) == 0.0

    def test_calculate_units_with_explicit_bankroll(self, kelly):
        units = kelly.calculate_units(0.52, 2.10, bankroll=500)
        assert units > 0
        assert units == kelly.calculate(0.52, 2.10) * 500
