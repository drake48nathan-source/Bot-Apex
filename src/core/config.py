"""
Configuration centrale du projet via Pydantic Settings.

Charge et valide toutes les variables d'environnement au démarrage.
Un singleton `settings` est exporté et importé partout dans le projet.

Usage:
    from src.core.config import settings
    api_key = settings.ODDS_API_KEY
    if settings.DEMO_MODE:
        return DEMO_DATA
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Toutes les variables de configuration du projet.

    Priorité : variables système > fichier .env > valeurs par défaut.
    Les champs sans valeur par défaut sont obligatoires (sauf si DEMO_MODE=true).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ─── Environnement ────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEMO_MODE: bool = False
    TIMEZONE: str = "Europe/Paris"

    # ─── Base de données ──────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./botv2.db"

    # ─── The Odds API ─────────────────────────────────────────────────────────
    ODDS_API_KEY: str = ""
    ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"

    # ─── API-Football ─────────────────────────────────────────────────────────
    API_FOOTBALL_KEY: str = ""
    API_FOOTBALL_BASE_URL: str = "https://v3.football.api-sports.io"
    API_FOOTBALL_HOST: str = "v3.football.api-sports.io"

    # ─── BallDontLie (Phase 2) ────────────────────────────────────────────────
    BALLDONTLIE_API_KEY: str = ""

    # ─── WhatsApp Meta Cloud API ──────────────────────────────────────────────
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_RECIPIENT_NUMBER: str = ""
    WHATSAPP_API_VERSION: str = "v19.0"

    # ─── Telegram (fallback) ──────────────────────────────────────────────────
    TELEGRAM_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ─── Scheduler ────────────────────────────────────────────────────────────
    BOT_SEND_HOUR: int = 9
    BOT_SEND_MINUTE: int = 0
    ODDS_FETCH_INTERVAL_MINUTES: int = 60
    ODDS_FETCH_LIVE_INTERVAL_MINUTES: int = 15

    # ─── Paramètres métier ────────────────────────────────────────────────────
    EV_THRESHOLD: float = 0.05
    KELLY_FRACTION: float = 0.25
    MIN_ODDS: float = 1.50
    MAX_ODDS: float = 5.00
    MAX_BETS_PER_DAY: int = 5
    BANKROLL_UNITS: float = 100.0

    # ─── Ligues ───────────────────────────────────────────────────────────────
    FOOTBALL_LEAGUES: str = (
        "soccer_epl,soccer_spain_la_liga,soccer_germany_bundesliga,"
        "soccer_italy_serie_a,soccer_france_ligue_one"
    )

    # ─── Modèle Dixon-Coles ───────────────────────────────────────────────────
    DIXON_COLES_XI: float = 0.0018
    DIXON_COLES_SEASONS: int = 5

    # ─── Alertes admin ────────────────────────────────────────────────────────
    ADMIN_TELEGRAM_CHAT_ID: str = ""

    # ─── Properties dérivées ─────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def whatsapp_enabled(self) -> bool:
        return bool(self.WHATSAPP_TOKEN and self.WHATSAPP_PHONE_NUMBER_ID and not self.DEMO_MODE)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.TELEGRAM_TOKEN and self.TELEGRAM_CHAT_ID)

    @property
    def football_leagues_list(self) -> list[str]:
        return [l.strip() for l in self.FOOTBALL_LEAGUES.split(",") if l.strip()]

    @property
    def whatsapp_base_url(self) -> str:
        return (
            f"https://graph.facebook.com/{self.WHATSAPP_API_VERSION}"
            f"/{self.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )

    # ─── Validateurs ─────────────────────────────────────────────────────────

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}, got '{v}'")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
        return v

    @field_validator("EV_THRESHOLD")
    @classmethod
    def validate_ev_threshold(cls, v: float) -> float:
        if not (0 < v < 0.5):
            raise ValueError(f"EV_THRESHOLD must be in ]0, 0.5[, got {v}")
        return v

    @field_validator("KELLY_FRACTION")
    @classmethod
    def validate_kelly_fraction(cls, v: float) -> float:
        if not (0 < v <= 1.0):
            raise ValueError(f"KELLY_FRACTION must be in ]0, 1], got {v}")
        return v

    @model_validator(mode="after")
    def validate_odds_range(self) -> "Settings":
        if self.MIN_ODDS >= self.MAX_ODDS:
            raise ValueError(
                f"MIN_ODDS ({self.MIN_ODDS}) must be < MAX_ODDS ({self.MAX_ODDS})"
            )
        return self

    @model_validator(mode="after")
    def warn_if_keys_missing(self) -> "Settings":
        """En mode production, toutes les clés API sont requises."""
        if self.ENVIRONMENT == "production" and not self.DEMO_MODE:
            missing = []
            if not self.ODDS_API_KEY:
                missing.append("ODDS_API_KEY")
            if not self.API_FOOTBALL_KEY:
                missing.append("API_FOOTBALL_KEY")
            if not self.WHATSAPP_TOKEN:
                missing.append("WHATSAPP_TOKEN")
            if missing:
                raise ValueError(
                    f"Missing required API keys in production: {', '.join(missing)}"
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retourne le singleton Settings (mis en cache après le premier appel)."""
    return Settings()


# Singleton exporté
settings = get_settings()
