"""
Configuration des jobs APScheduler.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.core.config import settings
from src.core.logging import get_logger

if TYPE_CHECKING:
    from src.scheduler.pipeline import Pipeline

logger = get_logger(__name__)


def configure_scheduler(pipeline: "Pipeline") -> BackgroundScheduler:
    """Configure et retourne le scheduler avec tous les jobs."""
    scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)

    # ── Job quotidien : pipeline complet ────────────────────────────────────
    scheduler.add_job(
        func=_run_async(job_daily_pipeline, pipeline),
        trigger=CronTrigger(
            hour=settings.BOT_SEND_HOUR,
            minute=settings.BOT_SEND_MINUTE,
            timezone=settings.TIMEZONE,
        ),
        id="daily_pipeline",
        name="Pipeline quotidien",
        replace_existing=True,
        misfire_grace_time=600,  # 10 min de grâce si le scheduler était arrêté
    )

    # ── Job horaire : mise à jour des cotes ─────────────────────────────────
    scheduler.add_job(
        func=_run_async(job_fetch_odds_hourly, pipeline),
        trigger=IntervalTrigger(minutes=settings.ODDS_FETCH_INTERVAL_MINUTES),
        id="fetch_odds_hourly",
        name="Fetch cotes (horaire)",
        replace_existing=True,
    )

    logger.info(
        "Scheduler configured",
        daily_at=f"{settings.BOT_SEND_HOUR:02d}:{settings.BOT_SEND_MINUTE:02d}",
        odds_interval_min=settings.ODDS_FETCH_INTERVAL_MINUTES,
    )

    return scheduler


def _run_async(coro_func: "Any", *args: "Any") -> "Any":
    """Wrapper pour exécuter une coroutine depuis un job synchrone APScheduler."""
    def wrapper() -> None:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(coro_func(*args))
        except Exception as e:
            logger.error("Job failed", job=coro_func.__name__, error=str(e))
        finally:
            loop.close()
    return wrapper


async def job_daily_pipeline(pipeline: "Pipeline") -> None:
    """Job quotidien : exécute le pipeline complet."""
    logger.info("Job: daily_pipeline starting")
    try:
        stats = await pipeline.run_daily()
        logger.info(
            "Job: daily_pipeline done",
            status=stats.status.value,
            bets=stats.bets_selected,
        )
    except Exception as e:
        logger.error("Job: daily_pipeline crashed", error=str(e))


async def job_fetch_odds_hourly(pipeline: "Pipeline") -> None:
    """Job horaire : met à jour les cotes pour les matchs futurs."""
    logger.info("Job: fetch_odds_hourly starting")
    try:
        events = await pipeline.odds_fetcher.fetch_all_leagues()
        logger.info("Job: fetch_odds_hourly done", n_events=len(events))
    except Exception as e:
        logger.error("Job: fetch_odds_hourly failed", error=str(e))
