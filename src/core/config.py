"""
Configuration centrale du projet via Pydantic Settings.

Charge et valide toutes les variables d'environnement au démarrage.
Un singleton `settings` est exporté et doit être importé partout
plutôt que de lire os.environ directement.

Usage:
    from src.core.config import settings
    api_key = settings.ODDS_API_KEY
"""

from __future__ import annotations

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Toutes les variables de configuration du projet.

    Les valeurs sont chargées depuis le fichier .env (ou les variables
    d'environnement système) dans cet ordre de priorité :
    1. Variables d'environnement système
    2. Fichier .env à la racine du projet
    3. Valeurs par défaut définies ici

    Toutes les variables sans valeur par défaut sont obligatoires.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ─── Environnement ────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    """Mode d'exécution : 'development' ou 'production'."""

    LOG_LEVEL: str = "INFO"
    """Niveau de log : DEBUG, INFO, WARNING, ERROR."""

    # ─── Base de données ──────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./data/apex_bot.db"
    """URL de connexion SQLAlchemy. SQLite en Phase 1, PostgreSQL en Phase 3."""

    # ─── The Odds API ─────────────────────────────────────────────────────────
    ODDS_API_KEY: str
    """Clé API The Odds API (the-odds-api.com)."""

    ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"
    """URL de base de The Odds API v4."""

    # ─── API-Football ─────────────────────────────────────────────────────────
    FOOTBALL_API_KEY: str
    """Clé RapidAPI pour api-football (v3.football.api-sports.io)."""

    FOOTBALL_API_BASE_URL: str = "https://v3.football.api-sports.io"
    """URL de base de API-Football."""

    FOOTBALL_API_HOST: str = "v3.football.api-sports.io"
    """Header X-RapidAPI-Host requis par RapidAPI."""

    # ─── BallDontLie (Phase 2) ────────────────────────────────────────────────
    BALLDONTLIE_API_KEY: str = ""
    """Clé API BallDontLie pour les données NBA (optionnel en Phase 1)."""

    # ─── WhatsApp Meta Cloud API ──────────────────────────────────────────────
    WHATSAPP_ACCESS_TOKEN: str
    """Token d'accès Meta (temporaire 24h ou permanent via utilisateur système)."""

    WHATSAPP_PHONE_NUMBER_ID: str
    """ID numérique du numéro de téléphone WhatsApp Business."""

    WHATSAPP_BUSINESS_ACCOUNT_ID: str
    """ID du compte WhatsApp Business Account (WABA)."""

    WHATSAPP_API_VERSION: str = "v19.0"
    """Version de l'API Meta Graph à utiliser."""

    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = ""
    """Token de vérification pour le webhook Meta (optionnel si pas de webhook)."""

    WHATSAPP_RECIPIENTS: str = ""
    """Numéros destinataires séparés par virgule (format: +33612345678,+33698765432)."""

    # ─── Telegram (fallback) ──────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    """Token du bot Telegram obtenu via @BotFather."""

    TELEGRAM_CHAT_IDS: str = ""
    """IDs des chats/groupes Telegram séparés par virgule."""

    # ─── Paramètres métier — Sélection ───────────────────────────────────────
    EV_THRESHOLD: float = 0.05
    """Seuil d'expected value minimum pour sélectionner un pari (0.05 = +5%)."""

    KELLY_FRACTION: float = 0.25
    """Fraction du Kelly Criterion appliquée (0.25 = quart-Kelly, plus conservateur)."""

    MIN_ODDS: float = 1.50
    """Cote décimale minimum pour qu'un pari soit sélectionnable."""

    MAX_ODDS: float = 5.00
    """Cote décimale maximum pour qu'un pari soit sélectionnable."""

    MAX_BETS_PER_DAY: int = 5
    """Nombre maximum de paris inclus dans le coupon quotidien."""

    BANKROLL_UNITS: float = 100.0
    """Taille de la bankroll en unités (référence pour le calcul Kelly)."""

    # ─── Sports & Ligues ──────────────────────────────────────────────────────
    SPORTS: str = "football"
    """Sports actifs séparés par virgule."""

    FOOTBALL_LEAGUES: str = (
        "soccer_epl,soccer_spain_la_liga,soccer_germany_bundesliga,"
        "soccer_italy_serie_a,soccer_france_ligue_one"
    )
    """Clés The Odds API des ligues football à couvrir."""

    # ─── Scheduler ────────────────────────────────────────────────────────────
    DAILY_PIPELINE_HOUR: int = 6
    """Heure UTC du pipeline quotidien (0-23)."""

    DAILY_PIPELINE_MINUTE: int = 0
    """Minute du pipeline quotidien (0-59)."""

    ODDS_FETCH_INTERVAL_MINUTES: int = 60
    """Intervalle de fetch des cotes pour les matchs futurs (en minutes)."""

    ODDS_FETCH_LIVE_INTERVAL_MINUTES: int = 15
    """Intervalle de fetch des cotes pour les matchs du jour (en minutes)."""

    # ─── Modèle Dixon-Coles ───────────────────────────────────────────────────
    DIXON_COLES_XI: float = 0.0018
    """Paramètre de décroissance temporelle ξ (xi). Plus élevé = plus de poids aux matchs récents."""

    DIXON_COLES_SEASONS: int = 5
    """Nombre de saisons historiques utilisées pour calibrer le modèle."""

    # ─── Alertes système ──────────────────────────────────────────────────────
    ADMIN_WHATSAPP: str = ""
    """Numéro WhatsApp de l'administrateur pour les alertes système."""

    ADMIN_TELEGRAM_CHAT_ID: str = ""
    """Chat ID Telegram de l'administrateur pour les alertes système."""

    # ─── Properties dérivées ─────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        """Retourne True si l'environnement est 'production'."""
        raise NotImplementedError

    @property
    def whatsapp_recipients_list(self) -> list[str]:
        """Parse WHATSAPP_RECIPIENTS en liste de numéros nettoyés."""
        raise NotImplementedError

    @property
    def telegram_chat_ids_list(self) -> list[str]:
        """Parse TELEGRAM_CHAT_IDS en liste d'IDs."""
        raise NotImplementedError

    @property
    def active_sports_list(self) -> list[str]:
        """Parse SPORTS en liste de sports actifs."""
        raise NotImplementedError

    @property
    def football_leagues_list(self) -> list[str]:
        """Parse FOOTBALL_LEAGUES en liste de clés de ligues."""
        raise NotImplementedError

    @property
    def whatsapp_base_url(self) -> str:
        """Retourne l'URL de base de l'API Meta Graph pour ce numéro."""
        raise NotImplementedError

    # ─── Validateurs ─────────────────────────────────────────────────────────

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Valide que l'environnement est 'development' ou 'production'."""
        raise NotImplementedError

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Valide que le niveau de log est valide."""
        raise NotImplementedError

    @field_validator("EV_THRESHOLD")
    @classmethod
    def validate_ev_threshold(cls, v: float) -> float:
        """Valide que EV_THRESHOLD est positif et raisonnable (< 50%)."""
        raise NotImplementedError

    @field_validator("KELLY_FRACTION")
    @classmethod
    def validate_kelly_fraction(cls, v: float) -> float:
        """Valide que KELLY_FRACTION est dans ]0, 1]."""
        raise NotImplementedError

    @model_validator(mode="after")
    def validate_odds_range(self) -> "Settings":
        """Valide que MIN_ODDS < MAX_ODDS."""
        raise NotImplementedError


# Singleton exporté — importer cet objet dans tous les modules
settings = Settings()  # type: ignore[call-arg]
