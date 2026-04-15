# Phase 1 — Plan détaillé jour par jour

**Durée :** 14 jours (2 semaines)
**Objectif :** Pipeline complet football → WhatsApp opérationnel

---

## Jour 1-2 : Fondations (infrastructure + base de données)

### Tâche 1.1 : Structure du projet
- [ ] Créer l'arborescence complète des dossiers (voir STRUCTURE.md)
- [ ] Initialiser `pyproject.toml` avec toutes les dépendances
- [ ] Créer `.env.example` avec toutes les variables documentées
- [ ] Créer `.gitignore` adapté Python/SQLite/secrets
- [ ] Configurer pre-commit hooks : black (format), ruff (lint), mypy (types)
- [ ] Créer `.python-version` avec `3.12`
- [ ] Tester que `python -m pytest` fonctionne (même avec 0 tests)

**Durée estimée : 2h**

---

### Tâche 1.2 : Configuration Pydantic Settings
- [ ] Créer `src/core/config.py` avec classe `Settings(BaseSettings)`
- [ ] Mapper toutes les variables `.env` vers des champs typés
- [ ] Ajouter validateurs Pydantic pour les valeurs critiques (URLs, tokens non vides)
- [ ] Tester le chargement depuis `.env.example` en local

**Durée estimée : 1.5h**

---

### Tâche 1.3 : Base de données SQLite (SQLAlchemy + Alembic)
- [ ] Créer `src/core/database.py` : engine, SessionLocal, Base
- [ ] Définir les modèles SQLAlchemy dans `src/data/models/` :
  - `Match` (id, sport, league, home_team, away_team, kickoff_utc, status, home_score, away_score)
  - `Odd` (id, match_id, bookmaker, market, outcome, price, updated_at)
  - `Prediction` (id, match_id, market, outcome, model_prob, ev, confidence)
  - `Bet` (id, prediction_id, stake, odds, result, pnl, placed_at)
  - `Alert` (id, match_id, channel, message_type, sent_at, status)
- [ ] Initialiser Alembic : `alembic init migrations/`
- [ ] Créer la migration initiale
- [ ] Écrire tests unitaires : création, lecture, relations FK

**Durée estimée : 3h**

---

### Tâche 1.4 : Logging structuré
- [ ] Créer `src/core/logging.py` avec structlog configuré (JSON en prod, couleurs en dev)
- [ ] Ajouter contexte par défaut : `sport`, `pipeline_run_id`, `environment`
- [ ] Tester l'output JSON en mode prod

**Durée estimée : 1h**

---

## Jour 3-4 : Collecte de données football

### Tâche 2.1 : BaseDataFetcher
- [ ] Créer `src/data/fetchers/base.py` avec classe abstraite `BaseDataFetcher`
- [ ] Implémenter cache TTL en mémoire (dict + timestamp, configurable par fetcher)
- [ ] Implémenter retry avec tenacity (3 tentatives, backoff exponentiel 1-30s)
- [ ] Implémenter circuit breaker : après 5 échecs consécutifs, pause 5 minutes
- [ ] Logger chaque appel API (url, status, durée, cache_hit)
- [ ] Écrire tests avec `pytest-httpx` (mock des réponses HTTP)

**Durée estimée : 3h**

---

### Tâche 2.2 : The Odds API Fetcher
- [ ] Créer `src/data/fetchers/odds.py` : classe `OddsFetcher(BaseDataFetcher)`
- [ ] Implémenter `fetch_upcoming_events(sport, regions, markets)` → liste de matchs + cotes
- [ ] Implémenter `fetch_event_odds(event_id, markets)` → cotes détaillées pour un match
- [ ] Parser la réponse JSON → objets `Odd` SQLAlchemy
- [ ] Sauvegarder en base de données avec `upsert` (update si existe, insert sinon)
- [ ] Cache TTL : 15 min pour les matchs futurs, 2 min pour les matchs J0
- [ ] Tests : mock réponse API, vérifier upsert correct

**Durée estimée : 3h**

---

