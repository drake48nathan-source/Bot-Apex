"""
Définition des jobs APScheduler du bot Apex V2.

Ce module configure le planning des tâches récurrentes.
Les fonctions de job sont des wrappers légers qui délèguent au Pipeline.

Jobs configurés :

1. job_daily_pipeline
   Heure : BOT_SEND_HOUR:BOT_SEND_MINUTE (configurable, défaut 09:00 Europe/Paris)
   Action : Run complet du pipeline (fetch → prédictions → sélection → envoi coupon)

2. job_fetch_odds_hourly
   Heure : Toutes les ODDS_FETCH_INTERVAL_MINUTES minutes
   Action : Mise à jour des cotes pour les matchs J+1 à J+7

3. job_fetch_odds_live
   Heure : Toutes les ODDS_FETCH_LIVE_INTERVAL_MINUTES minutes (matchs J0 uniquement)
   Action : Mise à jour des cotes pour les matchs du jour

4. job_weekly_report
   Heure : Chaque lundi à 09h00 (timezone configurée)
   Action : Rapport hebdomadaire ROI + statistiques de la semaine

Usage:
    from src.scheduler.jobs import configure_scheduler
    scheduler = configure_scheduler(pipeline)
    scheduler.start()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

if TYPE_CHECKING:
    from src.scheduler.pipeline import Pipeline


def configure_scheduler(pipeline: "Pipeline") -> AsyncIOScheduler:
    """
    Configure et retourne le scheduler APScheduler avec tous les jobs.

    Utilise AsyncIOScheduler pour la compatibilité avec le code async du pipeline.
    Le scheduler utilise la timezone configurée dans Settings (TIMEZONE).

    Args:
        pipeline: Instance du Pipeline orchestrateur.

    Returns:
        AsyncIOScheduler configuré mais pas encore démarré.
        Appeler scheduler.start() pour lancer les jobs.
    """
    raise NotImplementedError


async def job_daily_pipeline(pipeline: "Pipeline") -> None:
    """
    Job quotidien : exécute le pipeline complet.

    Wrapper autour de pipeline.run_daily() avec logging du résultat.
    Les erreurs sont capturées pour ne pas faire planter le scheduler.

    Args:
        pipeline: Instance du Pipeline.
    """
    raise NotImplementedError


async def job_fetch_odds_hourly(pipeline: "Pipeline") -> None:
    """
    Job horaire : met à jour les cotes pour les matchs J+1 à J+7.

    Ne génère pas de prédictions, uniquement de la collecte de données.
    Permet d'avoir des cotes fraîches pour les alertes de line movement.

    Args:
        pipeline: Instance du Pipeline.
    """
    raise NotImplementedError


async def job_fetch_odds_live(pipeline: "Pipeline") -> None:
    """
    Job live (toutes les 15 min) : cotes des matchs du jour.

    Déclenche une alerte WhatsApp si une cote bouge de plus de 10%
    sur un pari déjà dans le coupon du jour.

    Args:
        pipeline: Instance du Pipeline.
    """
    raise NotImplementedError


async def job_weekly_report(pipeline: "Pipeline") -> None:
    """
    Job hebdomadaire : rapport de performance de la semaine.

    Calcule :
    - ROI de la semaine (pnl / total misé)
    - Win rate (paris gagnés / paris réglés)
    - Meilleur pari de la semaine
    - Pire pari de la semaine

    Envoie le rapport via WhatsApp + Telegram.

    Args:
        pipeline: Instance du Pipeline.
    """
    raise NotImplementedError
