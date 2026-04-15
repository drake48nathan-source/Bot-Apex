"""
Fetcher pour les données historiques de football via API-Football.

En DEMO_MODE ou sans clé API, retourne des données synthétiques réalistes
permettant au modèle Dixon-Coles de se calibrer.

Usage:
    fetcher = FootballFetcher()
    matches = await fetcher.fetch_historical_matches("soccer_epl", 2024)
    # → [{"home_team": "Arsenal", "away_team": "Chelsea",
    #      "home_score": 2, "away_score": 1, "date": "2024-03-15"}, ...]
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Mapping Odds API sport_key → API-Football league_id
LEAGUE_ID_MAP: dict[str, int] = {
    "soccer_epl": 39,
    "soccer_spain_la_liga": 140,
    "soccer_germany_bundesliga": 78,
    "soccer_italy_serie_a": 135,
    "soccer_france_ligue_one": 61,
    "soccer_uefa_champs_league": 2,
    "soccer_uefa_europa_league": 3,
    "soccer_netherlands_eredivisie": 88,
    "soccer_portugal_primeira_liga": 94,
}

# Équipes de démo par ligue (pour DEMO_MODE)
_DEMO_TEAMS: dict[str, list[str]] = {
    "soccer_epl": [
        "Arsenal", "Chelsea", "Liverpool", "Manchester City", "Manchester United",
        "Tottenham", "Newcastle", "Aston Villa", "Brighton", "West Ham",
    ],
    "soccer_spain_la_liga": [
        "Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla", "Valencia",
        "Athletic Club", "Real Sociedad", "Villarreal", "Real Betis", "Celta Vigo",
    ],
    "soccer_germany_bundesliga": [
        "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen",
        "Eintracht Frankfurt", "Wolfsburg", "Gladbach", "Union Berlin", "Freiburg", "Mainz",
    ],
    "soccer_italy_serie_a": [
        "Juventus", "Inter Milan", "AC Milan", "Napoli", "Roma",
        "Lazio", "Atalanta", "Fiorentina", "Torino", "Bologna",
    ],
    "soccer_france_ligue_one": [
        "PSG", "Monaco", "Lyon", "Marseille", "Lille",
        "Rennes", "Nice", "Lens", "Strasbourg", "Nantes",
    ],
}


def _generate_demo_matches(league: str, season: int) -> list[dict[str, Any]]:
    """Génère ~200 matchs synthétiques réalistes pour la calibration du modèle."""
    import random

    rng = random.Random(hash(f"{league}_{season}"))
    teams = _DEMO_TEAMS.get(league, _DEMO_TEAMS["soccer_epl"])
    matches: list[dict[str, Any]] = []

    # Double round-robin (chaque paire joue 2 fois)
    start_date = datetime(season, 8, 1)
    day_offset = 0

    for home in teams:
        for away in teams:
            if home == away:
                continue

            # Distribution Poisson réaliste : λ_home ≈ 1.5, λ_away ≈ 1.1
            home_goals = rng.choices(range(6), weights=[0.20, 0.35, 0.25, 0.12, 0.05, 0.03])[0]
            away_goals = rng.choices(range(6), weights=[0.28, 0.36, 0.22, 0.09, 0.04, 0.01])[0]

            match_date = start_date + timedelta(days=day_offset % 280)
            day_offset += 7

            matches.append({
                "home_team": home,
                "away_team": away,
                "home_score": home_goals,
                "away_score": away_goals,
                "date": match_date.strftime("%Y-%m-%d"),
            })

    logger.debug(
        "Generated demo matches",
        league=league,
        season=season,
        n_matches=len(matches),
    )
    return matches


class FootballFetcher:
    """
    Récupère les résultats historiques de football pour calibrer Dixon-Coles.

    En DEMO_MODE ou sans API_FOOTBALL_KEY, utilise des données synthétiques.
    En production, appelle v3.football.api-sports.io.
    """

    _TIMEOUT = 20.0
    _MAX_RESULTS_PER_PAGE = 100

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.API_FOOTBALL_BASE_URL,
                headers={
                    "x-rapidapi-key": settings.API_FOOTBALL_KEY,
                    "x-rapidapi-host": settings.API_FOOTBALL_HOST,
                },
                timeout=self._TIMEOUT,
            )
        return self._client

    async def fetch_historical_matches(
        self, league: str, season: int
    ) -> list[dict[str, Any]]:
        """
        Retourne les matchs terminés d'une ligue/saison.

        Args:
            league: Sport key Odds API (ex: "soccer_epl").
            season: Année de début de saison (ex: 2024 = saison 2024/2025).

        Returns:
            Liste de dicts : {"home_team", "away_team", "home_score", "away_score", "date"}
        """
        if settings.DEMO_MODE or not settings.API_FOOTBALL_KEY:
            return _generate_demo_matches(league, season)

        league_id = LEAGUE_ID_MAP.get(league)
        if league_id is None:
            logger.warning("Unknown league key, using demo data", league=league)
            return _generate_demo_matches(league, season)

        try:
            return await self._fetch_from_api(league_id, season)
        except Exception as e:
            logger.error(
                "API-Football fetch failed, falling back to demo data",
                league=league,
                season=season,
                error=str(e),
            )
            return _generate_demo_matches(league, season)

    async def _fetch_from_api(
        self, league_id: int, season: int
    ) -> list[dict[str, Any]]:
        """Interroge l'endpoint /fixtures de API-Football."""
        client = self._get_client()
        matches: list[dict[str, Any]] = []
        page = 1

        while True:
            resp = await client.get(
                "/fixtures",
                params={
                    "league": league_id,
                    "season": season,
                    "status": "FT",  # Full-Time uniquement
                    "page": page,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            fixtures = data.get("response", [])
            if not fixtures:
                break

            for f in fixtures:
                teams = f.get("teams", {})
                goals = f.get("goals", {})
                fixture = f.get("fixture", {})

                home_goals = goals.get("home")
                away_goals = goals.get("away")
                if home_goals is None or away_goals is None:
                    continue

                date_str = fixture.get("date", "")
                try:
                    match_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    date_formatted = match_date.strftime("%Y-%m-%d")
                except Exception:
                    date_formatted = date_str[:10]

                matches.append({
                    "home_team": teams.get("home", {}).get("name", ""),
                    "away_team": teams.get("away", {}).get("name", ""),
                    "home_score": int(home_goals),
                    "away_score": int(away_goals),
                    "date": date_formatted,
                })

            paging = data.get("paging", {})
            if page >= paging.get("total", 1):
                break
            page += 1
            await asyncio.sleep(0.1)  # Respecter le rate-limit

        logger.info(
            "Fetched historical matches from API-Football",
            league_id=league_id,
            season=season,
            n_matches=len(matches),
        )
        return matches

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
