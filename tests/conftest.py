"""Fixtures pytest partagées."""

from __future__ import annotations

import os
import random
from datetime import datetime, timezone

import pytest

# Forcer DEMO_MODE pour tous les tests
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ODDS_API_KEY", "demo")
os.environ.setdefault("API_FOOTBALL_KEY", "demo")


@pytest.fixture
def sample_match():
    return {
        "external_id": "test_match_001",
        "sport": "football",
        "league": "EPL",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "kickoff_utc": datetime(2024, 12, 15, 15, 0, tzinfo=timezone.utc),
        "status": "scheduled",
    }


@pytest.fixture
def sample_odds():
    return {
        "id": "test_match_001",
        "sport_key": "soccer_epl",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "bookmakers": [
            {
                "key": "bet365",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.10},
                            {"name": "Chelsea", "price": 3.50},
                            {"name": "Draw", "price": 3.20},
                        ],
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_historical_matches():
    """50 matchs historiques synthétiques."""
    random.seed(42)
    teams = ["Arsenal", "Chelsea", "Liverpool", "ManCity", "Spurs"]
    matches = []
    for _ in range(50):
        home, away = random.sample(teams, 2)
        matches.append({
            "home_team": home,
            "away_team": away,
            "home_score": max(0, int(random.gauss(1.5, 1))),
            "away_score": max(0, int(random.gauss(1.2, 1))),
            "date": "2024-01-15",
        })
    return matches
