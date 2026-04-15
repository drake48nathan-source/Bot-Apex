"""
Fetcher pour les cotes en temps réel via The Odds API.

En DEMO_MODE ou sans clé API, retourne des événements synthétiques
au format The Odds API permettant au pipeline de s'exécuter end-to-end.

Usage:
    fetcher = OddsFetcher()
    events = await fetcher.fetch_all_leagues()
    # → [{"id": "...", "sport_key": "soccer_epl", "home_team": "Arsenal",
    #      "away_team": "Chelsea", "commence_time": "...",
    #      "bookmakers": [...]}, ...]
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

_DEMO_EVENTS: list[dict[str, Any]] = [
    {
        "id": "demo_epl_001",
        "sport_key": "soccer_epl",
        "sport_title": "EPL",
        "commence_time": (datetime.now(timezone.utc) + timedelta(hours=20)).isoformat(),
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "bookmakers": [
            {
                "key": "bet365",
                "title": "Bet365",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.10},
                            {"name": "Draw", "price": 3.40},
                            {"name": "Chelsea", "price": 3.60},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "description": "2.5", "price": 1.85},
                            {"name": "Under", "description": "2.5", "price": 2.00},
                        ],
                    },
                    {
                        "key": "btts",
                        "outcomes": [
                            {"name": "Yes", "price": 1.75},
                            {"name": "No", "price": 2.10},
                        ],
                    },
                ],
            }
        ],
    },
    {
        "id": "demo_liga_001",
        "sport_key": "soccer_spain_la_liga",
        "sport_title": "La Liga",
        "commence_time": (datetime.now(timezone.utc) + timedelta(hours=22)).isoformat(),
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        "bookmakers": [
            {
                "key": "unibet",
                "title": "Unibet",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Real Madrid", "price": 2.30},
                            {"name": "Draw", "price": 3.20},
                            {"name": "Barcelona", "price": 3.10},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "description": "2.5", "price": 1.70},
                            {"name": "Under", "description": "2.5", "price": 2.20},
                        ],
                    },
                ],
            }
        ],
    },
    {
        "id": "demo_bundesliga_001",
        "sport_key": "soccer_germany_bundesliga",
        "sport_title": "Bundesliga",
        "commence_time": (datetime.now(timezone.utc) + timedelta(hours=18)).isoformat(),
        "home_team": "Bayern Munich",
        "away_team": "Borussia Dortmund",
        "bookmakers": [
            {
                "key": "betfair",
                "title": "Betfair",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Bayern Munich", "price": 1.65},
                            {"name": "Draw", "price": 4.00},
                            {"name": "Borussia Dortmund", "price": 5.50},
                        ],
                    },
                ],
            }
        ],
    },
]


class OddsFetcher:
    """
    Récupère les cotes du jour pour toutes les ligues configurées.

    En DEMO_MODE ou sans ODDS_API_KEY, retourne des événements synthétiques.
    En production, appelle api.the-odds-api.com/v4.
    """

    _TIMEOUT = 15.0
    _MARKETS = "h2h,totals,btts"
    _REGIONS = "eu"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.ODDS_API_BASE_URL,
                timeout=self._TIMEOUT,
            )
        return self._client

    async def fetch_all_leagues(self) -> list[dict[str, Any]]:
        """
        Récupère les événements avec cotes pour toutes les ligues de la config.

        Returns:
            Liste d'événements au format The Odds API, avec bookmakers et marchés.
        """
        if settings.DEMO_MODE or not settings.ODDS_API_KEY:
            logger.info("Using demo odds data", n_events=len(_DEMO_EVENTS))
            return _DEMO_EVENTS

        all_events: list[dict[str, Any]] = []
        leagues = settings.football_leagues_list

        tasks = [self._fetch_league(league) for league in leagues]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for league, result in zip(leagues, results):
            if isinstance(result, Exception):
                logger.error("Failed to fetch odds", league=league, error=str(result))
            else:
                all_events.extend(result)

        logger.info("Odds fetched for all leagues", n_events=len(all_events))
        return all_events

    async def _fetch_league(self, sport_key: str) -> list[dict[str, Any]]:
        """Interroge /sports/{sport_key}/odds pour une ligue."""
        client = self._get_client()

        resp = await client.get(
            f"/sports/{sport_key}/odds",
            params={
                "apiKey": settings.ODDS_API_KEY,
                "regions": self._REGIONS,
                "markets": self._MARKETS,
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
        )
        resp.raise_for_status()

        events = resp.json()
        remaining = resp.headers.get("x-requests-remaining", "?")
        logger.debug(
            "Odds API response",
            league=sport_key,
            n_events=len(events),
            requests_remaining=remaining,
        )
        return events

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
