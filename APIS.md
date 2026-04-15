# APEX BOT V2 — Guide des APIs utilisées

---

## 1. The Odds API

**Site :** https://the-odds-api.com  
**Plan :** Free (500 req/mois) → Basic ($20/mois, 10 000 req)  
**Usage principal :** Récupérer les cotes de tous les bookmakers pour les matchs à venir

### Endpoints utilisés

#### 1.1 Liste des sports disponibles
```
GET https://api.the-odds-api.com/v4/sports/
```
Paramètres :
- `apiKey` (obligatoire)

Exemple de réponse :
```json
[
  {
    "key": "soccer_epl",
    "group": "Soccer",
    "title": "EPL",
    "description": "English Premier League",
    "active": true,
    "has_outrights": false
  }
]
```

**Fréquence :** 1 fois par jour (données statiques)  
**Variables env :** `ODDS_API_KEY`

---

#### 1.2 Cotes des matchs à venir (principal)
```
GET https://api.the-odds-api.com/v4/sports/{sport}/odds/
```
Paramètres :
- `apiKey` (obligatoire)
- `regions` : `eu` (recommandé pour bookmakers européens)
- `markets` : `h2h,totals,btts,asian_handicap,double_chance`
- `oddsFormat` : `decimal`
- `dateFormat` : `iso`

Exemple de réponse :
```json
{
  "id": "a1b2c3d4e5f6",
  "sport_key": "soccer_epl",
  "sport_title": "EPL",
  "commence_time": "2024-12-15T15:00:00Z",
  "home_team": "Arsenal",
  "away_team": "Chelsea",
  "bookmakers": [
    {
      "key": "bet365",
      "title": "Bet365",
      "last_update": "2024-12-14T10:30:00Z",
      "markets": [
        {
          "key": "h2h",
          "last_update": "2024-12-14T10:30:00Z",
          "outcomes": [
            {"name": "Arsenal", "price": 2.10},
            {"name": "Chelsea", "price": 3.50},
            {"name": "Draw", "price": 3.20}
          ]
        },
        {
          "key": "totals",
          "outcomes": [
            {"name": "Over", "description": "2.5", "price": 1.85},
            {"name": "Under", "description": "2.5", "price": 1.95}
          ]
        }
      ]
    }
  ]
}
```

**Fréquence :** Toutes les 15 min pour matchs J0, toutes les heures pour J+1 à J+7  
**Quota consommé :** 1 requête par appel (attention au quota Free)  
**Cache recommandé :** 15 minutes (matchs futurs), 5 minutes (matchs J0)

Code exemple :
```python
import httpx

async def fetch_odds(sport: str, markets: list[str]) -> dict:
    params = {
        "apiKey": settings.ODDS_API_KEY,
        "regions": "eu",
        "markets": ",".join(markets),
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.ODDS_API_BASE_URL}/sports/{sport}/odds/",
            params=params,
            timeout=10.0,
        )
        resp.raise_for_status()
        # Remaining quota dans les headers
        remaining = resp.headers.get("x-requests-remaining")
        return resp.json()
```

**Gestion du quota :**
- Header `x-requests-remaining` sur chaque réponse → logger et alerter si < 100
- Réduire la fréquence si quota < 50

---

## 2. API-Football (RapidAPI)

**Site :** https://rapidapi.com/api-sports/api/api-football  
**Plan :** Free (100 req/jour) → Basic ($10/mois, 7 500 req/jour)  
**Usage principal :** Statistiques des équipes, historique des matchs, composition

### Endpoints utilisés

#### 2.1 Fixtures (matchs)
```
GET https://v3.football.api-sports.io/fixtures
```
Paramètres :
- `league` : ID de la ligue (EPL = 39, La Liga = 140, etc.)
- `season` : 2024
- `from` : 2024-12-15 (date début)
- `to` : 2024-12-22 (date fin)

Exemple de réponse :
```json
{
  "response": [
    {
      "fixture": {
        "id": 1035165,
        "date": "2024-12-15T15:00:00+00:00",
        "status": {"short": "NS", "long": "Not Started"}
      },
      "league": {"id": 39, "name": "Premier League"},
      "teams": {
        "home": {"id": 42, "name": "Arsenal"},
        "away": {"id": 49, "name": "Chelsea"}
      },
      "goals": {"home": null, "away": null}
    }
  ]
}
```

**Fréquence :** 1 fois par jour à 03h00 UTC  
**Cache :** 1 heure

---

#### 2.2 Statistiques d'équipe
```
GET https://v3.football.api-sports.io/teams/statistics
```
Paramètres : `team`, `league`, `season`

Exemple de réponse (simplifié) :
```json
{
  "response": {
    "team": {"id": 42, "name": "Arsenal"},
    "goals": {
      "for": {"average": {"home": "2.5", "away": "1.8"}},
      "against": {"average": {"home": "0.9", "away": "1.2"}}
    },
    "form": "WWDLW"
  }
}
```

