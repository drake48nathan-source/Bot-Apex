# APEX BOT V2 — Architecture technique détaillée

## 1. Arborescence complète du projet

```
BotV2/
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                          # Infrastructure transverse
│   │   ├── __init__.py
│   │   ├── config.py                  # Settings Pydantic (chargement .env)
│   │   ├── database.py                # SQLAlchemy engine + SessionLocal + Base
│   │   └── logging.py                 # structlog configuré (JSON prod, couleurs dev)
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   │
│   │   ├── fetchers/                  # Clients HTTP vers APIs externes
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # BaseDataFetcher : cache TTL + circuit breaker + retry
│   │   │   ├── odds.py                # The Odds API → cotes bookmakers
│   │   │   ├── football.py            # API-Football → stats, fixtures, H2H
│   │   │   ├── basketball.py          # BallDontLie → NBA stats (Phase 2)
│   │   │   └── weather.py             # Open-Meteo → météo stade (Phase 2)
│   │   │
│   │   └── models/                    # Modèles SQLAlchemy (ORM)
│   │       ├── __init__.py
│   │       ├── match.py               # Table matches
│   │       ├── odd.py                 # Table odds (cotes bookmakers)
│   │       ├── prediction.py          # Table predictions (résultat du modèle)
│   │       ├── bet.py                 # Table bets (paris joués + résultats)
│   │       ├── alert.py               # Table alerts (messages envoyés)
│   │       ├── pipeline_run.py        # Table pipeline_runs (logs d'exécution)
│   │       └── model_params.py        # Table model_params (paramètres calibrés)
│   │
│   ├── models/                        # Modèles de prédiction statistiques
│   │   ├── __init__.py
│   │   ├── base.py                    # Classe abstraite BaseModel
│   │   ├── dixon_coles.py             # Modèle Dixon-Coles (football)
│   │   ├── elo.py                     # Modèle Elo (basketball, tennis - Phase 2)
│   │   │
│   │   └── markets/                   # Calcul des probabilités par marché
│   │       ├── __init__.py
│   │       ├── base_market.py         # Classe abstraite BaseMarket
│   │       ├── result.py              # Marché 1X2 (Match Result)
│   │       ├── totals.py              # Marché Over/Under X.5 buts
│   │       ├── btts.py                # Both Teams to Score
│   │       ├── asian_handicap.py      # Asian Handicap -0.5/+0.5/etc.
│   │       └── double_chance.py       # Double Chance (1X, X2, 12)
│   │
│   ├── selection/
│   │   ├── __init__.py
│   │   ├── value_calculator.py        # Démarginisation + calcul EV
│   │   ├── kelly.py                   # Kelly Criterion (fraction)
│   │   └── selector.py                # ValueBetSelector (filtrage + ranking)
│   │
│   ├── messaging/
│   │   ├── __init__.py
│   │   ├── base.py                    # Classe abstraite BaseMessenger
│   │   ├── whatsapp.py                # Meta Cloud API (canal principal)
│   │   ├── telegram.py                # python-telegram-bot (canal fallback)
│   │   └── formatters.py              # Formatage des messages (coupon, alerte, analyse)
│   │
│   └── scheduler/
│       ├── __init__.py
│       ├── jobs.py                    # Définition des jobs APScheduler
│       └── pipeline.py                # Orchestrateur principal du pipeline
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Fixtures partagées (DB en mémoire, mocks)
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_dixon_coles.py        # Tests modèle statistique
│   │   ├── test_value_calculator.py   # Tests démarginisation + EV
│   │   ├── test_kelly.py              # Tests Kelly Criterion
│   │   ├── test_markets.py            # Tests des 5 marchés
│   │   ├── test_formatters.py         # Tests formatage messages
│   │   └── test_config.py             # Tests chargement config
│   │
│   └── integration/
│       ├── __init__.py
│       ├── test_odds_fetcher.py       # Tests avec mock HTTP
│       ├── test_football_fetcher.py   # Tests avec mock HTTP
│       ├── test_database.py           # Tests CRUD en DB SQLite mémoire
│       └── test_pipeline.py           # Tests pipeline end-to-end mocké
│
├── migrations/                        # Alembic
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
│
├── scripts/
│   ├── bootstrap.py                   # Téléchargement données historiques + calibration
│   ├── backtest.py                    # Backtesting sur données historiques
│   └── validate_model.py              # Validation métriques du modèle
│
├── .env.example                       # Template variables d'environnement
├── .gitignore
├── .python-version                    # "3.12"
├── alembic.ini                        # Configuration Alembic
├── pyproject.toml                     # Dépendances + config outils
├── Procfile                           # "worker: python -m src.scheduler.pipeline"
└── README.md
```

