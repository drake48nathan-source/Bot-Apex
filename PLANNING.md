# APEX BOT V2 — Plan de développement

## Vision

Construire un bot de prédiction sportive automatisé, rentable et maintenable, capable d'identifier des **value bets** (paris à valeur espérée positive) en analysant les cotes de bookmakers et en les comparant à des probabilités calculées par des modèles statistiques.

Le bot collecte des données en temps réel, génère des prédictions, sélectionne les meilleurs paris, et diffuse des alertes structurées via WhatsApp (Meta Cloud API) et Telegram.

**Ressources du projet :**
- GitHub : https://github.com/drake48nathan-source/Bot-Apex-
- Railway : https://railway.com/project/e97dc9a2-a986-4f2d-a3e1-0cb9fc3c2b48/service/4bc6caed-a2d4-450f-be04-638dff0a6219
- Déploiement : automatique via push sur `main` (Railway CI/CD)
- Plateforme cible : Railway (conteneur Docker, worker process)

**Principes directeurs :**
- Rigueur statistique avant tout (pas de "gut feeling")
- Code testable, modulaire, déployable sur un VPS low-cost (Oracle Free Tier)
- Monétisation progressive (accès gratuit → premium → abonnement)
- Zéro dépendance à des navigateurs headless ou scrapers fragiles

---

## Architecture cible

