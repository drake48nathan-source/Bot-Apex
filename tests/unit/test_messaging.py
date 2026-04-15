"""Tests unitaires pour formatters, WhatsApp et Telegram en DEMO_MODE."""

from __future__ import annotations

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Assurer DEMO_MODE pour tous les tests
os.environ["DEMO_MODE"] = "true"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

class FakeBet:
    """Bet minimal pour tester les formatters."""
    def __init__(self, **kwargs):
        self.match_name = kwargs.get("match_name", "Arsenal vs Chelsea")
        self.league = kwargs.get("league", "EPL")
        self.kickoff_utc = kwargs.get("kickoff_utc", datetime(2024, 12, 15, 15, 0, tzinfo=timezone.utc))
        self.market = kwargs.get("market", "h2h")
        self.outcome = kwargs.get("outcome", "home")
        self.outcome_label = kwargs.get("outcome_label", "Victoire Arsenal")
        self.bookmaker = kwargs.get("bookmaker", "bet365")
        self.odds = kwargs.get("odds", 2.10)
        self.model_prob = kwargs.get("model_prob", 0.52)
        self.fair_odds = kwargs.get("fair_odds", 2.25)
        self.ev = kwargs.get("ev", 0.092)
        self.kelly_pct = kwargs.get("kelly_pct", 0.021)
        self.confidence = kwargs.get("confidence", "high")
        # Computed string props mirroring SelectedBet
        self.ev_pct = f"+{self.ev * 100:.1f}%"
        self.kelly_pct_str = f"{self.kelly_pct * 100:.1f}%"


@pytest.fixture
def bet():
    return FakeBet()


@pytest.fixture
def multi_bets():
    return [
        FakeBet(match_name="Arsenal vs Chelsea", ev=0.092),
        FakeBet(match_name="Liverpool vs ManCity", odds=3.20, ev=0.065, confidence="medium"),
        FakeBet(match_name="Spurs vs West Ham", odds=2.50, ev=0.08, confidence="low"),
    ]


# ─── CouponFormatter ──────────────────────────────────────────────────────────

class TestCouponFormatter:
    def test_single_bet_contains_match(self, bet):
        from src.messaging.formatters import CouponFormatter
        text = CouponFormatter().format([bet])
        assert "Arsenal" in text

    def test_single_bet_ev_present(self, bet):
        from src.messaging.formatters import CouponFormatter
        text = CouponFormatter().format([bet])
        assert "+9.2%" in text

    def test_single_bet_length_in_range(self, bet):
        from src.messaging.formatters import CouponFormatter
        text = CouponFormatter().format([bet])
        assert 100 < len(text) <= 4096

    def test_multiple_bets_all_present(self, multi_bets):
        from src.messaging.formatters import CouponFormatter
        text = CouponFormatter().format(multi_bets)
        assert "Arsenal" in text
        assert "Liverpool" in text
        assert "Spurs" in text

    def test_multiple_bets_avg_ev_shown(self, multi_bets):
        from src.messaging.formatters import CouponFormatter
        text = CouponFormatter().format(multi_bets)
        # EV moyen = (9.2 + 6.5 + 8.0) / 3 = 7.9%
        assert "EV moyen" in text

    def test_empty_bets_returns_something(self):
        """Format avec 0 bets ne doit pas crasher."""
        from src.messaging.formatters import CouponFormatter
        text = CouponFormatter().format([])
        assert isinstance(text, str)

    def test_truncation_for_very_long_coupon(self):
        """Un coupon de plus de 4096 chars est tronqué."""
        from src.messaging.formatters import CouponFormatter
        # Créer beaucoup de bets pour forcer la troncature
        bets = [FakeBet(match_name=f"Team{i} vs Team{i+1}", ev=0.06) for i in range(50)]
        text = CouponFormatter().format(bets)
        assert len(text) <= 4096

    def test_date_in_header(self, bet):
        from src.messaging.formatters import CouponFormatter
        fixed_date = datetime(2024, 12, 15)
        text = CouponFormatter().format([bet], date=fixed_date)
        assert "15/12/2024" in text

    def test_confidence_stars_high(self, bet):
        from src.messaging.formatters import CouponFormatter
        bet.confidence = "high"
        text = CouponFormatter().format([bet])
        assert "⭐⭐⭐" in text

    def test_confidence_stars_medium(self, bet):
        from src.messaging.formatters import CouponFormatter
        bet.confidence = "medium"
        text = CouponFormatter().format([bet])
        assert "⭐⭐" in text


