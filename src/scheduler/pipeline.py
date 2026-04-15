"""
Pipeline orchestrateur principal du bot Apex V2.

Modes :
  python -m src.scheduler.pipeline           → scheduler complet
  python -m src.scheduler.pipeline --run-once → run unique
  python -m src.scheduler.pipeline --run-once --dry-run → sans envoi messages
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.core.config import settings
from src.core.database import get_db, init_db
from src.core.logging import add_context, clear_context, get_logger

logger = get_logger(__name__)


class PipelineStatus(Enum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILURE = "failure"


@dataclass
class PipelineRunStats:
    run_type: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    status: PipelineStatus = PipelineStatus.RUNNING
    matches_fetched: int = 0
    predictions_made: int = 0
    bets_selected: int = 0
    alerts_sent: int = 0
    errors: list[str] = field(default_factory=list)
    error_message: str = ""

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()


class Pipeline:
    """Orchestrateur principal du bot Apex V2."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._initialized = False

        # Import ici pour éviter les imports circulaires au démarrage
        from src.data.fetchers.football import FootballFetcher
        from src.data.fetchers.odds import OddsFetcher
        from src.messaging.telegram import TelegramClient
        from src.messaging.whatsapp import WhatsAppClient
        from src.models.dixon_coles import DixonColesModel
        from src.selection.selector import ValueBetSelector

        self.odds_fetcher = OddsFetcher()
        self.football_fetcher = FootballFetcher()
        self.model = DixonColesModel(xi=settings.DIXON_COLES_XI)
        self.selector = ValueBetSelector()
        self.whatsapp = WhatsAppClient()
        self.telegram = TelegramClient()

    async def _ensure_initialized(self) -> None:
        """Initialise la base de données et calibre le modèle au premier run."""
        if self._initialized:
            return

        # Créer les tables si elles n'existent pas
        init_db()
        logger.info("Database initialized")

        # Calibrer le modèle avec des données historiques
        await self._calibrate_model()
        self._initialized = True

    async def _calibrate_model(self) -> None:
        """Télécharge les données historiques et calibre Dixon-Coles."""
        logger.info("Calibrating Dixon-Coles model...")
        all_matches: list[dict] = []

        for league in settings.football_leagues_list:
            for season_offset in range(settings.DIXON_COLES_SEASONS):
                season = 2024 - season_offset
                try:
                    matches = await self.football_fetcher.fetch_historical_matches(league, season)
                    all_matches.extend(matches)
                except Exception as e:
                    logger.warning("Failed to fetch historical data", league=league, season=season, error=str(e))

        if all_matches:
            self.model.fit(all_matches)
            logger.info("Model calibrated", n_matches=len(all_matches))
        else:
            logger.error("No historical data available for calibration")

    async def run_daily(self) -> PipelineRunStats:
        """
        Exécute le pipeline quotidien complet.

        Étapes :
        1. Fetch des cotes (The Odds API)
        2. Prédictions Dixon-Coles
        3. Sélection des value bets
        4. Envoi du coupon WhatsApp + Telegram
        5. Sauvegarde des stats
        """
        stats = PipelineRunStats(run_type="daily")
        run_id = stats.started_at.strftime("%Y%m%d_%H%M%S")
        add_context(pipeline_run_id=run_id)

        logger.info("Pipeline daily run started", dry_run=self.dry_run)

        try:
            await self._ensure_initialized()

            # ── Étape 1 : Fetch des cotes ───────────────────────────────────
            events = await self._step_fetch_odds(stats)

            # ── Étape 2 : Prédictions ───────────────────────────────────────
            bets = await self._step_predict_and_select(events, stats)

            # ── Étape 3 : Envoi du coupon ───────────────────────────────────
            if bets and not self.dry_run:
                await self._step_send_coupon(bets, stats)
            elif bets and self.dry_run:
                logger.info("DRY RUN: skipping message send", n_bets=len(bets))
                for bet in bets:
                    logger.info(
                        "Would send",
                        match=bet.match_name,
                        market=bet.market,
                        ev=f"{bet.ev*100:.1f}%",
                        odds=bet.odds,
                    )
            else:
                logger.warning("No value bets found today")

            stats.status = PipelineStatus.SUCCESS
            if stats.errors:
                stats.status = PipelineStatus.PARTIAL_FAILURE

        except Exception as e:
            logger.error("Pipeline failed", error=str(e))
            stats.status = PipelineStatus.FAILURE
            stats.error_message = str(e)
            # Notifier l'admin
            try:
                await self.telegram.send_system_alert(
                    f"Pipeline daily run FAILED:\n{str(e)}", level="ERROR"
                )
            except Exception:
                pass

        finally:
            stats.finished_at = datetime.now(timezone.utc)
            logger.info(
                "Pipeline run finished",
                status=stats.status.value,
                duration_s=round(stats.duration_seconds or 0, 1),
                matches=stats.matches_fetched,
                predictions=stats.predictions_made,
                bets=stats.bets_selected,
                alerts=stats.alerts_sent,
            )
            clear_context()

        return stats

    async def _step_fetch_odds(self, stats: PipelineRunStats) -> list[dict]:
        """Étape 1 : Récupère les cotes pour toutes les ligues configurées."""
        logger.info("Step 1: Fetching odds")
        try:
            events = await self.odds_fetcher.fetch_all_leagues()
            stats.matches_fetched = len(events)
            logger.info("Odds fetched", n_events=len(events))
            return events
        except Exception as e:
            stats.errors.append(f"Odds fetch failed: {e}")
            logger.error("Odds fetch failed", error=str(e))
            return []

    async def _step_predict_and_select(
        self, events: list[dict], stats: PipelineRunStats
    ) -> list[Any]:
        """Étapes 2+3 : Génère les prédictions et sélectionne les value bets."""
        if not events:
            return []

        logger.info("Step 2-3: Predicting and selecting value bets")

        if not self.model.is_fitted:
            logger.warning("Model not fitted, skipping predictions")
            return []

        bets = self.selector.select_from_events(events, self.model)
        stats.predictions_made = len(events) * 5  # 5 marchés par match
        stats.bets_selected = len(bets)

        # Sauvegarder les prédictions en base
        if bets:
            self._save_predictions_to_db(bets)

        return bets

    async def _step_send_coupon(self, bets: list[Any], stats: PipelineRunStats) -> None:
        """Étape 4 : Envoie le coupon WhatsApp (avec fallback Telegram)."""
        logger.info("Step 4: Sending coupon", n_bets=len(bets))

        wa_results = await self.whatsapp.send_coupon(bets)
        wa_success = sum(1 for r in wa_results if r.success)
        stats.alerts_sent += wa_success

        # Fallback Telegram si WhatsApp échoue ou n'est pas configuré
        if wa_success == 0 or not settings.whatsapp_enabled:
            tg_results = await self.telegram.send_coupon(bets)
            stats.alerts_sent += sum(1 for r in tg_results if r)

        logger.info(
            "Coupon sent",
            wa_sent=wa_success,
            total_sent=stats.alerts_sent,
        )

    def _save_predictions_to_db(self, bets: list[Any]) -> None:
        """Sauvegarde les prédictions sélectionnées en base."""
        try:
            from src.data.models.match import Match
            from src.data.models.prediction import Prediction

            with get_db() as db:
                for bet in bets:
                    # Upsert match
                    match = db.query(Match).filter(
                        Match.external_id == bet.match_id
                    ).first()
                    if not match:
                        match = Match(
                            external_id=bet.match_id or f"auto_{bet.match_name}",
                            sport="football",
                            league=bet.league,
                            home_team=bet.match_name.split(" vs ")[0],
                            away_team=bet.match_name.split(" vs ")[-1],
                            kickoff_utc=bet.kickoff_utc,
                        )
                        db.add(match)
                        db.flush()

                    pred = Prediction(
                        match_id=match.id,
                        market=bet.market,
                        outcome=bet.outcome,
                        model_prob=bet.model_prob,
                        best_bookmaker=bet.bookmaker,
                        best_odds=bet.odds,
                        fair_odds=bet.fair_odds,
                        ev=bet.ev,
                        kelly_fraction=bet.kelly_pct,
                        confidence=bet.confidence,
                    )
                    db.add(pred)
                db.commit()
                logger.info("Predictions saved to DB", n=len(bets))
        except Exception as e:
            logger.error("Failed to save predictions", error=str(e))

    def run(self) -> None:
        """Lance le scheduler APScheduler complet."""
        from src.scheduler.jobs import configure_scheduler

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        scheduler = configure_scheduler(self)

        # Gestion gracieuse des signaux
        def shutdown(sig: int, frame: Any) -> None:
            logger.info("Shutdown signal received", signal=sig)
            scheduler.shutdown(wait=False)
            loop.stop()

        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)

        logger.info(
            "Apex Bot V2 scheduler starting",
            send_hour=settings.BOT_SEND_HOUR,
            send_minute=settings.BOT_SEND_MINUTE,
            demo_mode=settings.DEMO_MODE,
        )

        scheduler.start()
        try:
            loop.run_forever()
        finally:
            loop.close()
            logger.info("Scheduler stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apex Bot V2 — Pipeline de prédiction sportive")
    parser.add_argument("--run-once", action="store_true", help="Exécuter une seule fois")
    parser.add_argument("--dry-run", action="store_true", help="Sans envoi de messages")
    args = parser.parse_args()

    pipeline = Pipeline(dry_run=args.dry_run)

    if args.run_once:
        stats = asyncio.run(pipeline.run_daily())
        code = 0 if stats.status in (PipelineStatus.SUCCESS, PipelineStatus.PARTIAL_FAILURE) else 1
        sys.exit(code)
    else:
        pipeline.run()


if __name__ == "__main__":
    main()
