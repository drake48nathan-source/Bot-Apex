"""
Configuration de la base de données SQLAlchemy.

Expose :
- `Base`         : classe de base pour tous les modèles ORM
- `get_db()`     : context manager pour obtenir une session
- `init_db()`    : crée les tables (développement seulement)
- `engine`       : moteur SQLAlchemy global

Usage:
    from src.core.database import get_db
    with get_db() as db:
        db.add(match)
        db.commit()
"""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, event, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.config import settings


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy du projet."""
    pass


def create_db_engine(database_url: str) -> Engine:
    """
    Crée et configure le moteur SQLAlchemy.

    Pour SQLite : active WAL mode et foreign keys.
    Pour PostgreSQL : configure le pool de connexions.
    """
    is_sqlite = database_url.startswith("sqlite")

    connect_args: dict = {}
    if is_sqlite:
        connect_args["check_same_thread"] = False
        # Crée le répertoire si nécessaire
        if "///" in database_url:
            db_path = database_url.split("///")[1]
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

    engine = create_engine(
        database_url,
        connect_args=connect_args,
        echo=settings.LOG_LEVEL == "DEBUG",
    )

    if is_sqlite:
        _configure_sqlite(engine)

    return engine


def _configure_sqlite(engine: Engine) -> None:
    """Active les pragmas SQLite pour la performance et l'intégrité."""

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn: object, connection_record: object) -> None:  # type: ignore[misc]
        cursor = dbapi_conn.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64 MB cache
        cursor.close()


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Crée la factory de sessions SQLAlchemy."""
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager pour obtenir une session de base de données.

    Rollback automatique en cas d'exception, fermeture garantie.

    Usage:
        with get_db() as db:
            db.add(obj)
            db.commit()
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """
    Crée toutes les tables définies dans les modèles SQLAlchemy.

    À utiliser uniquement en développement ou dans les tests.
    En production : utiliser `alembic upgrade head`.
    """
    # Import explicite de tous les modèles pour que SQLAlchemy les découvre
    import src.data.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def drop_all_tables() -> None:
    """Supprime toutes les tables. À utiliser UNIQUEMENT dans les tests."""
    Base.metadata.drop_all(bind=engine)


# ─── Initialisation globale ────────────────────────────────────────────────────
engine: Engine = create_db_engine(settings.DATABASE_URL)
SessionLocal: sessionmaker[Session] = create_session_factory(engine)
