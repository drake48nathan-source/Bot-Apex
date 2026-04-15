"""
Configuration Alembic pour les migrations SQLAlchemy.

Ce fichier est exécuté par Alembic lors des commandes upgrade/downgrade/revision.
Il configure la connexion à la base de données depuis la variable DATABASE_URL
et importe tous les modèles pour l'autogénération des migrations.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ajouter la racine du projet au PYTHONPATH pour les imports src.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import de tous les modèles (requis pour autogenerate)
from src.core.database import Base  # noqa: E402
import src.data.models  # noqa: E402, F401  # Force l'import de tous les modèles

# Configuration Alembic
config = context.config

# Configurer les loggers depuis alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Surcharger sqlalchemy.url avec DATABASE_URL si défini
database_url = os.getenv("DATABASE_URL", "sqlite:///./botv2.db")
config.set_main_option("sqlalchemy.url", database_url)

# Métadonnées pour l'autogénération
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Mode offline : génère le SQL sans connexion active.
    Utilisé avec `alembic upgrade --sql`.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Mode online : connexion active à la base de données.
    Mode par défaut pour `alembic upgrade head`.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
