# Apex Bot V2 — Bot de prédiction sportive

Bot automatisé de value betting sportif. Identifie les paris à valeur espérée positive en comparant les probabilités calculées par des modèles statistiques aux cotes des bookmakers.

## Fonctionnalités

- **Modèle Dixon-Coles** pour le football (5 ligues européennes)
- **5 marchés** : 1X2, Over/Under, BTTS, Asian Handicap, Double Chance
- **Démarginisation** des cotes bookmakers (power method)
- **Kelly Criterion** pour le dimensionnement des mises
- **Alertes WhatsApp** via Meta Cloud API + Telegram (fallback)
- **Scheduler APScheduler** : pipeline quotidien 06h00 UTC
- **Déploiement Oracle Free Tier** (Ubuntu ARM)

## Démarrage rapide

### Prérequis
- Python 3.12+
- Clés API : The Odds API, API-Football, Meta WhatsApp Cloud

### Installation

```bash
git clone https://github.com/drake48nathan-source/Bot-Apex-.git
cd Bot-Apex-
pip install -e ".[dev]"
cp .env.example .env
# Remplir .env avec vos clés API
```

### Configuration base de données

```bash
alembic upgrade head
python scripts/bootstrap.py  # Télécharge données historiques + calibre le modèle
```

### Lancement

```bash
# Pipeline unique (test)
python -m src.scheduler.pipeline --run-once

# Scheduler complet (production)
python -m src.scheduler.pipeline
```

### Tests

```bash
pytest
pytest --cov=src --cov-report=html  # Avec rapport de couverture
```

## Architecture

Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour le schéma complet.

## Plan de développement

Voir [PLANNING.md](PLANNING.md) pour la vision et les phases.  
Voir [PHASE1.md](PHASE1.md) pour le détail jour par jour de la Phase 1.

## APIs utilisées

Voir [APIS.md](APIS.md) pour la documentation des APIs.

## WhatsApp

Voir [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md) pour la configuration Meta Cloud API.

## Marchés implémentés

Voir [MARKETS.md](MARKETS.md) pour les formules et exemples par marché.

## Structure du projet

Voir [STRUCTURE.md](STRUCTURE.md) pour l'arborescence complète annotée.