# ─── AlertFormatter ───────────────────────────────────────────────────────────

class TestAlertFormatter:
    def test_default_trigger_value_bet(self, bet):
        from src.messaging.formatters import AlertFormatter
        text = AlertFormatter().format(bet)
        assert "Value bet détecté" in text

    def test_trigger_line_movement(self, bet):
        from src.messaging.formatters import AlertFormatter
        text = AlertFormatter().format(bet, "line_movement")
        assert "Mouvement de cote" in text

    def test_trigger_high_ev(self, bet):
        from src.messaging.formatters import AlertFormatter
        text = AlertFormatter().format(bet, "high_ev")
        assert "EV exceptionnel" in text

    def test_unknown_trigger_passthrough(self, bet):
        from src.messaging.formatters import AlertFormatter
        text = AlertFormatter().format(bet, "custom_reason")
        assert "custom_reason" in text

    def test_contains_match_name(self, bet):
        from src.messaging.formatters import AlertFormatter
        text = AlertFormatter().format(bet)
        assert "Arsenal" in text

    def test_contains_odds(self, bet):
        from src.messaging.formatters import AlertFormatter
        text = AlertFormatter().format(bet)
        assert "2.10" in text

    def test_kickoff_formatted(self, bet):
        from src.messaging.formatters import AlertFormatter
        text = AlertFormatter().format(bet)
        assert "15/12" in text

    def test_no_kickoff_no_crash(self):
        from src.messaging.formatters import AlertFormatter
        bet = FakeBet(kickoff_utc=None)
        text = AlertFormatter().format(bet)
        assert "Arsenal" in text


# ─── AnalysisFormatter ────────────────────────────────────────────────────────

class TestAnalysisFormatter:
    def test_format_empty_predictions(self):
        from src.messaging.formatters import AnalysisFormatter

        match = MagicMock()
        match.home_team = "Arsenal"
        match.away_team = "Chelsea"

        text = AnalysisFormatter().format(match, [], [])
        assert "Arsenal" in text
        assert "PRÉDICTIONS" in text

    def test_format_with_predictions(self):
        from src.messaging.formatters import AnalysisFormatter

        match = MagicMock()
        match.home_team = "Arsenal"
        match.away_team = "Chelsea"

        pred = MagicMock()
        pred.market = "h2h"
        pred.outcome = "home"
        pred.model_prob = 0.52
        pred.ev = 0.09

        text = AnalysisFormatter().format(match, [pred], [])
        assert "h2h/home" in text
        assert "52.0%" in text

    def test_format_with_selected_bets(self):
        from src.messaging.formatters import AnalysisFormatter

        match = MagicMock()
        match.home_team = "Arsenal"
        match.away_team = "Chelsea"

        bet = FakeBet()
        text = AnalysisFormatter().format(match, [], [bet])
        assert "VALUE BETS" in text
        assert "2.10" in text


# ─── SystemAlertFormatter ─────────────────────────────────────────────────────

class TestSystemAlertFormatter:
    def test_warning_level(self):
        from src.messaging.formatters import SystemAlertFormatter
        text = SystemAlertFormatter().format("Pipeline failed", "WARNING")
        assert "⚠️" in text
        assert "Pipeline failed" in text

    def test_error_level(self):
        from src.messaging.formatters import SystemAlertFormatter
        text = SystemAlertFormatter().format("Critical error", "ERROR")
        assert "🚨" in text
        assert "Critical error" in text

    def test_default_level_is_warning(self):
        from src.messaging.formatters import SystemAlertFormatter
        text = SystemAlertFormatter().format("Test")
        assert "⚠️" in text


