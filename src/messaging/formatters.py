"""
Formateurs de messages pour WhatsApp et Telegram.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.config import settings


CONFIDENCE_STARS = {"low": "⭐", "medium": "⭐⭐", "high": "⭐⭐⭐"}

SEPARATOR = "━" * 28


class CouponFormatter:
    """Formate le coupon quotidien de value bets."""

    MAX_LENGTH = 4096

    def format(self, bets: list[Any], date: datetime | None = None) -> str:
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%d/%m/%Y")
        lines = [
            f"🎯 *APEX BOT — Coupon du {date_str}*",
            "",
            f"📊 FOOTBALL — {len(bets)} value bet{'s' if len(bets) > 1 else ''}",
            SEPARATOR,
            "",
        ]

        for i, bet in enumerate(bets, 1):
            lines.extend(self._format_single_bet(bet, i))
            lines.append("")

        lines.append(SEPARATOR)

        if bets:
            avg_ev = sum(b.ev for b in bets) / len(bets)
            lines.append(f"📈 EV moyen du coupon : +{avg_ev * 100:.1f}%")

        lines.extend([
            f"💰 Mise recommandée : 2-3% de bankroll par pari",
            "",
            "⚠️ _Paris à titre informatif uniquement_",
            "_Jouez de manière responsable_",
        ])

        text = "\n".join(lines)
        if len(text) > self.MAX_LENGTH:
            text = text[: self.MAX_LENGTH - 20] + "\n...[tronqué]"
        return text

    def _format_single_bet(self, bet: Any, index: int) -> list[str]:
        stars = CONFIDENCE_STARS.get(getattr(bet, "confidence", "medium"), "⭐⭐")
        kickoff = getattr(bet, "kickoff_utc", None)
        if kickoff:
            try:
                kickoff_str = kickoff.strftime("%H:%M UTC")
            except Exception:
                kickoff_str = ""
        else:
            kickoff_str = ""

        label = getattr(bet, "outcome_label", bet.outcome) if hasattr(bet, "outcome_label") else str(bet)
        ev_str = getattr(bet, "ev_pct", f"+{bet.ev*100:.1f}%") if hasattr(bet, "ev_pct") else ""
        kelly_str = getattr(bet, "kelly_pct_str", "") if hasattr(bet, "kelly_pct_str") else ""

        return [
            f"*{index}️⃣  {bet.match_name}*  {kickoff_str}",
            f"   Marché : {label}",
            f"   Cote : {bet.odds:.2f} @ {bet.bookmaker.upper()}",
            f"   EV : {ev_str} | Kelly : {kelly_str}",
            f"   Confiance : {stars}",
        ]


class AlertFormatter:
    """Formate les alertes value bet unitaires."""

    def format(self, bet: Any, trigger_reason: str = "value_bet") -> str:
        reason_labels = {
            "value_bet": "Value bet détecté",
            "line_movement": "Mouvement de cote",
            "high_ev": "EV exceptionnel",
        }
        reason_label = reason_labels.get(trigger_reason, trigger_reason)

        kickoff = getattr(bet, "kickoff_utc", None)
        kickoff_str = ""
        if kickoff:
            try:
                kickoff_str = kickoff.strftime("%d/%m %H:%M UTC")
            except Exception:
                pass

        label = getattr(bet, "outcome_label", bet.outcome) if hasattr(bet, "outcome_label") else ""
        ev_str = getattr(bet, "ev_pct", "") if hasattr(bet, "ev_pct") else ""
        kelly_str = getattr(bet, "kelly_pct_str", "") if hasattr(bet, "kelly_pct_str") else ""

        return "\n".join([
            f"⚡ *ALERTE VALUE BET — {reason_label}*",
            "",
            f"⚽ *{bet.match_name}*",
            f"🕐 Coup d'envoi : {kickoff_str}",
            "",
            f"📊 Marché : {label}",
            f"💶 Cote : {bet.odds:.2f} @ {bet.bookmaker.upper()}",
            f"📈 EV : {ev_str}",
            f"⚖️ Kelly : {kelly_str}",
            "",
            SEPARATOR,
            "⚠️ _Information uniquement | Vérifiez les cotes avant de parier_",
        ])


class AnalysisFormatter:
    """Formate l'analyse détaillée d'un match."""

    def format(
        self,
        match: Any,
        predictions: list[Any],
        selected_bets: list[Any],
        team_stats: dict[str, Any] | None = None,
    ) -> str:
        home = getattr(match, "home_team", "Home")
        away = getattr(match, "away_team", "Away")

        lines = [
            f"🔍 *ANALYSE — {home} vs {away}*",
            "",
            SEPARATOR,
            "*📊 PRÉDICTIONS MODÈLE*",
            "",
        ]

        # Afficher les prédictions disponibles
        for pred in predictions:
            market = getattr(pred, "market", "")
            outcome = getattr(pred, "outcome", "")
            prob = getattr(pred, "model_prob", 0.0)
            ev = getattr(pred, "ev", None)
            ev_str = f"  EV: +{ev*100:.1f}%" if ev and ev > 0 else ""
            lines.append(f"   {market}/{outcome}: {prob*100:.1f}%{ev_str}")

        lines.append("")
        lines.append(SEPARATOR)

        if selected_bets:
            lines.append("*⚡ VALUE BETS DÉTECTÉS*")
            lines.append("")
            for bet in selected_bets:
                ev_str = getattr(bet, "ev_pct", "")
                label = getattr(bet, "outcome_label", bet.outcome) if hasattr(bet, "outcome_label") else ""
                lines.append(f"✅ {label} @ {bet.odds:.2f} — EV {ev_str}")
            lines.append("")
            lines.append(SEPARATOR)

        lines.extend([
            "",
            "⚠️ _Information uniquement | Pariez de manière responsable_",
        ])

        return "\n".join(lines)


class SystemAlertFormatter:
    """Formate les alertes système (erreurs pipeline, etc.)."""

    def format(self, message: str, level: str = "WARNING") -> str:
        icon = "🚨" if level == "ERROR" else "⚠️"
        return f"{icon} *SYSTÈME APEX BOT*\n\n{message}"
