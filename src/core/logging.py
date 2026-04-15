"""
Configuration du logging structuré avec structlog.

- Développement : logs colorés et lisibles (ConsoleRenderer)
- Production    : logs JSON sur stdout (JSONRenderer pour Railway/VPS)

Usage:
    from src.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Fetching odds", sport="football", n_matches=12)
    logger.error("API failed", error=str(e), endpoint="/odds/")
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


_configured = False


def configure_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """
    Configure structlog et le logging standard Python.

    Doit être appelé une seule fois au démarrage, avant tout get_logger().
    Idempotent : les appels suivants sont ignorés silencieusement.
    """
    global _configured
    if _configured:
        return

    level = getattr(logging, log_level.upper(), logging.INFO)

    # ─── Processeurs communs ──────────────────────────────────────────────────
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    if environment == "production":
        # JSON sur stdout pour Railway / VPS
        processors = shared_processors + [
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Couleurs dans le terminal
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # ─── Logging standard Python (SQLAlchemy, APScheduler, etc.) ─────────────
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
    # Réduire le bruit des librairies tierces
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Retourne un logger structlog lié au nom du module.

    Usage recommandé (en haut de chaque fichier) :
        logger = get_logger(__name__)

    Le logger supporte le contexte :
        bound = logger.bind(pipeline_run_id="abc123")
        bound.info("Step done", duration_s=1.2)
    """
    return structlog.get_logger(name)  # type: ignore[return-value]


def add_context(**kwargs: Any) -> None:
    """
    Ajoute des variables de contexte thread-local à tous les logs suivants.

    Example:
        add_context(pipeline_run_id="run-001", sport="football")
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Vide le contexte thread-local. À appeler en fin de pipeline run."""
    structlog.contextvars.clear_contextvars()


# Auto-configure au chargement du module avec les settings courants
def _auto_configure() -> None:
    try:
        from src.core.config import settings
        configure_logging(
            log_level=settings.LOG_LEVEL,
            environment=settings.ENVIRONMENT,
        )
    except Exception:
        # Fallback si les settings ne sont pas encore chargés
        configure_logging()


_auto_configure()
