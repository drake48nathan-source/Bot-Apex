# APEX BOT V2 — Arborescence complète du projet

```
BotV2/
│
├── src/                               # Code source principal
│   ├── __init__.py
│   │
│   ├── core/                          # Infrastructure transverse (pas de logique métier)
│   │   ├── __init__.py
│   │   ├── config.py                  # Pydantic Settings — toutes les variables d'env
│   │   ├── database.py                # SQLAlchemy engine, SessionLocal, Base declarative
│   │   └── logging.py                 # structlog configuré, get_logger() factory
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   │
│   │   ├── fetchers/                  # Clients HTTP vers APIs externes
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # BaseDataFetcher : cache TTL + circuit breaker + retry (tenacity)
│   │   │   ├── odds.py                # OddsFetcher : The Odds API → cotes tous bookmakers
│   │   │   ├── football.py            # FootballFetcher : API-Football → fixtures, stats, H2H
│   │   │   ├── basketball.py          # BasketballFetcher : BallDontLie → NBA (Phase 2)
│   │   │   └── weather.py             # WeatherFetcher : Open-Meteo → météo stade (Phase 2)
│   │   │
│   │   └── models/                    # Modèles SQLAlchemy (mapping ORM ↔ tables SQL)
│   │       ├── __init__.py            # Exporte tous les modèles (pour Alembic)
│   │       ├── match.py               # Table matches
│   │       ├── odd.py                 # Table odds (cotes bookmakers)
│   │       ├── prediction.py          # Table predictions (output modèle + EV)
│   │       ├── bet.py                 # Table bets (paris trackés + résultats)
│   │       ├── alert.py               # Table alerts (messages envoyés)
│   │       ├── pipeline_run.py        # Table pipeline_runs (audit des exécutions)
│   │       └── model_params.py        # Table model_params (paramètres calibrés sauvegardés)
│   │
│   ├── models/                        # Modèles statistiques de prédiction
│   │   ├── __init__.py
│   │   ├── base.py                    # Classe abstraite BasePredictionModel
│   │   ├── dixon_coles.py             # DixonColesModel : calibration + prédiction football
│   │   ├── elo.py                     # EloModel : basketball et tennis (Phase 2)
│   │   │
│   │   └── markets/                   # Calcul probabilités par marché depuis matrice de scores
│   │       ├── __init__.py
│   │       ├── base_market.py         # Classe abstraite BaseMarket
│   │       ├── result.py              # ResultMarket : 1X2 (Match Result)
│   │       ├── totals.py              # TotalsMarket : Over/Under N.5 buts
│   │       ├── btts.py                # BTTSMarket : Both Teams to Score
│   │       ├── asian_handicap.py      # AsianHandicapMarket : AH -0.5/+0.5/etc.
│   │       └── double_chance.py       # DoubleChanceMarket : 1X, X2, 12
│   │
│   ├── selection/                     # Pipeline de sélection des value bets
│   │   ├── __init__.py
│   │   ├── value_calculator.py        # ValueCalculator : démarginisation + calcul EV
│   │   ├── kelly.py                   # KellyCriterion : calcul mise optimale
│   │   └── selector.py                # ValueBetSelector : filtrage + ranking + sélection finale
│   │
│   ├── messaging/                     # Couche d'envoi des messages
│   │   ├── __init__.py
│   │   ├── base.py                    # Classe abstraite BaseMessenger
│   │   ├── whatsapp.py                # WhatsAppClient : Meta Cloud API
│   │   ├── telegram.py                # TelegramClient : python-telegram-bot (fallback)
│   │   └── formatters.py              # CouponFormatter, AlertFormatter, AnalysisFormatter
│   │
│   └── scheduler/                     # Orchestration temporelle
│       ├── __init__.py
│       ├── jobs.py                    # Définition des jobs APScheduler (fréquence + fonction)
│       └── pipeline.py                # Pipeline : orchestrateur principal, __main__ entry point
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Fixtures pytest : DB mémoire, settings test, mocks HTTP
│   │
│   ├── unit/                          # Tests sans I/O externe (DB en mémoire, HTTP mocké)
│   │   ├── __init__.py
│   │   ├── test_dixon_coles.py        # Tests modèle : fit, predict, calibration
│   │   ├── test_value_calculator.py   # Tests démarginisation power/additive + calcul EV
│   │   ├── test_kelly.py              # Tests Kelly : fraction, validation bornes [0,1]
│   │   ├── test_markets.py            # Tests 5 marchés : probs somment à 1, cas limites
│   │   ├── test_formatters.py         # Tests formatage : longueur, encoding, structure
│   │   └── test_config.py             # Tests Settings : chargement .env, validations
│   │
│   └── integration/                   # Tests avec SQLite en mémoire et HTTP mocké
│       ├── __init__.py
│       ├── test_odds_fetcher.py       # Tests OddsFetcher avec pytest-httpx
│       ├── test_football_fetcher.py   # Tests FootballFetcher avec pytest-httpx
│       ├── test_database.py           # Tests CRUD complets (match, odd, prediction, bet)
│       └── test_pipeline.py           # Tests pipeline end-to-end avec toutes les dépendances mockées
│
├── migrations/                        # Migrations Alembic
│   ├── env.py                         # Config Alembic (pointe vers les modèles SQLAlchemy)
│   ├── script.py.mako                 # Template de migration
│   └── versions/
│       └── 001_initial_schema.py      # Migration initiale : toutes les tables
│
├── scripts/
│   ├── bootstrap.py                   # Setup initial : téléchargement données histo + calibration
│   ├── backtest.py                    # Backtesting sur données historiques avec métriques ROI
│   └── validate_model.py              # Validation du modèle calibré (Brier, log-loss, calibration)
│
├── data/                              # Données locales (gitignorée)
│   └── apex_bot.db                    # Base SQLite (créée automatiquement)
│
├── .env.example                       # Template de toutes les variables d'environnement
├── .env                               # Variables locales (gitignorée)
├── .gitignore                         # Exclusions git
├── .python-version                    # "3.12" (pour pyenv)
├── alembic.ini                        # Configuration Alembic
├── pyproject.toml                     # Dépendances + config black/ruff/mypy/pytest
├── Procfile                           # "worker: python -m src.scheduler.pipeline"
└── README.md                          # Documentation principale
```

