"""
Configuration de la base de données SQLAlchemy.

Expose :
- `engine` : le moteur de connexion (SQLite en Phase 1)
- `SessionLocal` : factory de sessions SQLAlchemy
- `Base` : classe de base pour tous les modèles ORM
- `get_db()` : context manager pour obtenir une session dans un job

La base de données est créée automatiquement au premier accès si elle n'existe pas.
En Phase 3, remplacer DATABASE_URL par une URL PostgreSQL sans changer ce fichier.

Usage:
    from src.core.database import get_db
    with get_db() as db:
        matches = db.query(Match).all()
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """
    Classe de base pour tous les modèles SQLAlchemy du projet.

    Tous les modèles dans src/data/models/ doivent hériter de cette classe.
    Alembic utilise également cette Base pour autogénérer les migrations.
    """

    pass


def create_db_engine(database_url: str) -> Engine:
    """
    Crée et configure le moteur SQLAlchemy.

    Pour SQLite : active le mode WAL (Write-Ahead Logging) pour de meilleures
    performances en lecture concurrente, et active les foreign keys (désactivées
    par défaut dans SQLite).

    Pour PostgreSQL : configure le pool de connexions (pool_size, max_overflow).

    Args:
        database_url: URL de connexion SQLAlchemy (ex: "sqlite:///./data/apex_bot.db")

    Returns:
        Engine SQLAlchemy configuré et prêt à l'emploi.
    """
    raise NotImplementedError


def _configure_sqlite(engine: Engine) -> None:
    """
    Configure les pragmas SQLite nécessaires à la performance et à l'intégrité.

    Appelé automatiquement lors de la création d'une connexion SQLite.
    Active : foreign_keys, WAL journal mode, synchronous=NORMAL.

    Args:
        engine: Engine SQLite à configurer.
    """
    raise NotImplementedError


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """
    Crée la factory de sessions SQLAlchemy.

    Args:
        engine: Engine SQLAlchemy créé par create_db_engine().

    Returns:
        sessionmaker configuré avec autocommit=False et autoflush=False.
    """
    raise NotImplementedError


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager pour obtenir une session de base de données.

    La session est automatiquement fermée après le bloc with.
    En cas d'exception, la transaction est rollback automatiquement.

    Usage:
        with get_db() as db:
            matches = db.query(Match).filter(Match.status == "scheduled").all()
            db.add(new_match)
            db.commit()

    Yields:
        Session SQLAlchemy active.

    Raises:
        SQLAlchemyError: En cas d'erreur de base de données (reraisée après rollback).
    """
    raise NotImplementedError


def init_db() -> None:
    """
    Crée toutes les tables définies dans les modèles SQLAlchemy.

    À appeler uniquement en développement ou dans les scripts de bootstrap.
    En production, utiliser les migrations Alembic (`alembic upgrade head`).

    Note: Import explicite de tous les modèles nécessaire pour que SQLAlchemy
    les découvre avant d'appeler Base.metadata.create_all().
    """
    raise NotImplementedError


# ─── Initialisation du module ──────────────────────────────────────────────────
# Ces objets sont initialisés au chargement du module et partagés globalement.
# engine et SessionLocal sont créés à partir des settings.
engine: Engine
SessionLocal: sessionmaker[Session]