---

---

## 1b. Déploiement Railway

**Projet :** https://railway.com/project/e97dc9a2-a986-4f2d-a3e1-0cb9fc3c2b48/service/4bc6caed-a2d4-450f-be04-638dff0a6219

**GitHub :** https://github.com/drake48nathan-source/Bot-Apex-  
→ Déploiement automatique à chaque push sur `main`

**Fichiers requis pour Railway :**
- `Procfile` : `worker: python -m src.scheduler.pipeline`
- `.python-version` : `3.12`
- `requirements.txt` : dépendances détectées par Railway
- `pyproject.toml` : config des outils et dépendances complètes

**Variables d'environnement à configurer dans Railway :**  
Aller dans le service → Settings → Variables et ajouter toutes les variables de `.env.example`.

---

## 2. Description de chaque module

### `src/core/`
Infrastructure partagée par tous les modules. Ne contient aucune logique métier.

- **`config.py`** : Charge et valide toutes les variables d'environnement via `pydantic-settings`. Expose un singleton `settings` importé partout.
- **`database.py`** : Configure l'engine SQLAlchemy (SQLite en Phase 1, PostgreSQL en Phase 3). Expose `get_db()` (context manager) et `Base` (classe de base des modèles).
- **`logging.py`** : Configure `structlog` avec processeurs adaptés à l'environnement (JSON en production, format coloré en développement). Expose `get_logger(__name__)`.