**Fréquence :** 1 fois par jour  
**Cache :** 6 heures

---

#### 2.3 Head-to-head
```
GET https://v3.football.api-sports.io/fixtures/headtohead
```
Paramètres : `h2h=42-49` (home_id-away_id), `last=5`

**Fréquence :** 1 fois par jour par paire d'équipes  
**Cache :** 24 heures (données historiques stables)

Code exemple :
```python
headers = {
    "X-RapidAPI-Key": settings.FOOTBALL_API_KEY,
    "X-RapidAPI-Host": settings.FOOTBALL_API_HOST,
}
async with httpx.AsyncClient(headers=headers) as client:
    resp = await client.get(
        f"{settings.FOOTBALL_API_BASE_URL}/fixtures",
        params={"league": 39, "season": 2024, "from": "2024-12-15", "to": "2024-12-22"},
    )
    data = resp.json()["response"]
```

**IDs des ligues principales :**
| Ligue | ID |
|-------|-----|
| Premier League | 39 |
| La Liga | 140 |
| Bundesliga | 78 |
| Serie A | 135 |
| Ligue 1 | 61 |
| Champions League | 2 |

---

## 3. BallDontLie (NBA — Phase 2)

**Site :** https://www.balldontlie.io  
**Plan :** Free (60 req/min, accès aux données historiques)  
**Usage principal :** Stats NBA pour le modèle basketball

### Endpoints utilisés

#### 3.1 Matchs à venir
```
GET https://api.balldontlie.io/v1/games
```
Paramètres : `dates[]=2024-12-15`, `per_page=100`

Exemple de réponse :
```json
{
  "data": [
    {
      "id": 1,
      "date": "2024-12-15T00:00:00.000Z",
      "home_team": {"id": 1, "full_name": "Atlanta Hawks", "abbreviation": "ATL"},
      "visitor_team": {"id": 2, "full_name": "Boston Celtics", "abbreviation": "BOS"},
      "home_team_score": 0,
      "visitor_team_score": 0,
      "status": "1st Qtr"
    }
  ]
}
```

**Fréquence :** 1 fois par jour  
**Variables env :** `BALLDONTLIE_API_KEY`

Code exemple :
```python
headers = {"Authorization": settings.BALLDONTLIE_API_KEY}
async with httpx.AsyncClient(headers=headers) as client:
    resp = await client.get(
        "https://api.balldontlie.io/v1/games",
        params={"dates[]": "2024-12-15", "per_page": 100},
    )
```

---

## 4. Open-Meteo (météo — Phase 2)

**Site :** https://open-meteo.com  
**Plan :** Gratuit (10 000 req/jour)  
**Usage principal :** Conditions météo au stade (vent, pluie → impact sur les totaux)

### Endpoint utilisé
```
GET https://api.open-meteo.com/v1/forecast
```
Paramètres : `latitude`, `longitude`, `hourly=precipitation,wind_speed_10m`, `forecast_days=7`

Exemple de réponse :
```json
{
  "hourly": {
    "time": ["2024-12-15T15:00"],
    "precipitation": [2.5],
    "wind_speed_10m": [25.0]
  }
}
```

**Pas de clé API requise** pour le plan gratuit  
**Fréquence :** 1 fois par jour, uniquement pour les matchs avec stade en extérieur

---

## 5. Meta WhatsApp Cloud API

**Site :** https://developers.facebook.com/docs/whatsapp/cloud-api  
**Plan :** 1 000 conversations d'affaires par mois gratuitement  
**Usage principal :** Envoi des coupons quotidiens et des alertes

### Endpoint d'envoi de message
```
POST https://graph.facebook.com/v19.0/{phone_number_id}/messages
```

Headers :
- `Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}`
- `Content-Type: application/json`

Body pour message texte libre (dans la fenêtre 24h) :
```json
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "+33612345678",
  "type": "text",
  "text": {
    "preview_url": false,
    "body": "Voici le coupon du jour..."
  }
}
```

Body pour message template (hors fenêtre 24h) :
```json
{
  "messaging_product": "whatsapp",
  "to": "+33612345678",
  "type": "template",
  "template": {
    "name": "daily_coupon",
    "language": {"code": "fr"},
    "components": [
      {
        "type": "body",
        "parameters": [
          {"type": "text", "text": "Arsenal vs Chelsea"},
          {"type": "text", "text": "+8.3%"}
        ]
      }
    ]
  }
}
```

Code exemple :
```python
async def send_message(to: str, text: str) -> dict:
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
```

**Gestion des erreurs :**
- Code 131047 : message hors fenêtre 24h → utiliser un template
- Code 131056 : quota atteint → retry dans 1h
- Code 100 : numéro invalide → loguer et skipper
- Code 190 : token expiré → refresh et retry

**Fréquence :** 1 fois par jour (coupon), + alertes ponctuelles  
**Variables env :** `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_API_VERSION`
