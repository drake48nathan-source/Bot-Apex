"""
Pipeline orchestrateur principal du bot Apex V2.

Ce module est le point d'entrée de l'application en production.
Il instancie et orchestre tous les composants dans le bon ordre,
gère les erreurs de manière centralisée et fournit des logs structurés
pour chaque étape d'exécution.

Modes d'exécution :
1. Scheduler complet (production) : `python -m src.scheduler.pipeline`
   → Lance APScheduler avec tous les jobs configurés (quotidien, horaire, hebdo)
   → Tourne indéfiniment jusqu'à interruption (SIGTERM/SIGINT)

2. Run unique (test/debug) : `python -m src.scheduler.pipeline --run-once`
   → Exécute le pipeline quotidien une seule fois et s'arrête

Pipeline quotidien (exécuté à 06h00 UTC) :
    Étape 1 : Fetch des cotes (The Odds API) pour les matchs J0 à J+7
    Étape 2 : Fetch des stats football (API-Football) pour les équipes des matchs J0
    Étape 3 : Prédiction Dixon-Coles pour chaque match J0
    Étape 4 : Calcul des value bets (démarginisation + EV + Kelly)
    Étape 5 : Sélection des top N value bets du jour
    Étape 6 : Formatage du coupon WhatsApp
    Étape 7 : Envoi WhatsApp (avec fallback Telegram si échec)
    Étape 8 : Sauvegarde du run en base (table pipeline_runs)

Usage:
    # Production
    python -m src.scheduler.pipeline

    # Test
    python -m src.scheduler.pipeline --run-once
    python -m src.scheduler.pipeline --run-once --dry-run  # Sans envoi WhatsApp
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PipelineStatus(Enum):
    """Statuts possibles d'un run de pipeline."""

    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"  # Certaines étapes ont échoué, mais le message a été envoyé
    FAILURE = "failure"  # Échec critique, message non envoyé


@dataclass
class PipelineRunStats:
    """
    Statistiques collectées pendant un run de pipeline.

    Attributes:
        run_type: Type de run ('daily', 'hourly_odds', 'weekly_report').
        started_at: Timestamp de début du run.
        finished_at: Timestamp de fin (None si en cours).
        status: Statut final du run.
        matches_fetched: Nombre de matchs récupérés depuis les APIs.
        predictions_made: Nombre de prédictions générées par le modèle.
        bets_selected: Nombre de value bets sélectionnés pour le coupon.
        alerts_sent: Nombre de messages WhatsApp/Telegram envoyés avec succès.
        errors: Liste des erreurs non fatales rencontrées.
        error_message: Message d'erreur principal si le run a échoué.
    """

    run_type: str
    started_at: datetime = field(default_factory=datetime.utcnow)
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
        """Durée du run en secondes. None si pas encore terminé."""
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()


