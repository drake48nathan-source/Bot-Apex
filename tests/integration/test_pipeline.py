"""Test d'intégration : pipeline end-to-end en mode démo."""

import asyncio
import os
import pytest

# Forcer DEMO_MODE=true pour ce test
os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ODDS_API_KEY"] = "demo"
os.environ["API_FOOTBALL_KEY"] = "demo"
os.environ["WHATSAPP_TOKEN"] = ""
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = ""
os.environ["TELEGRAM_TOKEN"] = ""


class TestPipelineDemoMode:
    """Tests pipeline complet sans appels API réels."""

    @pytest.mark.asyncio
    async def test_run_daily_returns_stats(self):
        """Le pipeline demo se termine sans erreur."""
        from src.scheduler.pipeline import Pipeline, PipelineStatus

        pipeline = Pipeline(dry_run=True)
        stats = await pipeline.run_daily()

        assert stats is not None
        assert stats.status in (
            PipelineStatus.SUCCESS,
            PipelineStatus.PARTIAL_FAILURE,
        )
        assert stats.finished_at is not None

    @pytest.mark.asyncio
    async def test_events_fetched_in_demo(self):
        """En DEMO_MODE, les événements démo sont retournés."""
        from src.data.fetchers.odds import OddsFetcher

        async with OddsFetcher() as fetcher:
            events = await fetcher.fetch_upcoming_events("soccer_epl")

        assert len(events) > 0
        assert "home_team" in events[0]
        assert "bookmakers" in events[0]

    @pytest.mark.asyncio
    async def test_model_fits_and_predicts(self):
        """Le modèle se calibre et prédit correctement."""
        from src.data.fetchers.football import FootballFetcher
        from src.models.dixon_coles import DixonColesModel

        async with FootballFetcher() as f:
            matches = await f.fetch_historical_matches("soccer_epl", 2023)

        assert len(matches) > 0

        model = DixonColesModel()
        result = model.fit(matches)
        assert result.convergence

        matrix = model.predict_score_matrix("Arsenal", "Chelsea")
        assert abs(matrix.sum() - 1.0) < 1e-4

    @pytest.mark.asyncio
    async def test_selector_returns_bets(self):
        """Le sélecteur retourne des value bets depuis les données démo."""
        from src.data.fetchers.football import FootballFetcher
        from src.data.fetchers.odds import OddsFetcher, DEMO_EVENTS
        from src.models.dixon_coles import DixonColesModel
        from src.selection.selector import ValueBetSelector

        # Calibrer le modèle
        async with FootballFetcher() as f:
            matches = await f.fetch_historical_matches("soccer_epl", 2023)

        model = DixonColesModel()
        model.fit(matches)

        # Sélectionner depuis les events démo
        selector = ValueBetSelector()
        bets = selector.select_from_events(DEMO_EVENTS, model)

        # En démo avec données synthétiques, des bets peuvent être trouvés
        assert isinstance(bets, list)
        # Tous les bets respectent les filtres
        from src.core.config import settings
        for bet in bets:
            assert bet.ev >= settings.EV_THRESHOLD
            assert settings.MIN_ODDS <= bet.odds <= settings.MAX_ODDS

    @pytest.mark.asyncio
    async def test_whatsapp_demo_returns_success(self):
        """En DEMO_MODE, WhatsApp retourne success sans vraie API."""
        from src.messaging.whatsapp import WhatsAppClient

        async with WhatsAppClient() as client:
            result = await client.send_text_message("+33600000000", "Test message")

        assert result.success is True
        assert result.message_id == "demo_msg_id"

    @pytest.mark.asyncio
    async def test_formatters_produce_valid_text(self):
        """Les formatters produisent du texte non-vide et dans les limites."""
        from src.messaging.formatters import CouponFormatter, AlertFormatter
        from src.selection.selector import SelectedBet
        from datetime import datetime, timezone

        bet = SelectedBet(
            match_name="Arsenal vs Chelsea",
            league="EPL",
            kickoff_utc=datetime(2024, 12, 15, 15, 0, tzinfo=timezone.utc),
            market="h2h",
            outcome="home",
            outcome_label="Victoire Arsenal",
            bookmaker="bet365",
            odds=2.10,
            model_prob=0.52,
            fair_odds=2.25,
            ev=0.092,
            kelly_pct=0.021,
            confidence="high",
        )

        coupon = CouponFormatter().format([bet])
        assert len(coupon) > 100
        assert len(coupon) <= 4096
        assert "Arsenal" in coupon
        assert "+9.2%" in coupon

        alert = AlertFormatter().format(bet)
        assert len(alert) > 50
        assert "Arsenal" in alert
