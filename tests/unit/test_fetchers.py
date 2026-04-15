"""Tests unitaires pour les fetchers en DEMO_MODE et le circuit breaker."""

from __future__ import annotations

import os
import time
import pytest

os.environ["DEMO_MODE"] = "true"
os.environ["API_FOOTBALL_KEY"] = "demo"
os.environ["ODDS_API_KEY"] = "demo"


# ─── FootballFetcher (DEMO_MODE) ──────────────────────────────────────────────

class TestFootballFetcherDemo:
    @pytest.mark.asyncio
    async def test_fetch_team_stats_known_team(self):
        from src.data.fetchers.football import FootballFetcher
        async with FootballFetcher() as f:
            stats = await f.fetch_team_stats("Arsenal")
        assert "goals_for_avg_home" in stats
        assert stats["goals_for_avg_home"] > 0

    @pytest.mark.asyncio
    async def test_fetch_team_stats_unknown_team_returns_defaults(self):
        from src.data.fetchers.football import FootballFetcher
        async with FootballFetcher() as f:
            stats = await f.fetch_team_stats("UnknownFC")
        # Should return default stats, not crash
        assert "goals_for_avg_home" in stats

    @pytest.mark.asyncio
    async def test_fetch_h2h_known_pair(self):
        from src.data.fetchers.football import FootballFetcher
        async with FootballFetcher() as f:
            matches = await f.fetch_h2h("Arsenal", "Chelsea")
        assert len(matches) > 0
        assert "home_score" in matches[0]

    @pytest.mark.asyncio
    async def test_fetch_h2h_reverse_pair(self):
        """Reverse pair should also work via DEMO_H2H lookup."""
        from src.data.fetchers.football import FootballFetcher
        async with FootballFetcher() as f:
            matches = await f.fetch_h2h("Chelsea", "Arsenal")
        assert isinstance(matches, list)

    @pytest.mark.asyncio
    async def test_fetch_h2h_unknown_pair_returns_empty(self):
        from src.data.fetchers.football import FootballFetcher
        async with FootballFetcher() as f:
            matches = await f.fetch_h2h("UnknownA", "UnknownB")
        assert matches == []

    @pytest.mark.asyncio
    async def test_fetch_historical_matches_season_2023(self):
        from src.data.fetchers.football import FootballFetcher
        async with FootballFetcher() as f:
            matches = await f.fetch_historical_matches("soccer_epl", 2023)
        assert len(matches) > 50
        assert all("home_team" in m for m in matches)
        assert all("home_score" in m for m in matches)

    @pytest.mark.asyncio
    async def test_fetch_historical_different_seeds(self):
        """Different seasons → different random data via seed."""
        from src.data.fetchers.football import FootballFetcher
        async with FootballFetcher() as f:
            m2022 = await f.fetch_historical_matches("soccer_epl", 2022)
            m2023 = await f.fetch_historical_matches("soccer_epl", 2023)
        # Different seeds → different sequences
        scores_2022 = [(m["home_score"], m["away_score"]) for m in m2022[:5]]
        scores_2023 = [(m["home_score"], m["away_score"]) for m in m2023[:5]]
        assert scores_2022 != scores_2023

    def test_parse_team_stats_empty_raw(self):
        from src.data.fetchers.football import FootballFetcher
        f = FootballFetcher()
        stats = f._parse_team_stats({})
        assert stats["goals_for_avg_home"] == 1.5

    def test_parse_fixtures_skips_missing_goals(self):
        from src.data.fetchers.football import FootballFetcher
        f = FootballFetcher()
        raw = [
            {"teams": {"home": {"name": "A"}, "away": {"name": "B"}},
             "goals": {"home": None, "away": None},
             "fixture": {"date": "2024-01-01"}},
            {"teams": {"home": {"name": "C"}, "away": {"name": "D"}},
             "goals": {"home": 2, "away": 1},
             "fixture": {"date": "2024-01-02"}},
        ]
        result = f._parse_fixtures(raw)
        assert len(result) == 1
        assert result[0]["home_team"] == "C"

    def test_default_stats_structure(self):
        from src.data.fetchers.football import FootballFetcher
        f = FootballFetcher()
        stats = f._default_stats("SomeTeam")
        assert stats["team"]["name"] == "SomeTeam"
        assert "goals_for_avg_home" in stats
        assert "form" in stats

    @pytest.mark.asyncio
    async def test_resolve_team_id_known(self):
        from src.data.fetchers.football import FootballFetcher
        f = FootballFetcher()
        team_id = await f._resolve_team_id("Arsenal")
        assert team_id == 42

    @pytest.mark.asyncio
    async def test_resolve_team_id_unknown_returns_zero(self):
        from src.data.fetchers.football import FootballFetcher
        f = FootballFetcher()
        team_id = await f._resolve_team_id("UnknownFC")
        assert team_id == 0


# ─── OddsFetcher (DEMO_MODE) ──────────────────────────────────────────────────

class TestOddsFetcherDemo:
    @pytest.mark.asyncio
    async def test_fetch_upcoming_events_returns_list(self):
        from src.data.fetchers.odds import OddsFetcher
        async with OddsFetcher() as f:
            events = await f.fetch_upcoming_events("soccer_epl")
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_events_have_required_fields(self):
        from src.data.fetchers.odds import OddsFetcher
        async with OddsFetcher() as f:
            events = await f.fetch_upcoming_events("soccer_epl")
        for event in events:
            assert "home_team" in event
            assert "away_team" in event
            assert "bookmakers" in event

    @pytest.mark.asyncio
    async def test_fetch_all_leagues_returns_events(self):
        from src.data.fetchers.odds import OddsFetcher
        async with OddsFetcher() as f:
            all_events = await f.fetch_all_leagues()
        # DEMO_MODE → returns events for all configured leagues
        assert isinstance(all_events, list)
        assert len(all_events) > 0

    @pytest.mark.asyncio
    async def test_unknown_league_returns_empty_or_demo(self):
        from src.data.fetchers.odds import OddsFetcher
        async with OddsFetcher() as f:
            events = await f.fetch_upcoming_events("soccer_fake_league")
        # DEMO_MODE still returns demo events
        assert isinstance(events, list)


# ─── CircuitBreaker ───────────────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_initial_state_allows_attempts(self):
        from src.data.fetchers.base import CircuitBreaker
        cb = CircuitBreaker()
        assert cb.can_attempt() is True

    def test_after_max_failures_blocks(self):
        from src.data.fetchers.base import CircuitBreaker
        cb = CircuitBreaker(max_failures=3, recovery_timeout=300)
        for _ in range(3):
            cb.record_failure()
        assert cb.can_attempt() is False

    def test_success_resets_failures(self):
        from src.data.fetchers.base import CircuitBreaker
        cb = CircuitBreaker(max_failures=5)
        for _ in range(3):
            cb.record_failure()
        cb.record_success()
        assert cb.can_attempt() is True
        assert cb.failure_count == 0

    def test_below_max_failures_still_open(self):
        from src.data.fetchers.base import CircuitBreaker
        cb = CircuitBreaker(max_failures=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.can_attempt() is True  # Only 4 of 5 failures

    def test_recovery_after_timeout(self):
        from src.data.fetchers.base import CircuitBreaker
        cb = CircuitBreaker(max_failures=2, recovery_timeout=0)
        for _ in range(2):
            cb.record_failure()
        # recovery_timeout=0 → should allow attempt immediately
        assert cb.can_attempt() is True

    def test_state_transitions(self):
        from src.data.fetchers.base import CircuitBreaker, CircuitState
        cb = CircuitBreaker(max_failures=2, recovery_timeout=300)
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