class Pipeline:
    """
    Orchestrateur principal du bot Apex V2.

    Instancie et coordonne tous les composants :
    - OddsFetcher et FootballFetcher pour la collecte
    - DixonColesModel pour les prédictions
    - ValueCalculator et ValueBetSelector pour la sélection
    - WhatsAppClient et TelegramClient pour la messagerie

    Le scheduler APScheduler est configuré dans run() et appelle
    run_daily() selon le planning configuré dans settings.
    """

    def __init__(self, dry_run: bool = False) -> None:
        """
        Initialise le pipeline et tous ses composants.

        Args:
            dry_run: Si True, skip l'envoi des messages WhatsApp/Telegram.
                    Utile pour le test et le debug. Les prédictions sont quand
                    même calculées et sauvegardées en base.
        """
        raise NotImplementedError

    async def run_daily(self) -> PipelineRunStats:
        """
        Exécute le pipeline quotidien complet.

        Collecte les données → Génère les prédictions → Sélectionne les value bets
        → Envoie le coupon WhatsApp → Sauvegarde les stats.

        En cas d'erreur sur une étape non-critique (ex: certains matchs échouent),
        continue avec les données disponibles et note l'erreur dans les stats.

        En cas d'erreur critique (ex: aucune donnée récupérée), bascule en FAILURE
        et envoie une alerte au canal admin (Telegram).

        Returns:
            PipelineRunStats avec les statistiques complètes du run.
        """
        raise NotImplementedError

    async def _step_fetch_odds(self, stats: PipelineRunStats) -> list[Any]:
        """
        Étape 1 : Fetch des cotes depuis The Odds API.

        Récupère les cotes pour toutes les ligues configurées (settings.FOOTBALL_LEAGUES),
        pour les marchés de la Phase 1 (h2h, totals, btts, asian_handicap, double_chance).

        Met à jour stats.matches_fetched.

        Args:
            stats: Objet stats du run courant (mis à jour en place).

        Returns:
            Liste des matchs avec leurs cotes.
        """
        raise NotImplementedError

    async def _step_fetch_football_stats(
        self, matches: list[Any], stats: PipelineRunStats
    ) -> dict[str, Any]:
        """
        Étape 2 : Fetch des statistiques football depuis API-Football.

        Pour chaque équipe dans les matchs du jour, récupère :
        - Statistiques de la saison (buts pour/contre, xG si disponible)
        - Forme récente (5 derniers matchs)
        - H2H (5 derniers face-à-face)

        Args:
            matches: Liste des matchs du jour (avec home_team_id, away_team_id).
            stats: Objet stats du run courant.

        Returns:
            Dict {team_id: TeamStats} avec les statistiques par équipe.
        """
        raise NotImplementedError

    async def _step_predict(
        self, matches: list[Any], team_stats: dict, stats: PipelineRunStats
    ) -> list[Any]:
        """
        Étape 3 : Génération des prédictions Dixon-Coles pour chaque match.

        Charge le modèle calibré depuis la base de données (une instance par ligue).
        Calcule la matrice de scores pour chaque match.
        Dérive les probabilités pour chaque marché actif.
        Sauvegarde les prédictions en base (table predictions).

        Args:
            matches: Liste des matchs à prédire.
            team_stats: Stats d'équipe collectées à l'étape précédente.
            stats: Objet stats du run courant.

        Returns:
            Liste des prédictions générées.
        """
        raise NotImplementedError

    async def _step_select_bets(
        self, predictions: list[Any], stats: PipelineRunStats
    ) -> list[Any]:
        """
        Étape 4 : Sélection des value bets.

        Applique la démarginisation sur les cotes bookmakers.
        Calcule l'EV pour chaque prédiction.
        Filtre selon EV_THRESHOLD, MIN_ODDS, MAX_ODDS.
        Calcule le Kelly Criterion.
        Sélectionne les MAX_BETS_PER_DAY meilleurs paris triés par EV décroissant.

        Args:
            predictions: Liste des prédictions générées à l'étape 3.
            stats: Objet stats du run courant.

        Returns:
            Liste des value bets sélectionnés (max MAX_BETS_PER_DAY).
        """
        raise NotImplementedError

    async def _step_send_coupon(
        self, bets: list[Any], stats: PipelineRunStats
    ) -> None:
        """
        Étape 5 : Envoi du coupon via WhatsApp (avec fallback Telegram).

        Formate le coupon via CouponFormatter.
        Tente l'envoi WhatsApp pour chaque destinataire configuré.
        Si WhatsApp échoue entièrement, bascule sur Telegram.
        Sauvegarde chaque envoi dans la table `alerts`.

        Args:
            bets: Liste des value bets sélectionnés.
            stats: Objet stats du run courant (stats.alerts_sent mis à jour).
        """
        raise NotImplementedError

    async def _save_run_stats(self, stats: PipelineRunStats) -> None:
        """
        Sauvegarde les statistiques du run en base de données (table pipeline_runs).

        Args:
            stats: Statistiques complètes du run terminé.
        """
        raise NotImplementedError

    async def _notify_admin_on_failure(self, stats: PipelineRunStats) -> None:
        """
        Envoie une notification à l'administrateur en cas d'échec critique.

        Utilise Telegram (plus fiable que WhatsApp pour les alertes système).

        Args:
            stats: Statistiques du run avec les informations d'erreur.
        """
        raise NotImplementedError

    def run(self) -> None:
        """
        Lance le scheduler APScheduler avec tous les jobs configurés.

        Jobs configurés :
        - job_daily_pipeline  : tous les jours à settings.DAILY_PIPELINE_HOUR:DAILY_PIPELINE_MINUTE UTC
        - job_hourly_odds     : toutes les settings.ODDS_FETCH_INTERVAL_MINUTES minutes
        - job_live_odds       : toutes les settings.ODDS_FETCH_LIVE_INTERVAL_MINUTES minutes (matchs J0)
        - job_weekly_report   : chaque lundi à 09h00 UTC

        Gère les signaux SIGTERM et SIGINT pour un arrêt propre.
        """
        raise NotImplementedError


def main() -> None:
    """
    Point d'entrée CLI du pipeline.

    Arguments :
        --run-once : Exécute le pipeline une seule fois et s'arrête.
        --dry-run  : N'envoie pas de messages WhatsApp/Telegram.
    """
    parser = argparse.ArgumentParser(description="Apex Bot V2 — Pipeline de prédiction sportive")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Exécuter le pipeline une seule fois sans démarrer le scheduler.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne pas envoyer de messages WhatsApp/Telegram (mode test).",
    )
    args = parser.parse_args()

    pipeline = Pipeline(dry_run=args.dry_run)

    if args.run_once:
        stats = asyncio.run(pipeline.run_daily())
        sys.exit(0 if stats.status in (PipelineStatus.SUCCESS, PipelineStatus.PARTIAL_FAILURE) else 1)
    else:
        pipeline.run()


if __name__ == "__main__":
    main()