### Tâche 2.3 : API-Football Fetcher
- [ ] Créer `src/data/fetchers/football.py` : classe `FootballFetcher(BaseDataFetcher)`
- [ ] Implémenter `fetch_fixtures(league_id, season)` → fixtures avec statut
- [ ] Implémenter `fetch_team_stats(team_id, league_id, season)` → xG, buts, forme
- [ ] Implémenter `fetch_head_to_head(team1_id, team2_id)` → 5 derniers H2H
- [ ] Parser et sauvegarder en base de données
- [ ] Cache TTL : 1h pour les stats, 5 min pour les fixtures en cours

**Durée estimée : 3h**

---

## Jour 5-6 : Modèle Dixon-Coles

### Tâche 3.1 : Implémentation Dixon-Coles core
- [ ] Créer `src/models/dixon_coles.py` : classe `DixonColesModel`
- [ ] Implémenter la fonction de vraisemblance (log-likelihood)
- [ ] Implémenter le facteur de correction Dixon-Coles (ρ) pour les scores 0-0, 1-0, 0-1, 1-1
- [ ] Implémenter le paramètre de décroissance temporelle (ξ) pour pondérer les matchs récents
- [ ] Implémenter `fit(matches_df)` : optimisation scipy.optimize.minimize
- [ ] Implémenter `predict_score_matrix(home_team, away_team)` → matrice de probabilités de scores (0-10 x 0-10)
- [ ] Écrire tests unitaires sur données synthétiques

**Durée estimée : 4h**

---

### Tâche 3.2 : Calibration et validation du modèle
- [ ] Script `scripts/bootstrap.py` : télécharger les données historiques (saisons 2020-2024)
- [ ] Calibrer le modèle sur PL, La Liga, Bundesliga, Serie A, Ligue 1
- [ ] Implémenter `validate_model(holdout_data)` : Brier Score, log-loss
- [ ] Sauvegarder les paramètres calibrés en base (table `ModelParams`)
- [ ] Afficher les métriques de validation dans les logs

**Durée estimée : 3h**

---

## Jour 7-8 : ValueBetSelector + marchés

### Tâche 4.1 : Démarginisation des cotes
- [ ] Créer `src/selection/value_calculator.py`
- [ ] Implémenter `demargin_power_method(odds_list)` → probabilités vraies
- [ ] Implémenter `demargin_additive(odds_list)` → alternative plus simple
- [ ] Implémenter `calculate_ev(model_prob, fair_odds)` → expected value en %
- [ ] Tests exhaustifs : vérifier que les probs somment à 1 après démarginisation

**Durée estimée : 2h**

---

### Tâche 4.2 : Marchés football (5 marchés)
- [ ] Créer `src/models/markets/result.py` : calcul 1X2 depuis matrice de scores
- [ ] Créer `src/models/markets/totals.py` : Over/Under X.5 buts
- [ ] Créer `src/models/markets/btts.py` : Both Teams to Score
- [ ] Créer `src/models/markets/asian_handicap.py` : Asian Handicap -0.5/+0.5
- [ ] Créer `src/models/markets/double_chance.py` : 1X, X2, 12
- [ ] Tests unitaires : vérifier que les probs somment à 1 pour chaque marché

**Durée estimée : 3h**

---

### Tâche 4.3 : Kelly Criterion + sélection finale
- [ ] Créer `src/selection/kelly.py` : `kelly_fraction(prob, odds, fraction=0.25)`
- [ ] Créer `src/selection/selector.py` : `ValueBetSelector`
- [ ] Filtres : EV minimum (+5%), cote min/max (1.50-5.00), Kelly min (1% bankroll)
- [ ] `select_daily_bets(matches)` → top N value bets du jour triés par EV
- [ ] Tests : vérifier les filtres et le tri

**Durée estimée : 2h**

---

## Jour 9-10 : Intégration WhatsApp (Meta Cloud API)

### Tâche 5.1 : WhatsApp Client
- [ ] Créer `src/messaging/whatsapp.py` : classe `WhatsAppClient`
- [ ] Implémenter `send_text_message(to, text)` via API Meta Cloud
- [ ] Implémenter `send_template_message(to, template_name, params)` pour les templates approuvés
- [ ] Gestion des erreurs : token expiré (refresh auto), rate limit (retry), numéro invalide (skip)
- [ ] Implémenter `send_coupon(bets_list)` → format coupon quotidien
- [ ] Tests avec mock httpx

**Durée estimée : 3h**

---

