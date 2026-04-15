"""
Bot Telegram/WhatsApp — Point d'entrée des commandes utilisateur.

Commandes Telegram disponibles :
  /coupon    → Envoie le coupon du jour (recalcule si besoin)
  /analyse   → Analyse détaillée d'un match (usage: /analyse Arsenal Chelsea)
  /alerte    → Active/désactive les alertes temps réel
  /stats     → Statistiques de performance (ROI, win rate)
  /ping      → Vérification que le bot est en ligne

Ce module utilise l'API Bot Telegram directement (pas python-telegram-bot)
pour garder la dépendance légère en Phase 1.

Usage :
  python -m src.bot                          → démarre le long-polling
  python -m src.scheduler.pipeline --run-once → pipeline une fois (sans bot)
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from typing import Any

import httpx

from src.core.config import settings
from src.core.database import get_db, init_db
from src.core.logging import get_logger
from src.messaging.formatters import AnalysisFormatter, CouponFormatter, SystemAlertFormatter
from src.messaging.telegram import TelegramClient

logger = get_logger(__name__)


class ApexBot:
    """
    Bot Telegram avec long-polling.

    Écoute les mises à jour Telegram et dispatche vers les handlers de commandes.
    Partage le Pipeline pour recalculer le coupon à la demande.
    """

    TELEGRAM_BASE = "https://api.telegram.org"

    def __init__(self) -> None:
        self.telegram = TelegramClient()
        self._client: httpx.AsyncClient | None = None
        self._offset: int = 0
        self._pipeline: Any = None  # Lazy init

        # Formatters
        self._coupon_fmt = CouponFormatter()
        self._analysis_fmt = AnalysisFormatter()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=35.0)
        return self._client

    def _url(self, method: str) -> str:
        return f"{self.TELEGRAM_BASE}/bot{settings.TELEGRAM_TOKEN}/{method}"

    async def _get_updates(self) -> list[dict]:
        """Long-polling : attend les nouvelles mises à jour Telegram."""
        client = self._get_client()
        try:
            resp = await client.post(
                self._url("getUpdates"),
                json={"offset": self._offset, "timeout": 30, "allowed_updates": ["message"]},
            )
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
        except httpx.TimeoutException:
            pass  # Timeout normal du long-polling
        except Exception as e:
            logger.error("GetUpdates failed", error=str(e))
        return []

    async def _send_reply(self, chat_id: str | int, text: str) -> None:
        """Envoie une réponse au chat."""
        await self.telegram.send_message(str(chat_id), text)

    async def _handle_update(self, update: dict) -> None:
        """Dispatche une mise à jour vers le bon handler."""
        message = update.get("message", {})
        text = message.get("text", "").strip()
        chat_id = message.get("chat", {}).get("id", "")

        if not text or not chat_id:
            return

        logger.info("Incoming command", chat_id=chat_id, text=text[:50])

        if text.startswith("/coupon"):
            await self._handle_coupon(chat_id)
        elif text.startswith("/analyse"):
            parts = text.split(maxsplit=1)
            args = parts[1] if len(parts) > 1 else ""
            await self._handle_analyse(chat_id, args)
        elif text.startswith("/stats"):
            await self._handle_stats(chat_id)
        elif text.startswith("/ping"):
            await self._handle_ping(chat_id)
        elif text.startswith("/start") or text.startswith("/help"):
            await self._handle_help(chat_id)
        else:
            await self._send_reply(chat_id, "Commande inconnue. Tapez /help pour la liste.")

    async def _handle_coupon(self, chat_id: str | int) -> None:
        """Recalcule et envoie le coupon du jour."""
        await self._send_reply(chat_id, "⏳ Calcul du coupon en cours...")

        pipeline = await self._get_pipeline()
        stats_obj = await pipeline.run_daily()

        if stats_obj.bets_selected == 0:
            await self._send_reply(chat_id, "📊 Aucun value bet détecté aujourd'hui.")
        else:
            await self._send_reply(
                chat_id,
                f"✅ Coupon envoyé ({stats_obj.bets_selected} paris sélectionnés)",
            )

    async def _handle_analyse(self, chat_id: str | int, args: str) -> None:
        """Génère l'analyse détaillée d'un match."""
        if not args:
            await self._send_reply(
                chat_id,
                "Usage : /analyse Arsenal Chelsea\nFournissez les deux équipes séparées par un espace.",
            )
            return

        # Parser "Arsenal Chelsea" ou "Arsenal vs Chelsea"
        teams = args.replace(" vs ", " ").replace(" VS ", " ").split()
        if len(teams) < 2:
            await self._send_reply(chat_id, "Spécifiez deux équipes : /analyse Arsenal Chelsea")
            return

        home_team = teams[0].title()
        away_team = teams[1].title()
        await self._send_reply(chat_id, f"⏳ Analyse de {home_team} vs {away_team}...")

        pipeline = await self._get_pipeline()
        if not pipeline.model.is_fitted:
            await self._send_reply(chat_id, "❌ Modèle non calibré. Relancez le pipeline.")
            return

        try:
            matrix = pipeline.model.predict_score_matrix(home_team, away_team)
            from src.models.markets import result as result_mkt, totals, btts

            r = result_mkt.compute(matrix)
            t = totals.compute(matrix, 2.5)
            b = btts.compute(matrix)

            text = "\n".join([
                f"🔍 *Analyse — {home_team} vs {away_team}*",
                "",
                "📊 *PRÉDICTIONS MODÈLE*",
                f"   Victoire {home_team} : {r['home']*100:.1f}%",
                f"   Match Nul : {r['draw']*100:.1f}%",
                f"   Victoire {away_team} : {r['away']*100:.1f}%",
                "",
                f"   Over 2.5 : {t['over']*100:.1f}%",
                f"   BTTS Oui : {b['yes']*100:.1f}%",
                "",
                "⚠️ _Information uniquement_",
            ])
            await self._send_reply(chat_id, text)
        except Exception as e:
            await self._send_reply(chat_id, f"❌ Erreur : {str(e)}")

    async def _handle_stats(self, chat_id: str | int) -> None:
        """Affiche les statistiques de performance depuis la DB."""
        try:
            from src.data.models.bet import Bet
            from src.data.models.prediction import Prediction

            with get_db() as db:
                total_preds = db.query(Prediction).count()
                bets = db.query(Bet).all()
                settled = [b for b in bets if b.is_settled]

                if not settled:
                    await self._send_reply(
                        chat_id,
                        f"📈 *Statistiques*\n\nPrédictions générées : {total_preds}\nAucun pari réglé pour l'instant.",
                    )
                    return

                wins = sum(1 for b in settled if b.result == "win")
                total_pnl = sum((b.pnl or 0) for b in settled)
                total_stake = sum(b.stake for b in settled)
                roi = (total_pnl / total_stake * 100) if total_stake > 0 else 0.0
                win_rate = wins / len(settled) * 100

                text = "\n".join([
                    "📈 *Statistiques de performance*",
                    "",
                    f"Prédictions générées : {total_preds}",
                    f"Paris réglés : {len(settled)}",
                    f"Win rate : {win_rate:.1f}%",
                    f"P&L total : {total_pnl:+.1f} unités",
                    f"ROI : {roi:+.1f}%",
                ])
                await self._send_reply(chat_id, text)
        except Exception as e:
            await self._send_reply(chat_id, f"❌ Erreur : {str(e)}")

    async def _handle_ping(self, chat_id: str | int) -> None:
        now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        model_status = "calibré ✅" if (self._pipeline and self._pipeline.model.is_fitted) else "non calibré ⚠️"
        await self._send_reply(
            chat_id,
            f"🤖 *Apex Bot V2 — En ligne*\n\n🕐 {now}\n🧠 Modèle : {model_status}\n🎯 Demo mode : {settings.DEMO_MODE}",
        )

    async def _handle_help(self, chat_id: str | int) -> None:
        await self._send_reply(
            chat_id,
            "\n".join([
                "🤖 *Apex Bot V2 — Commandes disponibles*",
                "",
                "/coupon → Coupon value bets du jour",
                "/analyse [equipe1] [equipe2] → Analyse d'un match",
                "/stats → Statistiques de performance",
                "/ping → Vérifier que le bot est en ligne",
                "/help → Cette aide",
                "",
                "_Développé avec Claude Code_",
            ]),
        )

    async def _get_pipeline(self) -> Any:
        """Retourne le pipeline (lazy init + calibration au premier appel)."""
        if self._pipeline is None:
            from src.scheduler.pipeline import Pipeline
            self._pipeline = Pipeline(dry_run=False)
            await self._pipeline._ensure_initialized()
        return self._pipeline

    async def run(self) -> None:
        """Démarre le long-polling Telegram."""
        if not settings.TELEGRAM_TOKEN:
            logger.error("TELEGRAM_TOKEN not set, bot cannot start")
            return

        init_db()
        logger.info("Apex Bot V2 Telegram bot starting", demo_mode=settings.DEMO_MODE)

        while True:
            try:
                updates = await self._get_updates()
                for update in updates:
                    self._offset = update["update_id"] + 1
                    await self._handle_update(update)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Bot loop error", error=str(e))
                await asyncio.sleep(5)

        await self.telegram.close()
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        logger.info("Bot stopped")


def main() -> None:
    """Point d'entrée CLI : python -m src.bot"""
    bot = ApexBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")


if __name__ == "__main__":
    main()
