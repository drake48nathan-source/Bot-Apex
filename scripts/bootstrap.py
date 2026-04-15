"""
Script d'initialisation du projet Apex Bot V2.

À exécuter une seule fois après le premier déploiement :
    python scripts/bootstrap.py

Actions :
1. Crée la base de données et applique les migrations (alembic upgrade head)
2. Vérifie que toutes les variables d'environnement requises sont présentes
3. Télécharge les données historiques des matchs (5 dernières saisons)
4. Calibre le modèle Dixon-Coles pour chaque ligue configurée
5. Sauvegarde les paramètres calibrés en base de données
6. Envoie un message de test WhatsApp pour valider la configuration
7. Affiche un rapport de validation

Usage:
    python scripts/bootstrap.py
    python scripts/bootstrap.py --skip-calibration  # Si données déjà présentes
    python scripts/bootstrap.py --skip-whatsapp-test  # Sans test WhatsApp
    python scripts/bootstrap.py --dry-run  # Validation seulement
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any


def main() -> None:
    """Point d'entrée du script bootstrap."""
    parser = argparse.ArgumentParser(description="Bootstrap Apex Bot V2")
    parser.add_argument("--skip-calibration", action="store_true", help="Passer la calibration du modèle")
    parser.add_argument("--skip-whatsapp-test", action="store_true", help="Passer le test WhatsApp")
    parser.add_argument("--dry-run", action="store_true", help="Validation uniquement, sans modifications")
    args = parser.parse_args()

    asyncio.run(_bootstrap(args))


async def _bootstrap(args: Any) -> None:
    """
    Exécute les étapes de bootstrap dans l'ordre.

    Chaque étape affiche son statut (OK / ERREUR) avant de passer à la suivante.
    En cas d'erreur critique, le bootstrap s'arrête avec un message explicatif.
    """
    raise NotImplementedError


async def _check_env_vars() -> bool:
    """
    Vérifie que toutes les variables d'environnement requises sont présentes.

    Distingue les variables obligatoires (API keys) des optionnelles (Telegram fallback).

    Returns:
        True si toutes les variables obligatoires sont présentes.
    """
    raise NotImplementedError


async def _download_historical_data(leagues: list[str], seasons: int = 5) -> dict:
    """
    Télécharge les données historiques depuis API-Football.

    Pour chaque ligue et chaque saison, télécharge tous les matchs terminés
    avec scores exacts. En mode DEMO_MODE, utilise des données synthétiques.

    Args:
        leagues: Liste des IDs de ligues API-Football.
        seasons: Nombre de saisons à télécharger (comptées depuis l'année courante).

    Returns:
        Dict {league_id: [matches]} avec les données historiques.
    """
    raise NotImplementedError


async def _calibrate_model(historical_data: dict) -> dict:
    """
    Calibre le modèle Dixon-Coles pour chaque ligue.

    Args:
        historical_data: Dict {league_id: [matches]} issu de _download_historical_data().

    Returns:
        Dict {league_id: ModelFitResult} avec les paramètres calibrés.
    """
    raise NotImplementedError


async def _test_whatsapp() -> bool:
    """
    Envoie un message de test WhatsApp pour valider la configuration.

    Returns:
        True si le message a été accepté par l'API Meta.
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()
