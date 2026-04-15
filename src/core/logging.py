"""
Configuration du logging structuré avec structlog.

En mode développement : logs colorés et lisibles dans le terminal.
En mode production (Railway/VPS) : logs JSON sur stdout, collectés par la plateforme.

Chaque log inclut automatiquement :
- timestamp ISO 8601
- niveau (INFO, WARNING, ERROR, etc.)
- nom du module appelant
- contexte courant (pipeline_run_id, sport, league si définis)

Usage:
    from src.core.logging import get_logger
    logger = get_logger(__name__)

    logger.info("Fetching odds", sport="football", league="EPL", n_matches=12)
    logger.error("API call failed", error=str(e), endpoint="/sports/soccer_epl/odds/")
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """
    Configure structlog et le logging standard Python.

    Doit être appelé une seule fois au démarrage de l'application,
    avant tout import de `get_logger()`.

    En développement : ConsoleRenderer avec couleurs (rich).
    En production : JSONRenderer pour l'ingestion par les plateformes de logs.

    Args:
        log_level: Niveau de log ("DEBUG", "INFO", "WARNING", "ERROR").
        environment: Environnement d'exécution ("development" ou "production").
    """
    raise NotImplementedError


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Retourne un logger structlog lié au nom du module appelant.

    Usage recommandé (en haut de chaque fichier) :
        logger = get_logger(__name__)

    Le logger supporte le contexte via bind() :
        logger = logger.bind(pipeline_run_id="abc123", sport="football")
        logger.info("Prédiction générée", match="Arsenal vs Chelsea", ev=0.092)

    Args:
        name: Nom du module (utiliser __name__ systématiquement).

    Returns:
        Logger structlog configuré avec le nom du module.
    """
    raise NotImplementedError


def add_context(**kwargs: Any) -> None:
    """
    Ajoute des variables de contexte au logger courant (thread-local).

    Utile pour ajouter le pipeline_run_id en début de run et l'avoir
    automatiquement dans tous les logs suivants de ce thread.

    Args:
        **kwargs: Paires clé-valeur à ajouter au contexte de log.

    Example:
        add_context(pipeline_run_id="run-2024-12-15-001", sport="football")
        # Tous les logs suivants incluront ces champs automatiquement
    """
    raise NotImplementedError


def clear_context() -> None:
    """
    Vide le contexte thread-local du logger.
    À appeler en fin de pipeline run pour éviter la fuite de contexte.
    """
    raise NotImplementedError