### `src/data/fetchers/`
Couche d'accès aux APIs externes. Chaque fetcher hérite de `BaseDataFetcher` qui gère :
- Cache TTL en mémoire (évite les appels redondants)
- Retry avec backoff exponentiel (tenacity)
- Circuit breaker (arrête les appels si l'API est en panne)
- Logging automatique de chaque appel (URL, durée, statut)

### `src/data/models/`
Modèles SQLAlchemy représentant le schéma de la base de données. Aucune logique métier ici, uniquement la définition des tables et des relations.

### `src/models/`
Modèles statistiques de prédiction. Cette couche reçoit des données brutes (historique de matchs) et produit des probabilités. Elle ne connaît pas la base de données.

### `src/selection/`
Transforme les probabilités du modèle en décisions de paris :
1. `value_calculator.py` : démarginise les cotes des bookmakers, calcule l'EV
2. `kelly.py` : calcule la mise optimale selon le Kelly Criterion
3. `selector.py` : filtre et classe les value bets selon des critères configurables

### `src/messaging/`
Couche de diffusion des messages. Indépendante du reste (peut être testée isolément).

### `src/scheduler/`
Orchestration temporelle. `jobs.py` définit la fréquence, `pipeline.py` l'ordre d'exécution.

---

## 3. Flux de données complet

```
1. COLLECTE (toutes les heures / 15 min pour J0)
   OddsFetcher.fetch_upcoming_events()
   FootballFetcher.fetch_fixtures()
   FootballFetcher.fetch_team_stats()
         │
         ▼
   Sauvegarde en DB : tables matches + odds

2. PRÉDICTION (à 06h00 UTC)
   DixonColesModel.load_params(from_db)
   Pour chaque match du jour :
     score_matrix = model.predict_score_matrix(home, away)
     Pour chaque marché :
       model_prob = MarketModule.compute(score_matrix)
       Sauvegarde en DB : table predictions

3. SÉLECTION
   Pour chaque prédiction :
     fair_odds = ValueCalculator.demargin(bookmaker_odds)
     ev = ValueCalculator.calculate_ev(model_prob, fair_odds)
     Si ev > EV_THRESHOLD :
       stake = Kelly.calculate(model_prob, best_odds)
       → value_bet candidat
   ValueBetSelector.rank_and_filter(candidates)
   → top_bets (liste finale)

4. MESSAGERIE
   formatters.format_daily_coupon(top_bets)
   WhatsAppClient.send_coupon(coupon_text)
   Si WhatsApp échoue :
     TelegramClient.send_coupon(coupon_text)
   Sauvegarde en DB : table alerts

5. LOGGING
   PipelineRun sauvegardé en DB (durée, nb_bets, statut)
   Logs structurés JSON → stdout → collectés par supervisord
```

---

## 4. Schéma de la base de données

### Table `matches`
```
id              INTEGER     PRIMARY KEY AUTOINCREMENT
external_id     TEXT        NOT NULL UNIQUE     -- ID API-Football ou The Odds API
sport           TEXT        NOT NULL            -- "football", "basketball", "tennis"
league          TEXT        NOT NULL            -- "EPL", "NBA", etc.
league_id       INTEGER                         -- ID numérique API-Football
season          TEXT                            -- "2024-25"
home_team       TEXT        NOT NULL
away_team       TEXT        NOT NULL
home_team_id    INTEGER
away_team_id    INTEGER
kickoff_utc     DATETIME    NOT NULL
venue           TEXT
status          TEXT        NOT NULL DEFAULT 'scheduled'
                            -- "scheduled", "in_play", "finished", "cancelled"
home_score      INTEGER
away_score      INTEGER
created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
```

### Table `odds`
```
id              INTEGER     PRIMARY KEY AUTOINCREMENT
match_id        INTEGER     NOT NULL REFERENCES matches(id)
bookmaker       TEXT        NOT NULL            -- "bet365", "unibet", etc.
market          TEXT        NOT NULL            -- "h2h", "totals", "btts", etc.
outcome         TEXT        NOT NULL            -- "home", "draw", "away", "over 2.5", etc.
price           REAL        NOT NULL            -- cote décimale
updated_at      DATETIME    NOT NULL
UNIQUE(match_id, bookmaker, market, outcome)
```

### Table `predictions`
```
id              INTEGER     PRIMARY KEY AUTOINCREMENT
match_id        INTEGER     NOT NULL REFERENCES matches(id)
model_version   TEXT        NOT NULL            -- "dixon_coles_v1.2"
market          TEXT        NOT NULL
outcome         TEXT        NOT NULL
model_prob      REAL        NOT NULL            -- probabilité modèle [0,1]
best_bookmaker  TEXT
best_odds       REAL                            -- meilleure cote disponible
fair_odds       REAL                            -- après démarginisation
ev              REAL                            -- expected value en % (0.05 = +5%)
kelly_fraction  REAL                            -- fraction Kelly recommandée
confidence      TEXT                            -- "low", "medium", "high"
created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
UNIQUE(match_id, market, outcome)
```

### Table `bets`
```
id              INTEGER     PRIMARY KEY AUTOINCREMENT
prediction_id   INTEGER     NOT NULL REFERENCES predictions(id)
bookmaker       TEXT        NOT NULL
odds_taken      REAL        NOT NULL
stake           REAL        NOT NULL            -- en unités bankroll
currency        TEXT        NOT NULL DEFAULT 'EUR'
placed_at       DATETIME    NOT NULL
result          TEXT                            -- "win", "loss", "push", "void", NULL
pnl             REAL                            -- profit/loss en unités
settled_at      DATETIME
notes           TEXT
```

### Table `alerts`
```
id              INTEGER     PRIMARY KEY AUTOINCREMENT
match_id        INTEGER     REFERENCES matches(id)
channel         TEXT        NOT NULL            -- "whatsapp", "telegram"
message_type    TEXT        NOT NULL            -- "daily_coupon", "value_bet", "analysis", "weekly_report"
recipient       TEXT        NOT NULL            -- numéro WhatsApp ou chat_id Telegram
message_preview TEXT                            -- premiers 200 chars du message
sent_at         DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
status          TEXT        NOT NULL DEFAULT 'pending'
                            -- "pending", "sent", "delivered", "failed"
error_message   TEXT
```

### Table `pipeline_runs`
```
id              INTEGER     PRIMARY KEY AUTOINCREMENT
run_type        TEXT        NOT NULL            -- "daily", "hourly_odds", "weekly_report"
started_at      DATETIME    NOT NULL
finished_at     DATETIME
status          TEXT        NOT NULL DEFAULT 'running'
                            -- "running", "success", "partial_failure", "failure"
matches_fetched INTEGER     DEFAULT 0
predictions_made INTEGER    DEFAULT 0
bets_selected   INTEGER     DEFAULT 0
alerts_sent     INTEGER     DEFAULT 0
error_message   TEXT
```

### Table `model_params`
```
id              INTEGER     PRIMARY KEY AUTOINCREMENT
model_name      TEXT        NOT NULL            -- "dixon_coles"
version         TEXT        NOT NULL
sport           TEXT        NOT NULL
league          TEXT        NOT NULL
params_json     TEXT        NOT NULL            -- paramètres sérialisés en JSON
trained_on      TEXT                            -- plage de dates d'entraînement
brier_score     REAL
log_loss        REAL
created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
is_active       BOOLEAN     NOT NULL DEFAULT TRUE
```

---

## 5. Variables d'environnement

### APIs externes
```bash
# The Odds API
ODDS_API_KEY=your_key_here                    # Clé API sur the-odds-api.com
ODDS_API_BASE_URL=https://api.the-odds-api.com/v4

# API-Football (RapidAPI)
FOOTBALL_API_KEY=your_rapidapi_key            # Clé RapidAPI
FOOTBALL_API_BASE_URL=https://v3.football.api-sports.io
FOOTBALL_API_HOST=v3.football.api-sports.io

# BallDontLie (NBA - Phase 2)
BALLDONTLIE_API_KEY=your_key_here             # Clé gratuite sur balldontlie.io
```

### Base de données
```bash
DATABASE_URL=sqlite:///./data/apex_bot.db     # Phase 1 SQLite
# DATABASE_URL=postgresql://user:pass@host/db # Phase 3 PostgreSQL
```

### WhatsApp Meta Cloud API
```bash
WHATSAPP_ACCESS_TOKEN=your_token              # Token temporaire ou permanent
WHATSAPP_PHONE_NUMBER_ID=123456789            # ID du numéro WhatsApp Business
WHATSAPP_BUSINESS_ACCOUNT_ID=987654321
WHATSAPP_API_VERSION=v19.0
WHATSAPP_WEBHOOK_VERIFY_TOKEN=random_secret   # Pour la vérification du webhook
WHATSAPP_RECIPIENTS=+33612345678,+33687654321 # Liste des destinataires (CSV)
```

### Telegram (fallback)
```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...          # Token @BotFather
TELEGRAM_CHAT_IDS=-1001234567890              # IDs des groupes/canaux (CSV)
```

### Paramètres métier
```bash
ENVIRONMENT=development                       # "development", "production"
LOG_LEVEL=INFO                                # "DEBUG", "INFO", "WARNING", "ERROR"
EV_THRESHOLD=0.05                             # Seuil EV minimum (+5%)
KELLY_FRACTION=0.25                           # Fraction Kelly (25% = quart de Kelly)
MIN_ODDS=1.50                                 # Cote minimum
MAX_ODDS=5.00                                 # Cote maximum
MAX_BETS_PER_DAY=5                            # Limite de paris par coupon
BANKROLL_UNITS=100                            # Bankroll en unités (pour Kelly)
DAILY_PIPELINE_HOUR=6                         # Heure UTC du pipeline quotidien
DAILY_PIPELINE_MINUTE=0
SPORTS=football                               # Sports actifs (CSV)
LEAGUES=EPL,LaLiga,Bundesliga,SerieA,Ligue1  # Ligues actives
```

---

## 6. Décisions techniques avec justification

### SQLite (Phase 1) → PostgreSQL (Phase 3)
**Phase 1 — SQLite :**
- Zéro infrastructure supplémentaire sur le VPS
- Suffisant pour < 50 000 lignes et 1 utilisateur concurrent (le scheduler)
- Migrations Alembic identiques, le changement de DB est transparent

**Phase 3 — PostgreSQL :**
- Nécessaire quand plusieurs processus lisent/écrivent simultanément
- Support natif JSON pour `params_json`
- Meilleure gestion des index et des volumes

### APScheduler 3.x (pas Celery)
- Celery nécessite un broker (Redis ou RabbitMQ) = infrastructure supplémentaire sur VPS low-cost
- APScheduler tourne dans le même processus Python, zéro dépendance externe
- Suffisant pour les besoins de la Phase 1 (< 10 jobs, pas de distribution)
- Limitation : pas de distribution multi-workers (acceptable Phase 1-2)

### Meta Cloud API (pas whatsapp-web.js)
- whatsapp-web.js nécessite un navigateur headless (Puppeteer/Chrome) = 500 MB RAM sur VPS
- Meta Cloud API est l'API officielle, stable, pas de risque de ban
- Inconvénient : nécessite un compte Meta Business et une approbation des templates
- Alternative rejetée : Twilio (coût élevé, $0.005/message)

### Dixon-Coles (Phase 1)
**Avantages :**
- Modèle académique prouvé (Dixon & Coles, 1997)
- Ne nécessite que l'historique des scores (facilement disponible)
- Excellent pour les marchés 1X2 et Over/Under
- Paramètre ρ corrige les biais sur les matchs à faible score

**Alternatives rejetées :**
- XGBoost : nécessite feature engineering complexe + gros dataset labellisé
- Elo simple : moins précis sur les marchés de totaux et handicaps
- Modèle Poisson simple : ne capture pas la corrélation des scores (biais ρ non corrigé)

### httpx (pas requests ou aiohttp)
- API presque identique à `requests` (adoption facile)
- Support async natif (préparation pour Phase 3 avec FastAPI)
- Meilleur support HTTP/2
- `pytest-httpx` permet le mock précis des requêtes dans les tests

### tenacity (pas implémentation manuelle du retry)
- Décorateurs propres : `@retry(wait=wait_exponential(min=1, max=30), stop=stop_after_attempt(3))`
- Configurable par exception type (retry sur HTTPError, pas sur ValueError)
- Logging automatique des tentatives