```
┌─────────────────────────────────────────────────────────────┐
│                        SOURCES DE DONNÉES                    │
│  The Odds API  │  API-Football  │  Open-Meteo  │ BallDontLie │
└────────┬────────────────┬───────────────┬──────────────┬─────┘
         │                │               │              │
         ▼                ▼               ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA FETCHERS (httpx + tenacity)          │
│              Cache TTL en mémoire + circuit breaker          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    BASE DE DONNÉES SQLITE                    │
│        Match │ Odd │ Prediction │ Bet │ Alert │ Log          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    MODÈLES DE PRÉDICTION                     │
│     Dixon-Coles (football) │ Elo (autres sports Phase 2)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    SÉLECTION DES PARIS                       │
│         Démarginisation │ Value Calculator │ Kelly           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    MESSAGING                                  │
│         WhatsApp (Meta Cloud API) │ Telegram (fallback)      │
└─────────────────────────────────────────────────────────────┘
         ▲
         │
┌────────┴────────────────────────────────────────────────────┐
│                    SCHEDULER (APScheduler)                   │
│    Pipeline quotidien │ Alertes temps réel │ Rapport hebdo   │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1 — Semaines 1-2 (Football + WhatsApp + 5 marchés)

### Objectifs
- Avoir un pipeline de bout en bout fonctionnel sur le football (top 5 ligues européennes)
- Implémenter le modèle Dixon-Coles pour les prédictions de score
- Couvrir 5 marchés : 1X2, Over/Under 2.5, BTTS, Asian Handicap, Double Chance
- Diffuser un coupon quotidien via WhatsApp
- Déployer sur Oracle Free Tier

### Livrables
1. Base de données SQLite avec schéma complet et migrations Alembic
2. Data fetchers pour The Odds API et API-Football (avec cache + retry)
3. Modèle Dixon-Coles calibré sur données historiques (5 dernières saisons)
4. ValueCalculator avec démarginisation (power method)
5. Scheduler APScheduler avec pipeline quotidien (06h00 UTC)
6. Intégration WhatsApp Meta Cloud API
7. Suite de tests unitaires (couverture > 80%)
8. Déploiement fonctionnel sur VPS

### Critères de succès (Definition of Done)
- [ ] Le pipeline tourne sans erreur pendant 7 jours consécutifs
- [ ] Au moins 1 coupon WhatsApp envoyé par jour
- [ ] Value bets avec EV > +5% détectés quotidiennement
- [ ] Temps d'exécution du pipeline < 3 minutes
- [ ] Zéro crash non géré (toutes les exceptions capturées et loguées)
- [ ] Couverture de tests > 80% sur les modules core/models/selection
- [ ] Documentation suffisante pour qu'un tiers puisse déployer en < 1h

---

## Phase 2 — Semaines 3-4 (Multi-sports + analyses détaillées)

### Objectifs
- Étendre à 2 sports supplémentaires : Basketball (NBA/Euroleague) et Tennis
- Générer des analyses détaillées par match (pas seulement une cote)
- Implémenter un système de tracking des résultats (win rate, ROI réel)

### Livrables
1. Fetcher BallDontLie pour NBA
2. Modèle Elo pour basketball et tennis
3. 5 nouveaux marchés (player props, spreads, moneylines)
4. Module de génération d'analyses markdown (contexte + stats + facteurs)
5. Dashboard de suivi ROI (logs structurés + export CSV)
6. Rapport hebdomadaire automatique WhatsApp/Telegram

### Critères de succès
- [ ] 3 sports couverts avec modèles distincts
- [ ] ROI calculé et affiché hebdomadairement
- [ ] Analyses matches envoyées > 1h avant coup d'envoi
- [ ] Taux de livraison messages > 99%

---

## Phase 3 — Semaines 5-6 (Alertes temps réel + feedback loop)

### Objectifs
- Détecter les mouvements de cotes en temps réel (line movements)
- Implémenter une boucle de feedback pour améliorer le modèle
- Migrer vers PostgreSQL pour les volumes de données croissants
- Ajouter une interface web légère (FastAPI + HTMX) pour le monitoring

### Livrables
1. Poller de cotes temps réel (toutes les 15 min pour les matchs J-1 et J0)
2. Alertes line movement WhatsApp
3. Recalibration automatique hebdomadaire du modèle Dixon-Coles
4. Migration SQLite → PostgreSQL (Alembic migration script)
5. Interface web FastAPI : tableau de bord prédictions + ROI
6. Système d'abonnement (tiers gratuit vs premium)

### Critères de succès
- [ ] Alertes line movement < 5 min après détection
- [ ] Recalibration automatique sans intervention manuelle
- [ ] Interface web accessible et fonctionnelle
- [ ] Système d'abonnement opérationnel avec au moins 1 tier payant

---

## Décisions d'architecture

| Décision | Option choisie | Raison | Alternatives rejetées |
|----------|---------------|--------|-----------------------|
| Base de données Phase 1 | SQLite | Simplicité, zéro infra, suffisant pour < 50k lignes | PostgreSQL (surcharge Phase 1), MongoDB (pas de schéma structuré) |
| Base de données Phase 3 | PostgreSQL | Concurrence, volumes, JSON natif | MySQL (moins bonne gestion des migrations) |
| Scheduler | APScheduler 3.x | Pas de broker requis, simple à déployer | Celery (nécessite Redis/RabbitMQ), Rocketry (moins mature) |
| Messaging principal | Meta Cloud API | Stable sur VPS, pas de session browser, API officielle | whatsapp-web.js (session fragile), Twilio (coût élevé) |
| Messaging fallback | python-telegram-bot | Gratuit, fiable, bonne API async | Discord (pas adapté aux paris sportifs) |
| Modèle football Phase 1 | Dixon-Coles | Pas besoin de training data externe, prouvé académiquement | XGBoost (nécessite features engineering + dataset), ELO simple (moins précis) |
| Modèle autres sports | Elo + spreads | Générique, adapté aux sports en points | Dixon-Coles (spécifique au football) |
| HTTP client | httpx | Support async natif, API clean | requests (synchrone), aiohttp (API moins intuitive) |
| Retry | tenacity | Décorateurs propres, configurable | Implémentation manuelle, backoff library |
| Settings | pydantic-settings | Validation automatique, .env natif | python-decouple (moins de validation) |
| Logging | structlog | JSON structuré, contexte par thread | loguru (moins structuré), logging standard (trop verbeux) |

---

## Risques identifiés

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Quota API The Odds API dépassé | Moyen | Élevé | Cache TTL agressif, monitoring des appels, fallback sur données J-1 |
| Token WhatsApp expiré | Faible | Élevé | Refresh automatique, alertes Telegram en fallback |
| Dixon-Coles sous-performant sur certaines ligues | Moyen | Moyen | Calibration par ligue séparément, seuil EV plus conservateur |
| VPS Oracle Free Tier instable | Faible | Élevé | Supervisord + healthcheck cron, notifications en cas de downtime |
| Changement d'API des bookmakers | Faible | Moyen | Abstraction via BaseDataFetcher, tests d'intégration sur données mockées |
| Faux positifs value bets (biais du modèle) | Moyen | Élevé | Backtesting systématique, seuils conservateurs Phase 1, tracking ROI réel |
| Legality / TOS bookmakers | Faible | Élevé | Usage personnel uniquement Phase 1, conseil juridique avant monétisation |