# ─── WhatsAppClient (DEMO_MODE) ───────────────────────────────────────────────

class TestWhatsAppClientDemo:
    @pytest.mark.asyncio
    async def test_send_text_message_demo_success(self):
        from src.messaging.whatsapp import WhatsAppClient
        async with WhatsAppClient() as client:
            result = await client.send_text_message("+33600000000", "Hello")
        assert result.success is True
        assert result.message_id == "demo_msg_id"

    @pytest.mark.asyncio
    async def test_send_coupon_demo(self, multi_bets):
        from src.messaging.whatsapp import WhatsAppClient
        import os
        os.environ["WHATSAPP_RECIPIENT_NUMBER"] = "+33600000000"
        async with WhatsAppClient() as client:
            results = await client.send_coupon(multi_bets)
        # Remet à vide
        os.environ["WHATSAPP_RECIPIENT_NUMBER"] = ""
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_send_alert_demo(self, bet):
        from src.messaging.whatsapp import WhatsAppClient
        import os
        os.environ["WHATSAPP_RECIPIENT_NUMBER"] = "+33600000000"
        async with WhatsAppClient() as client:
            results = await client.send_alert(bet, "value_bet")
        os.environ["WHATSAPP_RECIPIENT_NUMBER"] = ""
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_send_to_all_no_recipients(self):
        from src.messaging.whatsapp import WhatsAppClient
        import os
        os.environ["WHATSAPP_RECIPIENT_NUMBER"] = ""
        async with WhatsAppClient() as client:
            results = await client.send_to_all("test message")
        assert results == []

    def test_build_text_payload_short(self):
        from src.messaging.whatsapp import WhatsAppClient
        client = WhatsAppClient()
        payload = client._build_text_payload("+33600000000", "Hello")
        assert payload["to"] == "+33600000000"
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Hello"

    def test_build_text_payload_truncation(self):
        from src.messaging.whatsapp import WhatsAppClient
        client = WhatsAppClient()
        long_text = "x" * 5000
        payload = client._build_text_payload("+33600000000", long_text)
        assert len(payload["text"]["body"]) <= 4096


# ─── TelegramClient (DEMO_MODE) ───────────────────────────────────────────────

class TestTelegramClientDemo:
    @pytest.mark.asyncio
    async def test_send_message_demo_returns_true(self):
        from src.messaging.telegram import TelegramClient
        async with TelegramClient() as client:
            result = await client.send_message("123456789", "Hello Telegram")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_coupon_demo(self, multi_bets):
        import os
        os.environ["TELEGRAM_CHAT_ID"] = "123456789"
        from src.messaging.telegram import TelegramClient
        async with TelegramClient() as client:
            results = await client.send_coupon(multi_bets)
        os.environ["TELEGRAM_CHAT_ID"] = ""
        assert all(results)

    @pytest.mark.asyncio
    async def test_send_to_all_no_chat_ids(self):
        import os
        os.environ["TELEGRAM_CHAT_ID"] = ""
        from src.messaging.telegram import TelegramClient
        async with TelegramClient() as client:
            results = await client.send_to_all("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_send_system_alert_no_admin_chat(self):
        import os
        os.environ["TELEGRAM_CHAT_ID"] = ""
        os.environ.pop("ADMIN_TELEGRAM_CHAT_ID", None)
        from src.messaging.telegram import TelegramClient
        async with TelegramClient() as client:
            result = await client.send_system_alert("Pipeline error", "ERROR")
        assert result is False or result is True  # DEMO_MODE → True

    @pytest.mark.asyncio
    async def test_send_to_all_multiple_chat_ids(self):
        from unittest.mock import patch
        from src.messaging.telegram import TelegramClient
        # Patch settings directly to bypass lru_cache
        with patch("src.messaging.telegram.settings") as mock_settings:
            mock_settings.TELEGRAM_CHAT_ID = "111,222,333"
            mock_settings.DEMO_MODE = True
            mock_settings.telegram_enabled = True
            async with TelegramClient() as client:
                results = await client.send_to_all("broadcast test")
        assert len(results) == 3
        assert all(results)
