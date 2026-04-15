"""
Fixtures pytest partagées entre tous les tests.

Fournit :
- Une base de données SQLite en mémoire (isolée par test)
- Des settings de test avec DEMO_MODE=True
- Des objets mock pour les fetchers HTTP
- Des données de matchs de test réalistes
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ─── Database fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def test_engine():
    """Crée un engine SQLite en mémoire isolé pour chaque test."""
    raise NotImplementedError


@pytest.fixture(scope="function")
def test_db(test_engine):
    """
    Retourne une session de base de données de test.

    La base est créée au début de chaque test et détruite à la fin.
    Garantit l'isolation complète entre les tests.
    """
    raise NotImplementedError


# ─── Settings fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_settings():
    """
    Retourne une configuration de test avec des valeurs fictives.

    DEMO_MODE=True garantit que les tests ne font pas d'appels API réels.
    """
    raise NotImplementedError


# ─── Sample data fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def sample_match():
    """Retourne un dict représentant un match Arsenal vs Chelsea."""
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
    """Retourne un dict de cotes bookmakers au format The Odds API."""
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
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "description": "2.5", "price": 1.85},
                            {"name": "Under", "description": "2.5", "price": 1.95},
                        ],
                    },
                ],
            }
        ],
    }


@pytest.fixture
def sample_historical_matches():
    """
    Retourne une liste de 50 matchs historiques pour tester la calibration Dixon-Coles.
    Les scores sont réalistes pour la Premier League.
    """
    raise NotImplementedError


@pytest.fixture
def mock_odds_fetcher():
    """Mock du OddsFetcher pour les tests sans appel HTTP."""
    mock = AsyncMock()
    mock.fetch_upcoming_events.return_value = []
    return mock


@pytest.fixture
def mock_football_fetcher():
    """Mock du FootballFetcher pour les tests sans appel HTTP."""
    mock = AsyncMock()
    mock.fetch_fixtures.return_value = []
    return mock