### Tâche 5.2 : Formatters de messages
- [ ] Créer `src/messaging/formatters.py`
- [ ] `format_daily_coupon(bets)` → message coupon WhatsApp (voir WHATSAPP_SETUP.md)
- [ ] `format_value_bet_alert(bet)` → alerte unitaire
- [ ] `format_match_analysis(match, prediction)` → analyse détaillée
- [ ] Tests : vérifier que les messages ne dépassent pas 4096 chars

**Durée estimée : 2h**

---

### Tâche 5.3 : Telegram Client (fallback)
- [ ] Créer `src/messaging/telegram.py` : classe `TelegramClient`
- [ ] Implémenter `send_message(chat_id, text, parse_mode="HTML")`
- [ ] Implémenter `send_coupon(bets_list)` (réutilise les formatters)
- [ ] Tests avec mock

**Durée estimée : 1.5h**

---

## Jour 11-12 : Scheduler + pipeline complet

### Tâche 6.1 : Jobs APScheduler
- [ ] Créer `src/scheduler/jobs.py`
- [ ] `job_fetch_odds()` : toutes les 15 min pour matchs J0, toutes les heures pour J+1 à J+7
- [ ] `job_fetch_football_stats()` : une fois par jour à 03h00 UTC
- [ ] `job_daily_pipeline()` : à 06h00 UTC (run complet : fetch → predict → select → send)
- [ ] `job_weekly_report()` : chaque lundi à 09h00 UTC

**Durée estimée : 2h**

---

### Tâche 6.2 : Pipeline orchestrateur
- [ ] Créer `src/scheduler/pipeline.py` : classe `Pipeline`
- [ ] `run_daily()` : orchestration complète avec gestion d'erreurs
- [ ] Logging de chaque étape avec durée
- [ ] Sauvegarde de l'état du run en base (table `PipelineRun`)
- [ ] Notification en cas d'échec (Telegram)
- [ ] `__main__` pour lancement direct : `python -m src.scheduler.pipeline`

**Durée estimée : 3h**

---

## Jour 13-14 : Tests + déploiement Oracle Free Tier

### Tâche 7.1 : Suite de tests complète
- [ ] Tests d'intégration end-to-end sur pipeline complet avec données mockées
- [ ] Tests de charge : 100 matchs, 5 marchés, 10 bookmakers → < 1 sec
- [ ] Tests de régression : vérifier que les prédictions de référence ne changent pas
- [ ] Mesurer la couverture : `pytest --cov=src --cov-report=html`
- [ ] Objectif : > 80% couverture sur src/core, src/models, src/selection

**Durée estimée : 4h**

---

### Tâche 7.2 : Déploiement Oracle Free Tier
- [ ] Créer instance Oracle (Ubuntu 22.04, ARM, 4 OCPU, 24 GB RAM)
- [ ] Configurer SSH + firewall (port 22 uniquement)
- [ ] Installer Python 3.12, git, screen/tmux
- [ ] Cloner le repo, configurer `.env` de production
- [ ] Démarrer le pipeline avec supervisord (démarrage automatique au boot)
- [ ] Configurer cron healthcheck : ping toutes les 5 min, alerte Telegram si mort
- [ ] Tester l'envoi WhatsApp depuis le VPS

**Durée estimée : 3h**

---

### Tâche 7.3 : Documentation finale Phase 1
- [ ] Mettre à jour `README.md` avec instructions de déploiement
- [ ] Créer `CHANGELOG.md` avec les fonctionnalités implémentées
- [ ] Documenter les commandes utiles (relancer le pipeline, vérifier les logs, etc.)
- [ ] Rétrospective Phase 1 : ROI simulé vs réel, bugs rencontrés, ajustements Phase 2

**Durée estimée : 1h**

---

## Récapitulatif

| Jours | Module | Durée totale |
|-------|--------|-------------|
| 1-2 | Fondations (structure + DB + config + logging) | ~7.5h |
| 3-4 | Data fetchers (Odds API + API-Football) | ~6h |
| 5-6 | Modèle Dixon-Coles (implémentation + calibration) | ~7h |
| 7-8 | Value Calculator + 5 marchés + Kelly | ~7h |
| 9-10 | WhatsApp + Telegram + Formatters | ~6.5h |
| 11-12 | Scheduler + Pipeline orchestrateur | ~5h |
| 13-14 | Tests + Déploiement + Documentation | ~8h |
| **Total** | | **~47h** |