---

## Responsabilités des modules (résumé)

| Module | Responsabilité | Dépendances internes |
|--------|---------------|---------------------|
| `core/config.py` | Charger et valider la config | Aucune |
| `core/database.py` | Fournir l'accès à la DB | `core/config` |
| `core/logging.py` | Logging structuré | `core/config` |
| `data/fetchers/base.py` | Cache + retry + circuit breaker | `core/config`, `core/logging` |
| `data/fetchers/odds.py` | Cotes bookmakers | `fetchers/base`, `data/models` |
| `data/fetchers/football.py` | Stats football | `fetchers/base`, `data/models` |
| `data/models/*.py` | Schéma DB | `core/database` |
| `models/dixon_coles.py` | Prédiction scores | `data/models` (lecture params) |
| `models/markets/*.py` | Proba par marché | `models/dixon_coles` |
| `selection/value_calculator.py` | Démarginisation + EV | Aucune (pur calcul) |
| `selection/kelly.py` | Mise optimale | Aucune (pur calcul) |
| `selection/selector.py` | Filtrage + ranking | `value_calculator`, `kelly`, `core/config` |
| `messaging/whatsapp.py` | Envoi WhatsApp | `core/config`, `core/logging` |
| `messaging/telegram.py` | Envoi Telegram | `core/config`, `core/logging` |
| `messaging/formatters.py` | Formatage messages | `data/models` |
| `scheduler/jobs.py` | Définition jobs | `scheduler/pipeline` |
| `scheduler/pipeline.py` | Orchestration | Tous les modules ci-dessus |

---

## Conventions de nommage

- **Fichiers :** snake_case (ex: `dixon_coles.py`)
- **Classes :** PascalCase (ex: `DixonColesModel`, `OddsFetcher`)
- **Fonctions et méthodes :** snake_case (ex: `fetch_upcoming_events`)
- **Constantes :** UPPER_SNAKE_CASE (ex: `DEFAULT_TTL_SECONDS`)
- **Variables d'environnement :** UPPER_SNAKE_CASE préfixé par domaine (ex: `WHATSAPP_ACCESS_TOKEN`)
- **Tables de base de données :** snake_case pluriel (ex: `matches`, `pipeline_runs`)
